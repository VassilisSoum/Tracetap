#!/usr/bin/env python3
"""
Basic test runner to verify test syntax and imports without pytest.
This helps verify tests are correct even when pytest isn't installed.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src" / "tracetap"))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        from cert_installer import CertificateInstaller
        print("✅ cert_installer module imports successfully")
    except Exception as e:
        print(f"❌ Failed to import cert_installer: {e}")
        return False

    try:
        import tests.test_cert_installer as test_module
        print("✅ test_cert_installer module imports successfully")
    except Exception as e:
        if "pytest" in str(e):
            print(f"⚠️  test_cert_installer requires pytest (expected): {e}")
            print("   This is normal - install pytest to run full test suite")
            # Don't fail the test since this is expected
        else:
            print(f"❌ Failed to import test_cert_installer: {e}")
            return False

    return True

def test_basic_functionality():
    """Test basic certificate installer functionality."""
    print("\nTesting basic functionality...")

    try:
        from cert_installer import CertificateInstaller
        import platform

        # Test platform detection
        installer = CertificateInstaller()
        assert installer.platform in ["Darwin", "Windows", "Linux"]
        print(f"✅ Platform detection works: {installer.platform}")

        # Test with None cert_path (will try to auto-detect)
        installer_none = CertificateInstaller(cert_path=None)
        # When None, it tries to find cert in default location
        # So cert_path will either be found or remain None
        print(f"✅ None cert_path handling works (auto-detect: {installer_none.cert_path})")

        # Test verbose mode
        installer_verbose = CertificateInstaller(verbose=True)
        assert installer_verbose.verbose is True
        print("✅ Verbose mode works")

        return True
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_validation():
    """Test certificate validation logic."""
    print("\nTesting validation logic...")

    try:
        from cert_installer import CertificateInstaller
        from pathlib import Path
        import tempfile

        # Test with missing certificate
        installer = CertificateInstaller(cert_path=Path("/nonexistent/cert.pem"))
        result = installer.validate_certificate()
        assert result is False
        print("✅ Missing certificate validation works")

        # Test with valid certificate format
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write("-----BEGIN CERTIFICATE-----\n")
            f.write("TEST CERTIFICATE CONTENT\n")
            f.write("-----END CERTIFICATE-----\n")
            cert_path = Path(f.name)

        try:
            installer = CertificateInstaller(cert_path=cert_path)
            result = installer.validate_certificate()
            assert result is True
            print("✅ Valid certificate format validation works")
        finally:
            cert_path.unlink()

        return True
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all basic tests."""
    print("=" * 60)
    print("TraceTap Basic Test Runner")
    print("=" * 60)
    print()

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Basic Functionality", test_basic_functionality()))
    results.append(("Validation", test_validation()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:.<40} {status}")

    print()
    print(f"Total: {passed}/{total} test suites passed")
    print()

    if passed == total:
        print("✅ All basic tests passed!")
        print()
        print("To run full test suite with pytest:")
        print("  pip install pytest pytest-mock")
        print("  pytest tests/test_cert_installer.py -v")
        return 0
    else:
        print("❌ Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
