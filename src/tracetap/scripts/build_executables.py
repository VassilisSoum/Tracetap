#!/usr/bin/env python3
"""
Build script for creating standalone executables
Builds TraceTap and tracetap2wiremock for the current platform (Windows/Mac/Linux)

This script uses PyInstaller to create single-file executables that can be
distributed without requiring Python or dependencies to be installed.
"""

import subprocess
import sys
import platform
import shutil
from pathlib import Path
import os
from typing import Tuple, List


# ============================================================================
# UNICODE DETECTION & OUTPUT HELPERS
# ============================================================================

def _supports_unicode_stdout() -> bool:
    """Check if stdout supports Unicode characters."""
    enc = sys.stdout.encoding or ""
    return "utf" in enc.lower()


_USE_UNICODE = _supports_unicode_stdout()

# Unicode symbols if supported, ASCII fallback otherwise
OK = "✓" if _USE_UNICODE else "OK"
FAIL = "✗" if _USE_UNICODE else "X"
INFO = "ℹ" if _USE_UNICODE else "i"


def info(msg: str) -> None:
    """Print info message."""
    print(f"{INFO} {msg}" if _USE_UNICODE else msg)


def ok(msg: str) -> None:
    """Print success message."""
    print(f"{OK} {msg}")


def err(msg: str) -> None:
    """Print error message."""
    print(f"{FAIL} {msg}")


# ============================================================================
# PLATFORM DETECTION
# ============================================================================

def get_platform_info() -> Tuple[str, str, str]:
    """
    Get platform-specific information.

    Returns:
        Tuple of (platform_name, architecture, executable_extension)
        Examples:
        - Linux: ('linux', 'x64', '')
        - macOS Intel: ('macos', 'x64', '')
        - macOS M1: ('macos', 'arm64', '')
        - Windows: ('windows', 'x64', '.exe')
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Determine platform name and extension
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


# ============================================================================
# BUILD FUNCTIONS
# ============================================================================

def build_executable(script_name: str, output_name: str) -> bool:
    """
    Build a single executable using PyInstaller.

    Args:
        script_name: Source Python script (e.g., 'tracetap.py')
        output_name: Output executable name (e.g., 'tracetap')

    Returns:
        True if build succeeded, False otherwise
    """
    platform_name, arch, ext = get_platform_info()

    info(f"Building {output_name} from {script_name}...")

    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',  # Single executable file
        '--name', output_name,  # Output name
        '--clean',  # Clean PyInstaller cache
        '--noconfirm',  # Overwrite without asking
        '--console',  # Console application (not GUI)
        '--strip',  # Strip symbols (smaller size)
        script_name
    ]

    # Platform-specific options
    if platform_name == 'windows':
        # Windows-specific: no icon for now
        pass

    info(f"  Command: {' '.join(cmd)}")

    try:
        # Run PyInstaller
        subprocess.run(cmd, check=True, capture_output=True)
        ok(f"  Build successful: {output_name}")

        # Create release directory
        release_dir = Path('release')
        release_dir.mkdir(exist_ok=True)

        # Move executable to release directory with platform-specific name
        exe_name = f'{output_name}{ext}'
        release_name = f'{output_name}-{platform_name}-{arch}{ext}'

        src = Path('dist') / exe_name
        dst = release_dir / release_name

        if src.exists():
            shutil.copy2(src, dst)
            ok(f"  Executable created: {dst}")

            # Show file size
            size_mb = dst.stat().st_size / 1024 / 1024
            info(f"    Size: {size_mb:.1f} MB")

            # Make executable on Unix systems (Linux/macOS)
            if platform_name != 'windows':
                dst.chmod(0o755)
                info(f"    Permissions: 755 (executable)")

            return True
        else:
            err(f"  Error: Expected executable not found at {src}")
            return False

    except subprocess.CalledProcessError as e:
        err(f"  Build failed for {output_name}")
        # Show stderr if available
        if e.stderr:
            err(f"  Error output: {e.stderr.decode('utf-8', errors='replace')}")
        return False
    except Exception as e:
        err(f"  Unexpected error: {e}")
        return False


def build_all_executables() -> bool:
    """
    Build all TraceTap executables.

    Note: We only build TraceTap (the proxy) as an executable because it has
    complex dependencies (mitmproxy). The tracetap2wiremock tool is distributed
    as a Python script since it has zero dependencies and works across all
    platforms without GLIBC compatibility issues.

    Returns:
        True if all builds succeeded, False if any failed
    """
    platform_name, arch, ext = get_platform_info()

    print("=" * 70)
    info(f"Building TraceTap Executables for {platform_name}-{arch}")
    print("=" * 70)
    info(f"Python: {sys.version.split()[0]}")
    info(f"Platform: {platform.platform()}")
    print()

    # List of executables to build
    # Note: tracetap2wiremock is NOT built as an executable to avoid GLIBC
    # compatibility issues on Linux. It's distributed as a Python script instead.
    builds = [
        ('tracetap_main.py', 'tracetap'),
    ]

    results = []
    for script, name in builds:
        # Check if source file exists
        if not Path(script).exists():
            err(f"Source file not found: {script}")
            results.append(False)
            continue

        print()
        print("-" * 70)
        success = build_executable(script, name)
        results.append(success)
        print("-" * 70)

    # Summary
    print()
    print("=" * 70)
    info("Build Summary")
    print("=" * 70)

    for (script, name), success in zip(builds, results):
        status = OK if success else FAIL
        print(f"  {status} {name:<25} from {script}")

    all_success = all(results)

    print()
    if all_success:
        ok(f"All builds completed successfully!")
        info(f"Output directory: {Path('release').absolute()}")
        print()
        info("Note: tracetap2wiremock is distributed as a Python script (tracetap2wiremock.py)")
        info("      No dependencies needed - works on all platforms!")
    else:
        err(f"Some builds failed. Check error messages above.")

    return all_success


def clean_build_files() -> None:
    """
    Clean up build artifacts created by PyInstaller.

    Removes:
    - build/ directory (PyInstaller build files)
    - dist/ directory (intermediate executables)
    - __pycache__/ directories (Python bytecode)
    - *.spec files (PyInstaller spec files)
    """
    info("Cleaning up build artifacts...")

    # Directories to remove
    dirs_to_remove = ['build', 'dist', '__pycache__']

    # Files to remove (glob patterns)
    files_to_remove = ['*.spec']

    # Remove directories
    for dir_name in dirs_to_remove:
        path = Path(dir_name)
        if path.exists():
            shutil.rmtree(path)
            info(f"  Removed directory: {dir_name}/")

    # Remove spec files
    for pattern in files_to_remove:
        for file_path in Path('../../..').glob(pattern):
            file_path.unlink()
            info(f"  Removed file: {file_path}")

    ok("Cleanup complete")


def list_release_files() -> None:
    """List all files in the release directory."""
    release_dir = Path('release')

    if not release_dir.exists():
        info("No release directory found")
        return

    files = list(release_dir.glob('*'))

    if not files:
        info("Release directory is empty")
        return

    print()
    info("Release directory contents:")
    print()

    for file in sorted(files):
        if file.is_file():
            size_mb = file.stat().st_size / 1024 / 1024
            print(f"  {file.name:<40} {size_mb:>8.1f} MB")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main() -> int:
    """
    Main entry point for build script.

    Returns:
        0 if successful, 1 if any builds failed
    """
    # Build all executables
    success = build_all_executables()

    if success:
        # List created files
        list_release_files()

        # Handle cleanup
        # Detect CI or non-interactive environments
        non_interactive = not sys.stdin.isatty() or os.environ.get("CI") == "true"
        auto_clean = os.environ.get("AUTO_CLEAN", "").lower() in ("1", "true", "yes")

        print()
        if auto_clean:
            # Auto-cleanup if environment variable set
            clean_build_files()
        elif non_interactive:
            # Skip cleanup in CI/non-interactive mode
            info("Non-interactive mode: Skipping cleanup of build artifacts")
            info("Set AUTO_CLEAN=true to enable automatic cleanup")
        else:
            # Interactive mode: ask user
            info("Build artifacts (build/, dist/, *.spec) can be cleaned up")
            try:
                response = input("Clean up build artifacts? (y/N): ").lower().strip()
            except (EOFError, KeyboardInterrupt):
                print()
                response = 'n'

            if response == 'y':
                print()
                clean_build_files()

    # Final status
    print()
    print("=" * 70)
    if success:
        ok("Build complete! Check the release/ directory")
    else:
        err("Build failed. Check the error messages above.")
    print("=" * 70)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())