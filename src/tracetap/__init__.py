"""
TraceTap - HTTP Traffic Capture and Replay Tool

A comprehensive toolkit for capturing, analyzing, and replaying HTTP traffic.
"""

__version__ = "1.0.0"


def main():
    """Main CLI entry point for TraceTap."""
    import sys

    print(f"TraceTap v{__version__}")
    print("\nAvailable commands:")
    print("  tracetap-record           - Record UI interactions with network traffic")
    print("  tracetap-generate-tests   - Generate Playwright tests from recordings")
    print("  tracetap-quickstart       - Interactive quickstart guide")
    print("\nExamples:")
    print("  tracetap-record https://myapp.com -n login-test")
    print("  tracetap-generate-tests recordings/<session-id> -o tests/")
    print("\nFor help on a specific command:")
    print("  tracetap-record --help")
    print("  tracetap-generate-tests --help")
    print("\nDocumentation: https://github.com/VassilisSoum/tracetap")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
