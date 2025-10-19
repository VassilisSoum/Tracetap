#!/usr/bin/env python3
"""
Build script for creating standalone executables
Builds for the current platform (Windows/Mac/Linux)
"""

import subprocess
import sys
import platform
import shutil
from pathlib import Path
import os


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

    # Determine architecture
    if machine in ['x86_64', 'amd64']:
        arch = 'x64'
    elif machine in ['arm64', 'aarch64']:
        arch = 'arm64'
    else:
        arch = machine

    return platform_name, arch, ext


def build_executable():
    """Build the executable using PyInstaller"""
    platform_name, arch, ext = get_platform_info()

    print(f"Building TraceTap for {platform_name}-{arch}...")
    print(f"Python: {sys.version}")
    print(f"Platform: {platform.platform()}")
    print()

    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',  # Single executable
        '--name', 'tracetap',  # Output name
        '--clean',  # Clean cache
        '--noconfirm',  # Overwrite without asking
        '--console',  # Console application
        '--strip',  # Strip symbols (smaller size)
        'tracetap.py'
    ]

    # Add platform-specific options
    if platform_name == 'windows':
        cmd.extend([
            '--icon', 'NONE',  # No icon for now
        ])

    print(f"Running: {' '.join(cmd)}")
    print()

    try:
        subprocess.run(cmd, check=True)
        print("\n✓ Build successful!")

        # Create release directory
        release_dir = Path('release')
        release_dir.mkdir(exist_ok=True)

        # Move executable to release directory with platform name
        exe_name = f'tracetap{ext}'
        release_name = f'tracetap-{platform_name}-{arch}{ext}'

        src = Path('dist') / exe_name
        dst = release_dir / release_name

        if src.exists():
            shutil.copy2(src, dst)
            print(f"\n✓ Executable created: {dst}")
            print(f"  Size: {dst.stat().st_size / 1024 / 1024:.1f} MB")

            # Make executable on Unix systems
            if platform_name != 'windows':
                dst.chmod(0o755)

            return True
        else:
            print(f"\n✗ Error: Expected executable not found at {src}")
            return False

    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False


def clean_build_files():
    """Clean up build artifacts"""
    print("\nCleaning up build artifacts...")

    dirs_to_remove = ['build', 'dist', '__pycache__']
    files_to_remove = ['tracetap.spec']

    for dir_name in dirs_to_remove:
        path = Path(dir_name)
        if path.exists():
            shutil.rmtree(path)
            print(f"  Removed: {dir_name}/")

    for file_name in files_to_remove:
        path = Path(file_name)
        if path.exists():
            path.unlink()
            print(f"  Removed: {file_name}")


if __name__ == '__main__':
    print("=" * 60)
    print("TraceTap Executable Builder")
    print("=" * 60)
    print()

    success = build_executable()

    if success:
        # Detect CI or non-interactive environments
        non_interactive = not sys.stdin.isatty() or os.environ.get("CI") == "true"
        auto_clean = os.environ.get("AUTO_CLEAN", "").lower() in ("1", "true", "yes")

        if auto_clean:
            clean_build_files()
        elif non_interactive:
            print("\nNon-interactive mode detected; skipping cleanup of build artifacts.")
        else:
            print("\nBuild artifacts (build/, dist/) can be cleaned up.")
            try:
                response = input("Clean up build artifacts? (y/n): ").lower().strip()
            except EOFError:
                response = 'n'
            if response == 'y':
                clean_build_files()

    print("\n" + "=" * 60)
    if success:
        print("✓ Build complete! Check the release/ directory")
    else:
        print("✗ Build failed. Check the error messages above.")
    print("=" * 60)

    sys.exit(0 if success else 1)
