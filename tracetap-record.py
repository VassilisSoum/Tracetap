#!/usr/bin/env python3
"""
TraceTap Record - Standalone entry point for recording UI interactions

This script provides a direct entry point for the tracetap record command,
allowing users to run the recorder without needing to use the full CLI.

Usage:
    python tracetap-record.py <url> [options]
    ./tracetap-record.py <url> [options]

For help:
    python tracetap-record.py --help
"""

import sys
from pathlib import Path

# Add src directory to Python path to allow imports
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import and run the CLI
try:
    from tracetap.cli.record import main
except ImportError as e:
    print(f"Error: Failed to import tracetap modules: {e}")
    print("Please ensure tracetap is properly installed:")
    print("  pip install -e .")
    sys.exit(1)

if __name__ == "__main__":
    main()
