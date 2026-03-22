"""
UI interaction recorder using Playwright trace files.

This module provides functionality to record user interactions during manual
testing sessions, capturing both UI events and network traffic for automated
test generation.

Key features:
- Records browser interactions with microsecond-precision timestamps
- Captures screenshots, DOM snapshots, and source maps
- Supports headless and headed modes
- Integrates with mitmproxy for network capture (future)

Reference Implementation: spike/poc/trace-recorder.ts
"""

import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, BrowserContext, Page


logger = logging.getLogger(__name__)


@dataclass
class RecorderOptions:
    """Configuration options for trace recording."""

    headless: bool = False  # Visual browser for manual interaction
    screenshots: bool = True
    snapshots: bool = True
    sources: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    recording_mode: str = "codegen"  # "codegen" or "trace"


class TraceRecorder:
    """Records UI interactions using Playwright tracing.

    This class manages the browser lifecycle and trace capture for
    manual testing sessions. It launches a Playwright browser, enables
    tracing, and captures all user interactions with microsecond precision.

    Example:
        recorder = TraceRecorder(RecorderOptions(headless=False))
        await recorder.start_recording("https://example.com")
        # User interacts manually...
        await recorder.stop_recording("session.zip")
    """

    def __init__(self, options: Optional[RecorderOptions] = None):
        """Initialize the trace recorder.

        Args:
            options: Recording configuration options
        """
        self.options = options or RecorderOptions()
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def start_recording(self, url: str, proxy: Optional[str] = None) -> None:
        """Start recording user interactions at the given URL.

        Launches a Playwright browser, creates a context with tracing enabled,
        and navigates to the target URL. The user can then interact manually.

        Args:
            url: The URL to navigate to and begin recording
            proxy: Optional proxy server URL (e.g., "http://localhost:8888")

        Raises:
            RuntimeError: If recording is already in progress
        """
        if self.browser is not None:
            raise RuntimeError("Recording already in progress. Call stop_recording() first.")

        logger.info("🎬 Starting trace recorder...")
        logger.info(f"   URL: {url}")
        logger.info(f"   Headless: {self.options.headless}")
        if proxy:
            logger.info(f"   Proxy: {proxy}")

        # Launch browser
        await self._launch_browser()

        # Create context with tracing (and optional proxy)
        await self._create_context(proxy=proxy)

        # Start tracing BEFORE opening page
        logger.info("🔴 Starting trace capture...")
        await self.context.tracing.start(
            screenshots=self.options.screenshots,
            snapshots=self.options.snapshots,
            sources=self.options.sources
        )

        # Open page
        self.page = await self.context.new_page()

        logger.info(f"🌐 Navigating to {url}...")
        await self.page.goto(url)

        logger.info("\n✅ Recording started!")
        logger.info("👉 Interact with the browser manually.")
        logger.info("👉 Press ENTER when you're done to stop recording.\n")

    async def stop_recording(self, output_path: str) -> None:
        """Stop recording and save trace to file.

        Stops the Playwright tracing, saves the trace.zip file to the
        specified path, and closes the browser.

        Args:
            output_path: Path where trace.zip file will be saved

        Raises:
            RuntimeError: If recording has not been started
        """
        if self.context is None:
            raise RuntimeError("Recording not started. Call start_recording() first.")

        logger.info("\n⏹️  Stopping trace capture...")

        # Stop tracing and save
        output_file = Path(output_path)
        await self.context.tracing.stop(path=str(output_file))

        logger.info(f"💾 Trace saved to: {output_path}")

        # Close browser
        await self._close_browser()

        logger.info("✅ Recording complete!")

    async def wait_for_user_completion(self) -> None:
        """Wait for user to complete manual interactions.

        Blocks until the user signals completion (e.g., by pressing Enter).
        This allows for manual testing sessions of arbitrary duration.
        """
        input("Press ENTER to stop recording... ")

    async def record(self, url: str, output_path: str) -> None:
        """Complete recording workflow in one method.

        Convenience method that executes the full recording workflow:
        start -> wait for user -> stop.

        Args:
            url: The URL to navigate to and begin recording
            output_path: Path where trace.zip file will be saved
        """
        try:
            await self.start_recording(url)
            await self.wait_for_user_completion()
            await self.stop_recording(output_path)
        except Exception as error:
            logger.error(f"❌ Recording failed: {error}")
            if self.browser is not None:
                await self._close_browser()
            raise

    async def _launch_browser(self) -> None:
        """Launch Playwright browser with configured options.

        Raises:
            Exception: If browser launch fails
        """
        try:
            logger.info("\n📱 Launching browser...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.options.headless,
                slow_mo=0,  # No artificial slowdown
                args=['--start-maximized']  # Maximize browser window
            )
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            raise

    async def _create_context(self, proxy: Optional[str] = None) -> None:
        """Create browser context with tracing enabled.

        Args:
            proxy: Optional proxy server URL (e.g., "http://localhost:8888")

        Raises:
            RuntimeError: If browser is not launched
        """
        if self.browser is None:
            raise RuntimeError("Browser not launched. Call _launch_browser() first.")

        context_options = {
            "viewport": {
                "width": self.options.viewport_width,
                "height": self.options.viewport_height
            },
            "ignore_https_errors": True  # Required for mitmproxy SSL interception
        }

        # Add proxy configuration if provided
        if proxy:
            context_options["proxy"] = {"server": proxy}

        self.context = await self.browser.new_context(**context_options)

    async def _close_browser(self) -> None:
        """Close browser and cleanup resources."""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None
            self.page = None

        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
