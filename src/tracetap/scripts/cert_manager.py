#!/usr/bin/env python3
"""
TraceTap Certificate Manager CLI

Command-line interface for managing mitmproxy certificates.
Provides install, verify, info, and uninstall commands.
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cert_installer import CertificateInstaller


def main() -> None:
    """Main entry point for certificate manager CLI."""
    parser = argparse.ArgumentParser(
        description="TraceTap Certificate Manager - Manage mitmproxy CA certificates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Install certificate
  python cert_manager.py install

  # Verify certificate is installed
  python cert_manager.py verify

  # Show certificate information
  python cert_manager.py info

  # Install with custom certificate path
  python cert_manager.py install --cert-path /path/to/cert.pem

  # Enable verbose output
  python cert_manager.py install --verbose

For more help:
  docs/CERTIFICATE_INSTALLATION.md
  docs/TROUBLESHOOTING.md
"""
    )

    parser.add_argument(
        "command",
        choices=["install", "verify", "info", "uninstall"],
        help="Command to execute"
    )

    parser.add_argument(
        "--cert-path",
        type=Path,
        help="Path to certificate file (auto-detected if not specified)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output for debugging"
    )

    args = parser.parse_args()

    # Create installer instance
    installer = CertificateInstaller(
        cert_path=args.cert_path,
        verbose=args.verbose
    )

    # Execute command
    if args.command == "install":
        success = installer.install()
        sys.exit(0 if success else 1)

    elif args.command == "verify":
        success = installer.verify()
        if success:
            print(flush=True)
            print("✅ Certificate is installed and trusted", flush=True)
            print(flush=True)
            print("🧪 To test HTTPS interception:", flush=True)
            print("   1. Start TraceTap: python tracetap.py --listen 8080", flush=True)
            print("   2. Configure proxy: export HTTP(S)_PROXY=http://localhost:8080", flush=True)
            print("   3. Test: curl https://example.com", flush=True)
        sys.exit(0 if success else 1)

    elif args.command == "info":
        installer.info()
        sys.exit(0)

    elif args.command == "uninstall":
        print("🗑️  Uninstalling mitmproxy certificate...", flush=True)
        print(flush=True)
        success = uninstall_certificate(installer)
        sys.exit(0 if success else 1)


def uninstall_certificate(installer: CertificateInstaller) -> bool:
    """
    Uninstall/remove certificate from system trust store.

    Args:
        installer: CertificateInstaller instance

    Returns:
        True if uninstallation successful, False otherwise
    """
    platform_name = installer.platform

    if platform_name == "Darwin":
        return uninstall_macos(installer)
    elif platform_name == "Windows":
        return uninstall_windows(installer)
    elif platform_name == "Linux":
        return uninstall_linux(installer)
    else:
        print(f"❌ Unsupported platform: {platform_name}", flush=True)
        return False


def uninstall_macos(installer: CertificateInstaller) -> bool:
    """Uninstall certificate from macOS keychain."""
    print("🍎 Removing from macOS keychain...", flush=True)

    returncode, stdout, stderr = installer._run_command(
        ["security", "delete-certificate", "-c", installer.CERT_NAME, "login.keychain"],
        check=False
    )

    if returncode != 0:
        if "could not be found" in stderr.lower():
            print("⚠️  Certificate not found in keychain (already removed?)", flush=True)
            return True
        else:
            print(f"❌ Failed to remove certificate: {stderr}", flush=True)
            return False

    print("✅ Certificate removed from macOS keychain", flush=True)
    return True


def uninstall_windows(installer: CertificateInstaller) -> bool:
    """Uninstall certificate from Windows trust store."""
    print("🪟 Removing from Windows trust store...", flush=True)

    ps_script = f"""
$ErrorActionPreference = "Stop"
try {{
    $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
    $store.Open("ReadWrite")

    $certs = $store.Certificates | Where-Object {{ $_.Subject -like "*{installer.CERT_NAME}*" }}

    if ($certs.Count -eq 0) {{
        Write-Host "Certificate not found"
        $store.Close()
        exit 2
    }}

    foreach ($cert in $certs) {{
        $store.Remove($cert)
        Write-Host "Removed certificate: $($cert.Thumbprint)"
    }}

    $store.Close()
    exit 0
}} catch {{
    Write-Error $_.Exception.Message
    exit 1
}}
"""

    returncode, stdout, stderr = installer._run_command(
        ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        check=False
    )

    if returncode == 2:
        print("⚠️  Certificate not found in trust store (already removed?)", flush=True)
        return True
    elif returncode != 0:
        print(f"❌ Failed to remove certificate: {stderr}", flush=True)
        return False

    print("✅ Certificate removed from Windows trust store", flush=True)
    return True


def uninstall_linux(installer: CertificateInstaller) -> bool:
    """Uninstall certificate from Linux system trust."""
    print("🐧 Removing from Linux system trust...", flush=True)

    distro = installer._detect_linux_distro()

    if distro in ["debian", "ubuntu"]:
        cert_path = Path("/usr/local/share/ca-certificates/mitmproxy.crt")
        update_cmd = ["sudo", "update-ca-certificates", "--fresh"]
    elif distro in ["fedora", "rhel", "centos"]:
        cert_path = Path("/etc/pki/ca-trust/source/anchors/mitmproxy.pem")
        update_cmd = ["sudo", "update-ca-trust"]
    elif distro == "arch":
        cert_path = Path("/etc/ca-certificates/trust-source/anchors/mitmproxy.pem")
        update_cmd = ["sudo", "trust", "extract-compat"]
    else:
        cert_path = Path("/usr/local/share/ca-certificates/mitmproxy.crt")
        update_cmd = ["sudo", "update-ca-certificates", "--fresh"]

    if not cert_path.exists():
        print(f"⚠️  Certificate not found at {cert_path} (already removed?)", flush=True)
        return True

    print(f"📥 Removing {cert_path}", flush=True)
    returncode, stdout, stderr = installer._run_command(
        ["sudo", "rm", str(cert_path)],
        check=False,
        capture=False
    )

    if returncode != 0:
        print(f"❌ Failed to remove certificate file", flush=True)
        return False

    print("🔄 Updating CA certificates...", flush=True)
    returncode, stdout, stderr = installer._run_command(
        update_cmd,
        check=False,
        capture=False
    )

    if returncode != 0:
        print(f"❌ Failed to update CA certificates", flush=True)
        return False

    print("✅ Certificate removed from Linux system trust", flush=True)
    return True


if __name__ == "__main__":
    main()
