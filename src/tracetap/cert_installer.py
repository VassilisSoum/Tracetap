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

    # Banner formatting constants
    BANNER_WIDTH = 60

    # Exit codes
    COMMAND_NOT_FOUND_EXIT_CODE = 127

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
            print(f"[DEBUG] {message}", flush=True)

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
            return self.COMMAND_NOT_FOUND_EXIT_CODE, "", f"Command not found: {cmd[0]}"

    def validate_certificate(self) -> bool:
        """
        Validate that certificate file exists and is valid format.

        Returns:
            True if certificate is valid, False otherwise
        """
        if not self.cert_path:
            print("❌ Certificate file not found", flush=True)
            print(f"   Expected location: {Path.home()}/.mitmproxy/mitmproxy-ca-cert.pem", flush=True)
            print("   Generate it by running TraceTap first:", flush=True)
            print("   $ python tracetap.py --listen 8080", flush=True)
            return False

        if not self.cert_path.exists():
            print(f"❌ Certificate file does not exist: {self.cert_path}", flush=True)
            return False

        # Validate it's a PEM certificate
        try:
            with open(self.cert_path, 'r') as f:
                content = f.read()
                if "BEGIN CERTIFICATE" not in content:
                    print(f"❌ Invalid certificate format: {self.cert_path}", flush=True)
                    print("   File does not contain PEM certificate", flush=True)
                    return False
        except PermissionError as e:
            print(f"❌ Permission denied reading certificate file: {e}", flush=True)
            print(f"   Try running with elevated privileges:", flush=True)
            print(f"   sudo python {Path(__file__).name} install", flush=True)
            print(f"   Or check file permissions: ls -la {self.cert_path}", flush=True)
            return False
        except (FileNotFoundError, IOError, OSError) as e:
            print(f"❌ Cannot read certificate file: {e}", flush=True)
            print(f"   Ensure file exists and contains valid PEM certificate", flush=True)
            print(f"   Try regenerating: python tracetap.py --listen 8080", flush=True)
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

        print(f"🔐 Installing mitmproxy certificate...", flush=True)
        print(f"📄 Certificate: {self.cert_path}", flush=True)
        print(f"💻 Platform: {self.platform}", flush=True)
        print(flush=True)

        try:
            if self.platform == "Darwin":
                return self._install_macos()
            elif self.platform == "Windows":
                return self._install_windows()
            elif self.platform == "Linux":
                return self._install_linux()
            else:
                print(f"❌ Unsupported platform: {self.platform}", flush=True)
                return False
        except Exception as e:
            print(f"❌ Installation failed: {e}", flush=True)
            self._show_manual_instructions()
            return False

    def _install_macos(self) -> bool:
        """Install certificate on macOS using security command."""
        print("🍎 Installing for macOS...", flush=True)

        # Use login keychain (works across all macOS versions)
        keychain = "login.keychain"

        # Check if certificate already exists
        returncode, stdout, stderr = self._run_command(
            ["security", "find-certificate", "-c", self.CERT_NAME, keychain],
            check=False
        )

        if returncode == 0:
            print("⚠️  Certificate already exists, removing old version...", flush=True)
            self._run_command(
                ["security", "delete-certificate", "-c", self.CERT_NAME, keychain],
                check=False
            )

        # Install certificate with trust settings
        print("📥 Adding certificate to keychain...", flush=True)
        print("⚠️  You will be prompted for your password", flush=True)

        returncode, stdout, stderr = self._run_command(
            ["security", "add-trusted-cert", "-d", "-r", "trustRoot",
             "-k", keychain, str(self.cert_path)],
            check=False,
            capture=False  # Show password prompt to user
        )

        if returncode != 0:
            print(f"❌ Failed to add certificate to keychain", flush=True)
            if stderr and "denied" in stderr.lower():
                print(f"   This typically means you entered an incorrect password", flush=True)
                print(f"   Try again: security add-trusted-cert -d -r trustRoot -k login.keychain {self.cert_path}", flush=True)
            elif stderr and "already exists" in stderr.lower():
                print(f"   Certificate may already be installed", flush=True)
                print(f"   Try removing first: security delete-certificate -c mitmproxy login.keychain", flush=True)
            else:
                print(f"   Error: {stderr}", flush=True)
            self._show_manual_instructions()
            return False

        # Verify certificate was added with trust
        returncode, stdout, stderr = self._run_command(
            ["security", "find-certificate", "-c", self.CERT_NAME, "-p", keychain],
            check=False
        )

        if returncode != 0:
            print("❌ Certificate installation verification failed", flush=True)
            return False

        print("✅ Certificate installed to macOS keychain", flush=True)
        print(flush=True)
        print("📝 Note: For Firefox, additional setup may be required", flush=True)
        print("   See: docs/CERTIFICATE_INSTALLATION.md", flush=True)

        return True

    def _install_windows(self) -> bool:
        """Install certificate on Windows using PowerShell."""
        print("🪟 Installing for Windows...", flush=True)

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
            print(f"❌ PowerShell installation failed", flush=True)
            if stderr and ("access denied" in stderr.lower() or "unauthorized" in stderr.lower()):
                print(f"   Try running Command Prompt as Administrator", flush=True)
                print(f"   Then run: powershell -NoProfile -ExecutionPolicy Bypass", flush=True)
            elif stderr and ("not valid" in stderr.lower() or "cannot be loaded" in stderr.lower()):
                print(f"   Certificate file may be corrupted or invalid", flush=True)
                print(f"   Try regenerating: python tracetap.py --listen 8080", flush=True)
            else:
                print(f"   Error: {stderr}", flush=True)
            self._show_manual_instructions()
            return False

        print("✅ Certificate installed to Windows trust store (Current User)", flush=True)
        print(flush=True)
        print("📝 Notes:", flush=True)
        print("   - Certificate installed for Current User only", flush=True)
        print("   - For system-wide trust, run as Administrator", flush=True)
        print("   - For Firefox, additional setup may be required", flush=True)
        print("   - See: docs/CERTIFICATE_INSTALLATION.md", flush=True)

        return True

    def _install_linux(self) -> bool:
        """Install certificate on Linux (system-wide)."""
        print("🐧 Installing for Linux...", flush=True)

        # Detect distribution
        distro = self._detect_linux_distro()
        print(f"   Detected distribution: {distro}", flush=True)

        if distro in ["debian", "ubuntu"]:
            return self._install_linux_debian()
        elif distro in ["fedora", "rhel", "centos"]:
            return self._install_linux_redhat()
        elif distro == "arch":
            return self._install_linux_arch()
        else:
            print(f"⚠️  Unknown distribution: {distro}", flush=True)
            print("   Attempting Debian/Ubuntu method...", flush=True)
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
        except (FileNotFoundError, IOError, PermissionError):
            pass

        return "unknown"

    def _install_linux_debian(self) -> bool:
        """Install certificate on Debian/Ubuntu."""
        cert_dest = Path("/usr/local/share/ca-certificates/mitmproxy.crt")

        print(f"📥 Copying certificate to {cert_dest}", flush=True)
        print("   (requires sudo)", flush=True)

        returncode, stdout, stderr = self._run_command(
            ["sudo", "cp", str(self.cert_path), str(cert_dest)],
            check=False,
            capture=False
        )

        if returncode != 0:
            print(f"❌ Failed to copy certificate", flush=True)
            if stderr and "permission denied" in stderr.lower():
                print(f"   This requires sudo privileges", flush=True)
                print(f"   Try: sudo cp {self.cert_path} {cert_dest}", flush=True)
            else:
                print(f"   Error: {stderr if stderr else 'Unknown error'}", flush=True)
            self._show_manual_instructions()
            return False

        print("🔄 Updating CA certificates...", flush=True)
        returncode, stdout, stderr = self._run_command(
            ["sudo", "update-ca-certificates"],
            check=False,
            capture=False
        )

        if returncode != 0:
            print(f"❌ Failed to update CA certificates", flush=True)
            return False

        print("✅ Certificate installed system-wide", flush=True)
        self._show_firefox_note()
        return True

    def _install_linux_redhat(self) -> bool:
        """Install certificate on RHEL/Fedora/CentOS."""
        cert_dest = Path("/etc/pki/ca-trust/source/anchors/mitmproxy.pem")

        print(f"📥 Copying certificate to {cert_dest}", flush=True)
        print("   (requires sudo)", flush=True)

        returncode, stdout, stderr = self._run_command(
            ["sudo", "cp", str(self.cert_path), str(cert_dest)],
            check=False,
            capture=False
        )

        if returncode != 0:
            print(f"❌ Failed to copy certificate", flush=True)
            if stderr and "permission denied" in stderr.lower():
                print(f"   This requires sudo privileges", flush=True)
                print(f"   Try: sudo cp {self.cert_path} {cert_dest}", flush=True)
            else:
                print(f"   Error: {stderr if stderr else 'Unknown error'}", flush=True)
            self._show_manual_instructions()
            return False

        print("🔄 Updating CA trust...", flush=True)
        returncode, stdout, stderr = self._run_command(
            ["sudo", "update-ca-trust"],
            check=False,
            capture=False
        )

        if returncode != 0:
            print(f"❌ Failed to update CA trust", flush=True)
            return False

        print("✅ Certificate installed system-wide", flush=True)
        self._show_firefox_note()
        return True

    def _install_linux_arch(self) -> bool:
        """Install certificate on Arch Linux."""
        cert_dest = Path("/etc/ca-certificates/trust-source/anchors/mitmproxy.pem")

        print(f"📥 Copying certificate to {cert_dest}", flush=True)
        print("   (requires sudo)", flush=True)

        returncode, stdout, stderr = self._run_command(
            ["sudo", "cp", str(self.cert_path), str(cert_dest)],
            check=False,
            capture=False
        )

        if returncode != 0:
            print(f"❌ Failed to copy certificate", flush=True)
            if stderr and "permission denied" in stderr.lower():
                print(f"   This requires sudo privileges", flush=True)
                print(f"   Try: sudo cp {self.cert_path} {cert_dest}", flush=True)
            else:
                print(f"   Error: {stderr if stderr else 'Unknown error'}", flush=True)
            self._show_manual_instructions()
            return False

        print("🔄 Updating CA trust...", flush=True)
        returncode, stdout, stderr = self._run_command(
            ["sudo", "trust", "extract-compat"],
            check=False,
            capture=False
        )

        if returncode != 0:
            print(f"❌ Failed to update CA trust", flush=True)
            return False

        print("✅ Certificate installed system-wide", flush=True)
        self._show_firefox_note()
        return True

    def _show_firefox_note(self):
        """Show note about Firefox requiring additional setup."""
        print(flush=True)
        print("📝 Note: Firefox uses its own certificate store", flush=True)
        print("   For Firefox support, install 'libnss3-tools' and run:", flush=True)
        print(f"   $ certutil -A -d sql:$HOME/.mozilla/firefox/*.default* \\", flush=True)
        print(f"     -t 'C,,' -n '{self.CERT_NAME}' -i {self.cert_path}", flush=True)

    def _show_manual_instructions(self):
        """Show platform-specific manual installation instructions."""
        print(flush=True)
        print("=" * self.BANNER_WIDTH, flush=True)
        print("📋 MANUAL INSTALLATION INSTRUCTIONS", flush=True)
        print("=" * self.BANNER_WIDTH, flush=True)
        print(flush=True)

        if self.platform == "Darwin":
            print("macOS Manual Installation:", flush=True)
            print("1. Open Keychain Access (⌘+Space, type 'Keychain')", flush=True)
            print("2. Select 'login' keychain in left sidebar", flush=True)
            print("3. Drag and drop certificate file to keychain:", flush=True)
            print(f"   {self.cert_path}", flush=True)
            print("4. Double-click the imported certificate", flush=True)
            print("5. Expand 'Trust' section", flush=True)
            print("6. Set 'When using this certificate' to 'Always Trust'", flush=True)
            print("7. Close window and enter your password", flush=True)

        elif self.platform == "Windows":
            print("Windows Manual Installation:", flush=True)
            print("1. Double-click certificate file:", flush=True)
            print(f"   {self.cert_path}", flush=True)
            print("2. Click 'Install Certificate'", flush=True)
            print("3. Select 'Current User'", flush=True)
            print("4. Select 'Place all certificates in the following store'", flush=True)
            print("5. Click 'Browse' → Select 'Trusted Root Certification Authorities'", flush=True)
            print("6. Click 'Next' → 'Finish'", flush=True)
            print("7. Click 'Yes' on security warning", flush=True)

        elif self.platform == "Linux":
            distro = self._detect_linux_distro()
            print("Linux Manual Installation:", flush=True)
            if distro in ["debian", "ubuntu"]:
                print(f"$ sudo cp {self.cert_path} /usr/local/share/ca-certificates/mitmproxy.crt", flush=True)
                print("$ sudo update-ca-certificates", flush=True)
            elif distro in ["fedora", "rhel", "centos"]:
                print(f"$ sudo cp {self.cert_path} /etc/pki/ca-trust/source/anchors/mitmproxy.pem", flush=True)
                print("$ sudo update-ca-trust", flush=True)
            elif distro == "arch":
                print(f"$ sudo cp {self.cert_path} /etc/ca-certificates/trust-source/anchors/mitmproxy.pem", flush=True)
                print("$ sudo trust extract-compat", flush=True)
            else:
                print(f"$ sudo cp {self.cert_path} /usr/local/share/ca-certificates/mitmproxy.crt", flush=True)
                print("$ sudo update-ca-certificates", flush=True)

        print(flush=True)
        print("📖 Full guide: docs/CERTIFICATE_INSTALLATION.md", flush=True)
        print(flush=True)

    def verify(self) -> bool:
        """
        Verify certificate is installed and trusted.

        Returns:
            True if certificate is trusted, False otherwise
        """
        print("🔍 Verifying certificate installation...", flush=True)

        if not self.validate_certificate():
            return False

        if self.platform == "Darwin":
            return self._verify_macos()
        elif self.platform == "Windows":
            return self._verify_windows()
        elif self.platform == "Linux":
            return self._verify_linux()
        else:
            print(f"⚠️  Verification not supported on {self.platform}", flush=True)
            return False

    def _verify_macos(self) -> bool:
        """Verify certificate on macOS."""
        returncode, stdout, stderr = self._run_command(
            ["security", "find-certificate", "-c", self.CERT_NAME, "-p", "login.keychain"],
            check=False
        )

        if returncode != 0:
            print("❌ Certificate not found in keychain", flush=True)
            return False

        print("✅ Certificate found in keychain", flush=True)
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
            print("❌ Certificate not found in Windows trust store", flush=True)
            return False

        print("✅ Certificate found in Windows trust store", flush=True)
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
            print(f"❌ Certificate not found at {cert_path}", flush=True)
            return False

        print(f"✅ Certificate found at {cert_path}", flush=True)
        return True

    def info(self):
        """Display certificate information and installation instructions."""
        print("═" * self.BANNER_WIDTH, flush=True)
        print("   TraceTap Certificate Information", flush=True)
        print("═" * self.BANNER_WIDTH, flush=True)
        print(flush=True)

        if self.cert_path and self.cert_path.exists():
            print("✅ Certificate generated", flush=True)
            print(f"📄 Location: {self.cert_path}", flush=True)
        else:
            print("❌ Certificate not found", flush=True)
            print(f"📄 Expected location: {Path.home()}/.mitmproxy/mitmproxy-ca-cert.pem", flush=True)
            print(flush=True)
            print("Generate certificate by running TraceTap:", flush=True)
            print("$ python tracetap.py --listen 8080", flush=True)
            return

        print(f"💻 Platform: {self.platform}", flush=True)
        print(flush=True)

        self._show_manual_instructions()

        print("🔍 Verify installation:", flush=True)
        print("$ python src/tracetap/scripts/cert_manager.py verify", flush=True)
        print(flush=True)
        print("📖 Full documentation:", flush=True)
        print("   docs/CERTIFICATE_INSTALLATION.md", flush=True)
        print("   docs/TROUBLESHOOTING.md", flush=True)
        print(flush=True)
