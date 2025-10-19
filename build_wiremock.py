#!/usr/bin/env python3
"""
Build script for tracetap2wiremock executable only
Quick build script for just the WireMock converter

Usage:
    python build_wiremock.py
"""

import subprocess
import sys
import platform
import shutil
from pathlib import Path


def get_platform_info():
    """Get platform-specific information"""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == 'windows':
        ext = '.exe'
        platform_name = 'windows'
    elif system == 'darwin':
        ext = ''
        platform_name = 'macos'
    else:
        ext = ''
        platform_name = 'linux'

    if machine in ['x86_64', 'amd64']:
        arch = 'x64'
    elif machine in ['arm64', 'aarch64']:
        arch = 'arm64'
    else:
        arch = machine

    return platform_name, arch, ext


def main():
    """Build tracetap2wiremock executable"""
    platform_name, arch, ext = get_platform_info()

    print("=" * 60)
    print(f"Building tracetap2wiremock for {platform_name}-{arch}")
    print("=" * 60)
    print()

    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',
        '--name', 'tracetap2wiremock',
        '--clean',
        '--noconfirm',
        '--console',
        '--strip',
        'tracetap2wiremock.py'
    ]

    print(f"Running: {' '.join(cmd)}")
    print()

    try:
        subprocess.run(cmd, check=True)
        print("\n✓ Build successful!")

        # Create release directory
        release_dir = Path('release')
        release_dir.mkdir(exist_ok=True)

        # Move executable
        exe_name = f'tracetap2wiremock{ext}'
        release_name = f'tracetap2wiremock-{platform_name}-{arch}{ext}'

        src = Path('dist') / exe_name
        dst = release_dir / release_name

        if src.exists():
            shutil.copy2(src, dst)
            print(f"✓ Executable: {dst}")
            print(f"  Size: {dst.stat().st_size / 1024 / 1024:.1f} MB")

            # Make executable on Unix
            if platform_name != 'windows':
                dst.chmod(0o755)

            return 0
        else:
            print(f"✗ Error: Expected executable not found at {src}")
            return 1

    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())