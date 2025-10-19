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

def _supports_unicode_stdout() -> bool:
    enc = sys.stdout.encoding or ""
    return "utf" in enc.lower()


_USE_UNICODE = _supports_unicode_stdout()

OK = "✓" if _USE_UNICODE else "OK"
FAIL = "✗" if _USE_UNICODE else "X"

def info(msg: str) -> None:
    print(msg)

def ok(msg: str) -> None:
    print(f"{OK} {msg}")

def err(msg: str) -> None:
    print(f"{FAIL} {msg}")


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

    info(f"Building TraceTap for {platform_name}-{arch}...")
    info(f"Python: {sys.version}")
    info(f"Platform: {platform.platform()}")
    print()

    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',          # Single executable
        '--name', 'tracetap', # Output name
        '--clean',            # Clean cache
        '--noconfirm',        # Overwrite without asking
        '--console',          # Console application
        '--strip',            # Strip symbols (smaller size; no-op on Windows)
        'tracetap.py'
    ]

    info(f"Running: {' '.join(cmd)}")
    print()

    try:
        subprocess.run(cmd, check=True)
        ok("Build successful!")

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
            ok(f"Executable created: {dst}")
            info(f"  Size: {dst.stat().st_size / 1024 / 1024:.1f} MB")

            # Make executable on Unix systems
            if platform_name != 'windows':
                dst.chmod(0o755)

            return True
        else:
            err(f"Error: Expected executable not found at {src}")
            return False

    except subprocess.CalledProcessError as e:
        err(f"Build failed: {e}")
        return False
    except Exception as e:
        err(f"Unexpected error: {e}")
        return False


def clean_build_files():
    """Clean up build artifacts"""
    info("Cleaning up build artifacts...")

    dirs_to_remove = ['build', 'dist', '__pycache__']
    files_to_remove = ['tracetap.spec']

    for dir_name in dirs_to_remove:
        path = Path(dir_name)
        if path.exists():
            shutil.rmtree(path)
            info(f"  Removed: {dir_name}/")

    for file_name in files_to_remove:
        path = Path(file_name)
        if path.exists():
            path.unlink()
            info(f"  Removed: {file_name}")


if __name__ == '__main__':
    print("=" * 60)
    info("TraceTap Executable Builder")
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
            info("Non-interactive mode detected; skipping cleanup of build artifacts.")
        else:
            info("Build artifacts (build/, dist/) can be cleaned up.")
            try:
                response = input("Clean up build artifacts? (y/n): ").lower().strip()
            except EOFError:
                response = 'n'
            if response == 'y':
                clean_build_files()

    print()
    print("=" * 60)
    if success:
        ok("Build complete! Check the release/ directory")
    else:
        err("Build failed. Check the error messages above.")
    print("=" * 60)

    sys.exit(0 if success else 1)
