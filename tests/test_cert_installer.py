"""
Tests for certificate installer module.

Tests platform detection, certificate validation, installation logic,
and error handling without making actual system changes.
"""

import os
import platform
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "tracetap"))

from cert_installer import CertificateInstaller


# Module-level fixtures accessible to all test classes
@pytest.fixture
def mock_cert_file(tmp_path):
    """Create a mock certificate file for testing."""
    cert_path = tmp_path / ".mitmproxy" / "mitmproxy-ca-cert.pem"
    cert_path.parent.mkdir(parents=True)

    # Valid PEM certificate format
    cert_content = """-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKL0UG+mRKe4MA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
aWRnaXRzIFB0eSBMdGQwHhcNMjMwMTAxMDAwMDAwWhcNMjQwMTAxMDAwMDAwWjBF
-----END CERTIFICATE-----"""

    cert_path.write_text(cert_content)
    return cert_path


@pytest.fixture
def installer_with_mock_cert(mock_cert_file):
    """Create installer with mocked certificate."""
    return CertificateInstaller(cert_path=mock_cert_file, verbose=True)


class TestCertificateInstaller:
    """Test suite for CertificateInstaller class."""

    def test_platform_detection(self):
        """Test that platform is correctly detected."""
        installer = CertificateInstaller()
        assert installer.platform in ["Darwin", "Windows", "Linux"]
        assert installer.platform == platform.system()

    def test_cert_path_auto_detection(self, monkeypatch, mock_cert_file):
        """Test automatic certificate path detection."""
        # Mock Path.home() to return temp directory
        monkeypatch.setattr(Path, "home", lambda: mock_cert_file.parent.parent)

        installer = CertificateInstaller()
        assert installer.cert_path == mock_cert_file

    def test_cert_path_manual_specification(self, mock_cert_file):
        """Test manually specifying certificate path."""
        installer = CertificateInstaller(cert_path=mock_cert_file)
        assert installer.cert_path == mock_cert_file

    def test_verbose_mode(self, mock_cert_file):
        """Test verbose mode enables logging."""
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)
        assert installer.verbose is True

    def test_validate_certificate_success(self, installer_with_mock_cert):
        """Test certificate validation with valid certificate."""
        assert installer_with_mock_cert.validate_certificate() is True

    def test_validate_certificate_missing_file(self, tmp_path):
        """Test certificate validation when file doesn't exist."""
        nonexistent_path = tmp_path / "nonexistent.pem"
        installer = CertificateInstaller(cert_path=nonexistent_path)

        assert installer.validate_certificate() is False

    def test_validate_certificate_invalid_format(self, tmp_path):
        """Test certificate validation with invalid PEM format."""
        invalid_cert = tmp_path / "invalid.pem"
        invalid_cert.write_text("This is not a certificate")

        installer = CertificateInstaller(cert_path=invalid_cert)
        assert installer.validate_certificate() is False

    def test_validate_certificate_empty_file(self, tmp_path):
        """Test certificate validation with empty file."""
        empty_cert = tmp_path / "empty.pem"
        empty_cert.write_text("")

        installer = CertificateInstaller(cert_path=empty_cert)
        assert installer.validate_certificate() is False

    @patch('subprocess.run')
    def test_run_command_success(self, mock_run, installer_with_mock_cert):
        """Test successful command execution."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="success",
            stderr=""
        )

        returncode, stdout, stderr = installer_with_mock_cert._run_command(
            ["echo", "test"]
        )

        assert returncode == 0
        assert stdout == "success"
        assert stderr == ""

    @patch('subprocess.run')
    def test_run_command_failure(self, mock_run, installer_with_mock_cert):
        """Test command execution failure."""
        from subprocess import CalledProcessError

        mock_run.side_effect = CalledProcessError(
            returncode=1,
            cmd=["false"],
            output="",
            stderr="error"
        )

        returncode, stdout, stderr = installer_with_mock_cert._run_command(
            ["false"],
            check=False
        )

        assert returncode == 1

    @patch('subprocess.run')
    def test_run_command_not_found(self, mock_run, installer_with_mock_cert):
        """Test command execution when command not found."""
        mock_run.side_effect = FileNotFoundError()

        returncode, stdout, stderr = installer_with_mock_cert._run_command(
            ["nonexistent_command"]
        )

        assert returncode == 127
        assert "Command not found" in stderr


class TestLinuxDistroDetection:
    """Test Linux distribution detection."""

    @pytest.fixture
    def installer(self):
        return CertificateInstaller()

    def test_detect_debian(self, installer):
        """Test Debian detection."""
        def path_factory(path_str):
            mock_path = MagicMock()
            mock_path.exists.return_value = '/etc/debian_version' in str(path_str)
            return mock_path

        with patch('cert_installer.Path', side_effect=path_factory):
            distro = installer._detect_linux_distro()
            assert distro == "debian"

    def test_detect_fedora(self, installer):
        """Test Fedora detection."""
        def path_factory(path_str):
            mock_path = MagicMock()
            mock_path.exists.return_value = '/etc/fedora-release' in str(path_str)
            return mock_path

        with patch('cert_installer.Path', side_effect=path_factory):
            distro = installer._detect_linux_distro()
            assert distro == "fedora"

    def test_detect_arch(self, installer):
        """Test Arch Linux detection."""
        def path_factory(path_str):
            mock_path = MagicMock()
            mock_path.exists.return_value = '/etc/arch-release' in str(path_str)
            return mock_path

        with patch('cert_installer.Path', side_effect=path_factory):
            distro = installer._detect_linux_distro()
            assert distro == "arch"

    def test_detect_unknown(self, installer):
        """Test unknown distribution handling."""
        with patch.object(Path, 'exists', return_value=False):
            with patch('builtins.open', side_effect=FileNotFoundError()):
                distro = installer._detect_linux_distro()
                assert distro == "unknown"


class TestMacOSInstallation:
    """Test macOS-specific installation logic."""

    @patch('subprocess.run')
    def test_install_macos_success(self, mock_run, mock_cert_file):
        """Test successful macOS installation."""
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)

        # Mock security commands
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = installer._install_macos()

        # Should call security commands
        assert mock_run.called
        assert result is True

    @patch('subprocess.run')
    def test_install_macos_certificate_exists(self, mock_run, mock_cert_file):
        """Test macOS installation when certificate already exists."""
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)

        # First call: find-certificate (exists)
        # Second call: delete-certificate
        # Third call: add-trusted-cert
        # Fourth call: find-certificate (verify)
        mock_run.side_effect = [
            Mock(returncode=0, stdout="found", stderr=""),  # exists
            Mock(returncode=0, stdout="", stderr=""),       # delete
            Mock(returncode=0, stdout="", stderr=""),       # add
            Mock(returncode=0, stdout="found", stderr="")   # verify
        ]

        result = installer._install_macos()
        assert result is True

    @patch('subprocess.run')
    def test_install_macos_add_cert_fails(self, mock_run, mock_cert_file):
        """Test macOS installation when adding certificate fails."""
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)

        mock_run.side_effect = [
            Mock(returncode=1, stdout="", stderr="not found"),  # find (not exists)
            Mock(returncode=1, stdout="", stderr="access denied")  # add fails
        ]

        result = installer._install_macos()
        assert result is False


class TestWindowsInstallation:
    """Test Windows-specific installation logic."""

    @patch('subprocess.run')
    def test_install_windows_success(self, mock_run, mock_cert_file):
        """Test successful Windows installation."""
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)

        mock_run.return_value = Mock(
            returncode=0,
            stdout="Certificate installed successfully",
            stderr=""
        )

        result = installer._install_windows()

        # Should call PowerShell
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "powershell" in call_args
        assert result is True

    @patch('subprocess.run')
    def test_install_windows_powershell_failure(self, mock_run, mock_cert_file):
        """Test Windows installation when PowerShell fails."""
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)

        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Access denied"
        )

        result = installer._install_windows()
        assert result is False


class TestLinuxInstallation:
    """Test Linux-specific installation logic."""

    @patch('subprocess.run')
    def test_install_linux_debian_success(self, mock_run, mock_cert_file):
        """Test successful Debian/Ubuntu installation."""
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)

        # Mock distribution detection
        with patch.object(installer, '_detect_linux_distro', return_value='debian'):
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            result = installer._install_linux()

            assert mock_run.called
            assert result is True

    @patch('subprocess.run')
    def test_install_linux_fedora_success(self, mock_run, mock_cert_file):
        """Test successful Fedora/RHEL installation."""
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)

        with patch.object(installer, '_detect_linux_distro', return_value='fedora'):
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            result = installer._install_linux()
            assert result is True

    @patch('subprocess.run')
    def test_install_linux_arch_success(self, mock_run, mock_cert_file):
        """Test successful Arch Linux installation."""
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)

        with patch.object(installer, '_detect_linux_distro', return_value='arch'):
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            result = installer._install_linux()
            assert result is True

    @patch('subprocess.run')
    def test_install_linux_copy_fails(self, mock_run, mock_cert_file):
        """Test Linux installation when copying certificate fails."""
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)

        with patch.object(installer, '_detect_linux_distro', return_value='debian'):
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Permission denied")

            result = installer._install_linux()
            assert result is False


class TestVerification:
    """Test certificate verification logic."""

    @patch('subprocess.run')
    def test_verify_macos_success(self, mock_run, mock_cert_file):
        """Test successful macOS verification."""
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)
        mock_run.return_value = Mock(returncode=0, stdout="found", stderr="")

        result = installer._verify_macos()
        assert result is True

    @patch('subprocess.run')
    def test_verify_macos_not_found(self, mock_run, mock_cert_file):
        """Test macOS verification when certificate not found."""
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="not found")

        result = installer._verify_macos()
        assert result is False

    @patch('subprocess.run')
    def test_verify_windows_success(self, mock_run, mock_cert_file):
        """Test successful Windows verification."""
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)
        mock_run.return_value = Mock(returncode=0, stdout="Found", stderr="")

        result = installer._verify_windows()
        assert result is True

    def test_verify_linux_success(self, mock_cert_file):
        """Test successful Linux verification."""
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)

        with patch.object(installer, '_detect_linux_distro', return_value='debian'):
            with patch.object(Path, 'exists', return_value=True):
                result = installer._verify_linux()
                assert result is True

    def test_verify_linux_not_found(self, mock_cert_file):
        """Test Linux verification when certificate not found."""
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)

        with patch.object(installer, '_detect_linux_distro', return_value='debian'):
            with patch.object(Path, 'exists', return_value=False):
                result = installer._verify_linux()
                assert result is False


class TestManualInstructions:
    """Test manual installation instruction generation."""

    @patch('platform.system')
    def test_manual_instructions_macos(self, mock_system, mock_cert_file, capsys):
        """Test macOS manual instructions are displayed."""
        mock_system.return_value = "Darwin"
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)
        installer._show_manual_instructions()

        captured = capsys.readouterr()
        assert "macOS Manual Installation" in captured.out
        assert "Keychain Access" in captured.out

    @patch('platform.system')
    def test_manual_instructions_windows(self, mock_system, mock_cert_file, capsys):
        """Test Windows manual instructions are displayed."""
        mock_system.return_value = "Windows"
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)
        installer._show_manual_instructions()

        captured = capsys.readouterr()
        assert "Windows Manual Installation" in captured.out
        assert "Install Certificate" in captured.out

    @patch('platform.system')
    def test_manual_instructions_linux(self, mock_system, mock_cert_file, capsys):
        """Test Linux manual instructions are displayed."""
        mock_system.return_value = "Linux"
        installer = CertificateInstaller(cert_path=mock_cert_file, verbose=True)

        with patch.object(installer, '_detect_linux_distro', return_value='debian'):
            installer._show_manual_instructions()

            captured = capsys.readouterr()
            assert "Linux Manual Installation" in captured.out
            assert "update-ca-certificates" in captured.out


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_installer_without_cert_path(self, tmp_path, monkeypatch):
        """Test installer when certificate doesn't exist."""
        # Mock home to non-existent location
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "nonexistent")

        installer = CertificateInstaller()
        assert installer.cert_path is None

    def test_validate_with_none_cert_path(self, monkeypatch, capsys):
        """Test validation when cert_path is None."""
        # Mock _find_certificate to ensure cert_path stays None
        monkeypatch.setattr(CertificateInstaller, '_find_certificate', lambda self: None)

        installer = CertificateInstaller(cert_path=None)
        assert installer.cert_path is None  # Verify cert_path is None

        result = installer.validate_certificate()

        # Should print error message
        captured = capsys.readouterr()
        assert "Certificate file not found" in captured.out
        assert result is False

    @patch('platform.system')
    def test_install_unsupported_platform(self, mock_system, mock_cert_file):
        """Test installation on unsupported platform."""
        mock_system.return_value = "UnknownOS"
        installer = CertificateInstaller(cert_path=mock_cert_file)

        result = installer.install()
        assert result is False

    def test_info_without_certificate(self, tmp_path, monkeypatch, capsys):
        """Test info display when certificate doesn't exist."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "nonexistent")

        installer = CertificateInstaller()
        installer.info()

        captured = capsys.readouterr()
        assert "Certificate not found" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
