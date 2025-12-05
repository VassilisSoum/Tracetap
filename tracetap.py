#!/usr/bin/env python3
"""
TraceTap - HTTP/HTTPS traffic capture proxy

This is a convenience wrapper that calls the modular implementation.
The actual implementation is in src/tracetap/capture/tracetap_main.py

Usage:
    python tracetap.py --listen 8080 --export output.json

For more information, see README.md
"""

import sys
from pathlib import Path

# Add the capture module to the path
capture_dir = Path(__file__).parent / "src" / "tracetap" / "capture"
sys.path.insert(0, str(capture_dir))

# Import and run the modular main function
from tracetap_main import main

if __name__ == '__main__':
    main()
