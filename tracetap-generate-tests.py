#!/usr/bin/env python3
"""
TraceTap Test Generator CLI

Generates Playwright tests from recorded sessions using AI.

Usage:
    python tracetap-generate-tests.py <session-dir> -o <output-file> [options]
    ./tracetap-generate-tests.py <session-dir> -o <output-file> [options]

For help:
    python tracetap-generate-tests.py --help
"""

import sys
from pathlib import Path

# Add src directory to Python path to allow imports
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import and run the CLI
try:
    from tracetap.cli.generate_tests import main
except ImportError as e:
    print(f"Error: Failed to import tracetap modules: {e}")
    print("Please ensure tracetap is properly installed:")
    print("  pip install -e .")
    sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
