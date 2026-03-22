"""
Playwright codegen-based interaction recorder.

This module provides functionality to record user interactions using Playwright's
codegen tool, which properly captures manual interactions (mouse clicks, keyboard
input) unlike the trace API which only captures programmatic actions.

Key features:
- Records REAL manual user interactions (not just API calls)
- Uses Playwright codegen to generate Python code
- Parses generated code to extract actions
- Integrates with mitmproxy for network capture
- Provides same interface as TraceRecorder for drop-in replacement
- HYBRID MODE: Combines codegen actions with trace timestamps for accurate correlation

How it works:
1. Launches `playwright codegen` subprocess with tracing enabled
2. User interacts manually with the browser
3. Codegen generates Python code representing those actions
4. Trace captures real timestamps for those actions
5. CodegenParser merges actions with timestamps
6. Events are converted to TraceTap format with REAL timestamps

Reference: playwright codegen --help
"""

import subprocess
import tempfile
import logging
import signal
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from playwright.async_api import async_playwright
from .codegen_parser import CodegenParser


logger = logging.getLogger(__name__)


@dataclass
class CodegenOptions:
    """Configuration options for codegen recording."""

    headless: bool = False  # Not applicable to codegen (always headed)
    target: str = 'python-async'  # Code generation target
    viewport_width: int = 1920
    viewport_height: int = 1080
    device: Optional[str] = None  # Optional device emulation


class CodegenRecorder:
    """Records UI interactions using Playwright codegen.

    This class uses Playwright's codegen tool to record manual user interactions.
    Unlike TraceRecorder which uses the tracing API (only captures programmatic
    actions), codegen properly records clicks, typing, and other manual interactions.

    The recorded actions are captured as generated Python code, which is then
    parsed to extract TraceTap events.

    Example:
        recorder = CodegenRecorder(CodegenOptions())
        actions = await recorder.record("https://example.com", proxy="http://localhost:8888")
        print(f"Recorded {len(actions)} user actions")
    """

    def __init__(self, options: Optional[CodegenOptions] = None):
        """Initialize the codegen recorder.

        Args:
            options: Recording configuration options
        """
        self.options = options or CodegenOptions()
        self.process: Optional[subprocess.Popen] = None
        self.output_file: Optional[tempfile.NamedTemporaryFile] = None
        self.trace_file: Optional[Path] = None
        self.parser = CodegenParser()

        # Playwright instance for tracing
        self.playwright = None
        self.browser = None
        self.context = None

    async def start_recording(self, url: str, proxy: Optional[str] = None) -> None:
        """Start recording user interactions at the given URL.

        Launches Playwright codegen with the target URL AND starts tracing
        to capture real timestamps. The user can then interact manually
        and we'll capture both actions (codegen) and timestamps (trace).

        Args:
            url: The URL to navigate to and begin recording
            proxy: Optional proxy server URL (e.g., "http://localhost:8888")

        Raises:
            RuntimeError: If recording is already in progress or codegen fails to start
        """
        if self.process is not None:
            raise RuntimeError("Recording already in progress. Call stop_recording() first.")

        logger.info("🎬 Starting Playwright codegen recorder with tracing...")
        logger.info(f"   URL: {url}")
        logger.info(f"   Target: {self.options.target}")
        if proxy:
            logger.info(f"   Proxy: {proxy}")

        # Create temporary files for generated code and trace
        self.output_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            prefix='tracetap_codegen_',
            delete=False
        )
        output_path = self.output_file.name
        self.output_file.close()  # Close so codegen can write to it

        # Create trace file path
        self.trace_file = Path(output_path).parent / f"{Path(output_path).stem}_trace.zip"

        logger.info(f"   Codegen output: {output_path}")
        logger.info(f"   Trace output: {self.trace_file}")

        # Start Playwright with tracing for timestamp capture
        try:
            self.playwright = await async_playwright().start()
            browser_type = self.playwright.chromium  # Use chromium by default

            # Launch browser
            launch_options = {}
            self.browser = await browser_type.launch(**launch_options)

            # Create context with tracing enabled
            context_options = {
                "viewport": {
                    "width": self.options.viewport_width,
                    "height": self.options.viewport_height
                },
                "ignore_https_errors": True,
            }

            if proxy:
                context_options["proxy"] = {"server": proxy}

            self.context = await self.browser.new_context(**context_options)

            # Start tracing to capture real timestamps
            await self.context.tracing.start(
                screenshots=True,
                snapshots=True,
                sources=True
            )

            logger.info("   Tracing started for timestamp capture")

        except Exception as e:
            await self._cleanup_playwright()
            raise RuntimeError(f"Failed to start Playwright tracing: {e}")

        # Build codegen command
        cmd = [
            'playwright',
            'codegen',
            '--target', self.options.target,
            '--output', output_path,
        ]

        # Add viewport settings
        if self.options.viewport_width and self.options.viewport_height:
            cmd.extend([
                '--viewport-size',
                f'{self.options.viewport_width},{self.options.viewport_height}'
            ])

        # Add device emulation if specified
        if self.options.device:
            cmd.extend(['--device', self.options.device])

        # Add proxy if provided
        if proxy:
            cmd.extend(['--proxy-server', proxy])

        # Add URL
        cmd.append(url)

        logger.info(f"   Command: {' '.join(cmd)}")

        try:
            # Launch codegen process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )

            # Wait a moment for codegen to start
            time.sleep(2)

            # Check if process started successfully
            if self.process.poll() is not None:
                _, stderr = self.process.communicate()
                await self._cleanup_playwright()
                raise RuntimeError(f"Playwright codegen failed to start: {stderr.decode()}")

            logger.info(f"✅ Codegen started (PID: {self.process.pid})")
            logger.info("✅ Tracing enabled for timestamp capture")
            logger.info("\n👉 Interact with the browser manually.")
            logger.info("👉 Close the browser window when you're done.\n")

        except FileNotFoundError:
            await self._cleanup_playwright()
            raise RuntimeError(
                "Playwright not found. Install with: pip install playwright && playwright install"
            )
        except Exception as e:
            if self.process:
                self.process.kill()
                self.process = None
            if self.output_file and Path(output_path).exists():
                Path(output_path).unlink()
            await self._cleanup_playwright()
            raise RuntimeError(f"Failed to start codegen: {e}")

    async def stop_recording(self) -> Dict[str, Any]:
        """Stop recording and parse generated code with trace timestamps.

        Terminates the codegen process, stops tracing, and parses both
        to merge actions with real timestamps.

        Returns:
            Dictionary containing:
                - 'codegen_file': Path to generated Python code
                - 'trace_file': Path to trace.zip with timestamps
                - 'events': List of events with merged timestamps

        Raises:
            RuntimeError: If recording has not been started
        """
        if self.process is None:
            raise RuntimeError("Recording not started. Call start_recording() first.")

        logger.info("\n⏹️  Stopping codegen recorder...")

        output_path = self.output_file.name

        try:
            # Wait for process to exit (user should close browser)
            # If still running after timeout, terminate it
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                logger.info("   Terminating codegen process...")
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("   Force killing codegen process...")
                    self.process.kill()
                    self.process.wait()

            logger.info("   Codegen process stopped")

            # Stop tracing and save trace file
            if self.context:
                logger.info(f"   Stopping trace and saving to: {self.trace_file}")
                await self.context.tracing.stop(path=str(self.trace_file))
                logger.info("   Trace saved successfully")

            # Cleanup Playwright
            await self._cleanup_playwright()

            # Parse generated code with trace timestamps
            if not Path(output_path).exists():
                logger.warning(f"   No output file generated: {output_path}")
                return {
                    'codegen_file': output_path,
                    'trace_file': str(self.trace_file) if self.trace_file else None,
                    'events': []
                }

            logger.info(f"   Parsing codegen with trace timestamps...")

            # Use hybrid parser if trace file exists
            if self.trace_file and self.trace_file.exists():
                events = self.parser.parse_with_trace(output_path, str(self.trace_file))
                logger.info(f"✅ Recording complete! Captured {len(events)} actions with REAL timestamps")
            else:
                # Fallback to codegen-only parsing
                logger.warning("   Trace file not found, using synthetic timestamps")
                events = self.parser.parse(output_path)
                logger.info(f"✅ Recording complete! Captured {len(events)} actions")

            return {
                'codegen_file': output_path,
                'trace_file': str(self.trace_file) if self.trace_file else None,
                'events': events
            }

        except Exception as e:
            logger.error(f"Error stopping codegen: {e}")
            raise

        finally:
            self.process = None

            # Clean up temporary files
            if Path(output_path).exists():
                try:
                    Path(output_path).unlink()
                    logger.info(f"   Cleaned up: {output_path}")
                except Exception as e:
                    logger.warning(f"   Failed to clean up {output_path}: {e}")

            # Note: Keep trace file for analysis, don't delete it

    async def _cleanup_playwright(self) -> None:
        """Clean up Playwright resources."""
        try:
            if self.context:
                await self.context.close()
                self.context = None
            if self.browser:
                await self.browser.close()
                self.browser = None
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
        except Exception as e:
            logger.warning(f"Error cleaning up Playwright: {e}")

    def wait_for_user_completion(self) -> None:
        """Wait for user to complete manual interactions.

        This is a compatibility method for the RecordingSession interface.
        With codegen, the user closes the browser window to signal completion,
        but we also provide an option to press Enter in the terminal.
        """
        if self.process is None:
            raise RuntimeError("Recording not started.")

        logger.info("\n👉 Close the browser window when you're done recording.")
        logger.info("   Or press ENTER in this terminal to stop...\n")

        # Wait for either:
        # 1. User presses Enter
        # 2. Process exits (user closed browser)
        try:
            import select
            import sys

            while self.process.poll() is None:
                # Check if input is available (with 1 second timeout)
                if sys.stdin in select.select([sys.stdin], [], [], 1.0)[0]:
                    input()  # Consume the Enter key
                    logger.info("\n⏹️  Stopping recording...")
                    break
                # Otherwise, keep checking if process exited
                time.sleep(0.1)

        except (ImportError, OSError):
            # Fallback for systems without select (Windows)
            # Just block on input
            input("Press ENTER to stop recording... ")

    async def record(self, url: str, proxy: Optional[str] = None) -> Dict[str, Any]:
        """Complete recording workflow in one method.

        Convenience method that executes the full recording workflow:
        start -> wait for user -> stop -> parse with trace.

        Args:
            url: The URL to navigate to and begin recording
            proxy: Optional proxy server URL

        Returns:
            Dictionary with codegen_file, trace_file, and events
        """
        try:
            await self.start_recording(url, proxy=proxy)
            self.wait_for_user_completion()
            result = await self.stop_recording()
            return result

        except Exception as error:
            logger.error(f"❌ Recording failed: {error}")
            if self.process is not None:
                try:
                    self.process.kill()
                except Exception:
                    pass
                self.process = None
            await self._cleanup_playwright()
            raise
