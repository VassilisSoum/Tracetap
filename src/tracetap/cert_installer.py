"""
TraceTap Certificate Installer

A cross-platform certificate installer for mitmproxy CA certificates.
Simplified, reliable, and maintainable replacement for complex shell scripts.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


class CertificateInstaller:
    """Cross-platform certificate installer for mitmproxy CA certificates."""

    CERT_NAME = "mitmproxy"

    def __init__(self, cert_path: Optional[Path] = None, verbose: bool = False):
        """
        Initialize certificate installer.

        Args:
            cert_path: Path to certificate file (auto-detected if None)
            verbose: Enable verbose output for debugging
        """
        self.verbose = verbose
        self.platform = platform.system()
        self.cert_path = cert_path or self._find_certificate()

    def _find_certificate(self) -> Optional[Path]:
        """Find mitmproxy certificate in default location."""
        home = Path.home()
        cert_path = home / ".mitmproxy" / "mitmproxy-ca-cert.pem"

        if cert_path.exists():
            self._log(f"Found certificate: {cert_path}")
            return cert_path

        return None

    def _log(self, message: str):
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(f"[DEBUG] {message}")

    def _run_command(self, cmd: list, check: bool = True, capture: bool = True) -> Tuple[int, str, str]:
        """
        Run shell command with proper error handling.

        Args:
            cmd: Command and arguments as list
            check: Raise exception on non-zero exit
            capture: Capture stdout/stderr

        Returns:
            Tuple of (returncode, stdout, stderr)
        """
        self._log(f"Running command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=capture,
                text=True
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout or "", e.stderr or ""
        except FileNotFoundError as e:
            return 127, "", f"Command not found: {cmd[0]}"

    def validate_certificate(self) -> bool:
        """
        Validate that certificate file exists and is valid format.

        Returns:
            True if certificate is valid, False otherwise
        """
        if not self.cert_path:
            print("❌ Certificate file not found")
            print(f"   Expected location: {Path.home()}/.mitmproxy/mitmproxy-ca-cert.pem")
            print("   Generate it by running TraceTap first:")
            print("   $ python tracetap.py --listen 8080")
            return False

        if not self.cert_path.exists():
            print(f"❌ Certificate file does not exist: {self.cert_path}")
            return False

        # Validate it's a PEM certificate
        try:
            with open(self.cert_path, 'r') as f:
                content = f.read()
                if "BEGIN CERTIFICATE" not in content:
                    print(f"❌ Invalid certificate format: {self.cert_path}")
                    print("   File does not contain PEM certificate")
                    return False
        except Exception as e:
            print(f"❌ Cannot read certificate file: {e}")
            return False

        self._log("Certificate validation passed")
        return True

    def install(self) -> bool:
        """
        Install certificate to system trust store.

        Returns:
            True if installation successful, False otherwise
        """
        if not self.validate_certificate():
            return False

        print(f"🔐 Installing mitmproxy certificate...")
        print(f"📄 Certificate: {self.cert_path}")
        print(f"💻 Platform: {self.platform}")
        print()

        try:
            if self.platform == "Darwin":
                return self._install_macos()
            elif self.platform == "Windows":
                return self._install_windows()
            elif self.platform == "Linux":
                return self._install_linux()
            else:
                print(f"❌ Unsupported platform: {self.platform}")
                return False
        except Exception as e:
            print(f"❌ Installation failed: {e}")
            self._show_manual_instructions()
            return False

    def _install_macos(self) -> bool:
        """Install certificate on macOS using security command."""
        print("🍎 Installing for macOS...")

        # Use login keychain (works across all macOS versions)
        keychain = "login.keychain"

        # Check if certificate already exists
        returncode, stdout, stderr = self._run_command(
            ["security", "find-certificate", "-c", self.CERT_NAME, keychain],
            check=False
        )

        if returncode == 0:
            print("⚠️  Certificate already exists, removing old version...")
            self._run_command(
                ["security", "delete-certificate", "-c", self.CERT_NAME, keychain],
                check=False
            )

        # Install certificate with trust settings
        print("📥 Adding certificate to keychain...")
        print("⚠️  You will be prompted for your password")

        returncode, stdout, stderr = self._run_command(
            ["security", "add-trusted-cert", "-d", "-r", "trustRoot",
             "-k", keychain, str(self.cert_path)],
            check=False,
            capture=False  # Show password prompt to user
        )

        if returncode != 0:
            print(f"❌ Failed to add certificate to keychain")
            print(f"   Error: {stderr}")
            self._show_manual_instructions()
            return False

        # Verify certificate was added with trust
        returncode, stdout, stderr = self._run_command(
            ["security", "find-certificate", "-c", self.CERT_NAME, "-p", keychain],
            check=False
        )

        if returncode != 0:
            print("❌ Certificate installation verification failed")
            return False

        print("✅ Certificate installed to macOS keychain")
        print()
        print("📝 Note: For Firefox, additional setup may be required")
        print("   See: docs/CERTIFICATE_INSTALLATION.md")

        return True

    def _install_windows(self) -> bool:
        """Install certificate on Windows using PowerShell."""
        print("🪟 Installing for Windows...")

        # Use PowerShell to install certificate properly
        # This avoids manual PEM parsing and uses built-in certificate handling
        ps_script = f"""
$ErrorActionPreference = "Stop"
try {{
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2("{str(self.cert_path)}")
    $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
    $store.Open("ReadWrite")

    # Check if certificate already exists
    $existing = $store.Certificates | Where-Object {{ $_.Thumbprint -eq $cert.Thumbprint }}
    if ($existing) {{
        Write-Host "Certificate already installed"
        $store.Close()
        exit 0
    }}

    # Add certificate
    $store.Add($cert)
    $store.Close()

    Write-Host "Certificate installed successfully"
    Write-Host "Thumbprint: $($cert.Thumbprint)"
    exit 0
}} catch {{
    Write-Error $_.Exception.Message
    exit 1
}}
"""

        returncode, stdout, stderr = self._run_command(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            check=False
        )

        if returncode != 0:
            print(f"❌ PowerShell installation failed")
            print(f"   Error: {stderr}")
            self._show_manual_instructions()
            return False

        print("✅ Certificate installed to Windows trust store (Current User)")
        print()
        print("📝 Notes:")
        print("   - Certificate installed for Current User only")
        print("   - For system-wide trust, run as Administrator")
        print("   - For Firefox, additional setup may be required")
        print("   - See: docs/CERTIFICATE_INSTALLATION.md")

        return True

    def _install_linux(self) -> bool:
        """Install certificate on Linux (system-wide)."""
        print("🐧 Installing for Linux...")

        # Detect distribution
        distro = self._detect_linux_distro()
        print(f"   Detected distribution: {distro}")

        if distro in ["debian", "ubuntu"]:
            return self._install_linux_debian()
        elif distro in ["fedora", "rhel", "centos"]:
            return self._install_linux_redhat()
        elif distro == "arch":
            return self._install_linux_arch()
        else:
            print(f"⚠️  Unknown distribution: {distro}")
            print("   Attempting Debian/Ubuntu method...")
            return self._install_linux_debian()

    def _detect_linux_distro(self) -> str:
        """Detect Linux distribution."""
        if Path("/etc/debian_version").exists():
            return "debian"
        elif Path("/etc/fedora-release").exists():
            return "fedora"
        elif Path("/etc/redhat-release").exists():
            return "rhel"
        elif Path("/etc/arch-release").exists():
            return "arch"

        # Try to read os-release
        try:
            with open("/etc/os-release") as f:
                content = f.read().lower()
                if "ubuntu" in content:
                    return "ubuntu"
                elif "debian" in content:
                    return "debian"
                elif "fedora" in content:
                    return "fedora"
                elif "centos" in content or "rhel" in content:
                    return "rhel"
                elif "arch" in content:
                    return "arch"
        except:
            pass

        return "unknown"

    def _install_linux_debian(self) -> bool:
        """Install certificate on Debian/Ubuntu."""
        cert_dest = Path("/usr/local/share/ca-certificates/mitmproxy.crt")

        print(f"📥 Copying certificate to {cert_dest}")
        print("   (requires sudo)")

        returncode, stdout, stderr = self._run_command(
            ["sudo", "cp", str(self.cert_path), str(cert_dest)],
            check=False,
            capture=False
        )

        if returncode != 0:
            print(f"❌ Failed to copy certificate")
            self._show_manual_instructions()
            return False

        print("🔄 Updating CA certificates...")
        returncode, stdout, stderr = self._run_command(
            ["sudo", "update-ca-certificates"],
            check=False,
            capture=False
        )

        if returncode != 0:
            print(f"❌ Failed to update CA certificates")
            return False

        print("✅ Certificate installed system-wide")
        self._show_firefox_note()
        return True

    def _install_linux_redhat(self) -> bool:
        """Install certificate on RHEL/Fedora/CentOS."""
        cert_dest = Path("/etc/pki/ca-trust/source/anchors/mitmproxy.pem")

        print(f"📥 Copying certificate to {cert_dest}")
        print("   (requires sudo)")

        returncode, stdout, stderr = self._run_command(
            ["sudo", "cp", str(self.cert_path), str(cert_dest)],
            check=False,
            capture=False
        )

        if returncode != 0:
            print(f"❌ Failed to copy certificate")
            self._show_manual_instructions()
            return False

        print("🔄 Updating CA trust...")
        returncode, stdout, stderr = self._run_command(
            ["sudo", "update-ca-trust"],
            check=False,
            capture=False
        )

        if returncode != 0:
            print(f"❌ Failed to update CA trust")
            return False

        print("✅ Certificate installed system-wide")
        self._show_firefox_note()
        return True

    def _install_linux_arch(self) -> bool:
        """Install certificate on Arch Linux."""
        cert_dest = Path("/etc/ca-certificates/trust-source/anchors/mitmproxy.pem")

        print(f"📥 Copying certificate to {cert_dest}")
        print("   (requires sudo)")

        returncode, stdout, stderr = self._run_command(
            ["sudo", "cp", str(self.cert_path), str(cert_dest)],
            check=False,
            capture=False
        )

        if returncode != 0:
            print(f"❌ Failed to copy certificate")
            self._show_manual_instructions()
            return False

        print("🔄 Updating CA trust...")
        returncode, stdout, stderr = self._run_command(
            ["sudo", "trust", "extract-compat"],
            check=False,
            capture=False
        )

        if returncode != 0:
            print(f"❌ Failed to update CA trust")
            return False

        print("✅ Certificate installed system-wide")
        self._show_firefox_note()
        return True

    def _show_firefox_note(self):
        """Show note about Firefox requiring additional setup."""
        print()
        print("📝 Note: Firefox uses its own certificate store")
        print("   For Firefox support, install 'libnss3-tools' and run:")
        print(f"   $ certutil -A -d sql:$HOME/.mozilla/firefox/*.default* \\")
        print(f"     -t 'C,,' -n '{self.CERT_NAME}' -i {self.cert_path}")

    def _show_manual_instructions(self):
        """Show platform-specific manual installation instructions."""
        print()
        print("=" * 60)
        print("📋 MANUAL INSTALLATION INSTRUCTIONS")
        print("=" * 60)
        print()

        if self.platform == "Darwin":
            print("macOS Manual Installation:")
            print("1. Open Keychain Access (⌘+Space, type 'Keychain')")
            print("2. Select 'login' keychain in left sidebar")
            print("3. Drag and drop certificate file to keychain:")
            print(f"   {self.cert_path}")
            print("4. Double-click the imported certificate")
            print("5. Expand 'Trust' section")
            print("6. Set 'When using this certificate' to 'Always Trust'")
            print("7. Close window and enter your password")

        elif self.platform == "Windows":
            print("Windows Manual Installation:")
            print("1. Double-click certificate file:")
            print(f"   {self.cert_path}")
            print("2. Click 'Install Certificate'")
            print("3. Select 'Current User'")
            print("4. Select 'Place all certificates in the following store'")
            print("5. Click 'Browse' → Select 'Trusted Root Certification Authorities'")
            print("6. Click 'Next' → 'Finish'")
            print("7. Click 'Yes' on security warning")

        elif self.platform == "Linux":
            distro = self._detect_linux_distro()
            print("Linux Manual Installation:")
            if distro in ["debian", "ubuntu"]:
                print(f"$ sudo cp {self.cert_path} /usr/local/share/ca-certificates/mitmproxy.crt")
                print("$ sudo update-ca-certificates")
            elif distro in ["fedora", "rhel", "centos"]:
                print(f"$ sudo cp {self.cert_path} /etc/pki/ca-trust/source/anchors/mitmproxy.pem")
                print("$ sudo update-ca-trust")
            elif distro == "arch":
                print(f"$ sudo cp {self.cert_path} /etc/ca-certificates/trust-source/anchors/mitmproxy.pem")
                print("$ sudo trust extract-compat")
            else:
                print(f"$ sudo cp {self.cert_path} /usr/local/share/ca-certificates/mitmproxy.crt")
                print("$ sudo update-ca-certificates")

        print()
        print("📖 Full guide: docs/CERTIFICATE_INSTALLATION.md")
        print()

    def verify(self) -> bool:
        """
        Verify certificate is installed and trusted.

        Returns:
            True if certificate is trusted, False otherwise
        """
        print("🔍 Verifying certificate installation...")

        if not self.validate_certificate():
            return False

        if self.platform == "Darwin":
            return self._verify_macos()
        elif self.platform == "Windows":
            return self._verify_windows()
        elif self.platform == "Linux":
            return self._verify_linux()
        else:
            print(f"⚠️  Verification not supported on {self.platform}")
            return False

    def _verify_macos(self) -> bool:
        """Verify certificate on macOS."""
        returncode, stdout, stderr = self._run_command(
            ["security", "find-certificate", "-c", self.CERT_NAME, "-p", "login.keychain"],
            check=False
        )

        if returncode != 0:
            print("❌ Certificate not found in keychain")
            return False

        print("✅ Certificate found in keychain")
        return True

    def _verify_windows(self) -> bool:
        """Verify certificate on Windows."""
        ps_script = f"""
$cert = Get-ChildItem Cert:\\CurrentUser\\Root | Where-Object {{ $_.Subject -like "*{self.CERT_NAME}*" }}
if ($cert) {{
    Write-Host "Found"
    exit 0
}} else {{
    exit 1
}}
"""
        returncode, stdout, stderr = self._run_command(
            ["powershell", "-Command", ps_script],
            check=False
        )

        if returncode != 0:
            print("❌ Certificate not found in Windows trust store")
            return False

        print("✅ Certificate found in Windows trust store")
        return True

    def _verify_linux(self) -> bool:
        """Verify certificate on Linux."""
        # Check if certificate exists in standard locations
        distro = self._detect_linux_distro()

        if distro in ["debian", "ubuntu"]:
            cert_path = Path("/usr/local/share/ca-certificates/mitmproxy.crt")
        elif distro in ["fedora", "rhel", "centos"]:
            cert_path = Path("/etc/pki/ca-trust/source/anchors/mitmproxy.pem")
        elif distro == "arch":
            cert_path = Path("/etc/ca-certificates/trust-source/anchors/mitmproxy.pem")
        else:
            cert_path = Path("/usr/local/share/ca-certificates/mitmproxy.crt")

        if not cert_path.exists():
            print(f"❌ Certificate not found at {cert_path}")
            return False

        print(f"✅ Certificate found at {cert_path}")
        return True

    def info(self):
        """Display certificate information and installation instructions."""
        print("═" * 60)
        print("   TraceTap Certificate Information")
        print("═" * 60)
        print()

        if self.cert_path and self.cert_path.exists():
            print("✅ Certificate generated")
            print(f"📄 Location: {self.cert_path}")
        else:
            print("❌ Certificate not found")
            print(f"📄 Expected location: {Path.home()}/.mitmproxy/mitmproxy-ca-cert.pem")
            print()
            print("Generate certificate by running TraceTap:")
            print("$ python tracetap.py --listen 8080")
            return

        print(f"💻 Platform: {self.platform}")
        print()

        self._show_manual_instructions()

        print("🔍 Verify installation:")
        print("$ python src/tracetap/scripts/cert_manager.py verify")
        print()
        print("📖 Full documentation:")
        print("   docs/CERTIFICATE_INSTALLATION.md")
        print("   docs/TROUBLESHOOTING.md")
        print()
