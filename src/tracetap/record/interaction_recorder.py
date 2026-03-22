"""
Browser interaction recorder using Playwright with CDP event capture.

Records real manual user interactions (clicks, typing, navigation) by injecting
JavaScript event listeners into the page. Captures both UI events and network
traffic from a single browser instance with real timestamps.

This replaces the broken two-browser hybrid approach (codegen + trace) with a
single reliable recording mechanism.

How it works:
1. Launches a headed Chromium browser via Playwright
2. Injects JS event listeners for click, input, change, submit, keydown
3. Captures network traffic via page.on('request')/page.on('response')
4. User interacts manually with the browser
5. All events have real timestamps from the browser's performance.now()
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class RecordedEvent:
    """A single recorded user interaction or network event."""
    type: str  # 'click', 'fill', 'navigate', 'keypress', 'select', 'submit', 'request', 'response'
    timestamp: float  # Unix timestamp in milliseconds
    selector: Optional[str] = None
    value: Optional[str] = None
    url: Optional[str] = None
    tag: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class NetworkCall:
    """A captured network request/response pair."""
    method: str
    url: str
    timestamp: float  # Unix timestamp in milliseconds
    request_headers: Dict[str, str] = field(default_factory=dict)
    request_body: Optional[str] = None
    response_status: Optional[int] = None
    response_headers: Dict[str, str] = field(default_factory=dict)
    response_body: Optional[str] = None
    duration: Optional[float] = None


@dataclass
class RecorderOptions:
    """Configuration options for interaction recording."""
    headless: bool = False
    viewport_width: int = 1920
    viewport_height: int = 1080
    capture_network: bool = True
    capture_screenshots: bool = False
    ignore_resource_types: List[str] = field(
        default_factory=lambda: ['image', 'font', 'stylesheet', 'media']
    )


# JavaScript injected into every page to capture user interactions
INTERACTION_CAPTURE_JS = """
() => {
    if (window.__tracetap_initialized) return;
    window.__tracetap_initialized = true;
    function getSelector(el) {
        if (!el || el === document.body || el === document.documentElement) return 'body';

        // Prefer data-testid
        if (el.dataset && el.dataset.testid) return `[data-testid="${el.dataset.testid}"]`;

        // Then id
        if (el.id) return `#${el.id}`;

        // Then name attribute for form elements
        if (el.name && ['INPUT', 'SELECT', 'TEXTAREA', 'BUTTON'].includes(el.tagName)) {
            return `${el.tagName.toLowerCase()}[name="${el.name}"]`;
        }

        // Then aria-label
        if (el.getAttribute('aria-label')) {
            return `[aria-label="${el.getAttribute('aria-label')}"]`;
        }

        // Then role + text content for buttons/links
        if (['BUTTON', 'A'].includes(el.tagName)) {
            const text = el.textContent.trim().substring(0, 50);
            if (text) return `${el.tagName.toLowerCase()}:has-text("${text}")`;
        }

        // Then placeholder for inputs
        if (el.placeholder) return `[placeholder="${el.placeholder}"]`;

        // Then type for inputs
        if (el.tagName === 'INPUT' && el.type) {
            return `input[type="${el.type}"]`;
        }

        // Fallback to tag + nth-of-type
        const parent = el.parentElement;
        if (parent) {
            const siblings = Array.from(parent.children).filter(c => c.tagName === el.tagName);
            if (siblings.length > 1) {
                const index = siblings.indexOf(el) + 1;
                return `${getSelector(parent)} > ${el.tagName.toLowerCase()}:nth-of-type(${index})`;
            }
            return `${getSelector(parent)} > ${el.tagName.toLowerCase()}`;
        }

        return el.tagName.toLowerCase();
    }

    function pushEvent(evt) {
        // Attach frame context if this is an iframe
        if (window.__tracetap_frame && !window.__tracetap_frame.isMain) {
            evt.frame = {
                name: window.__tracetap_frame.name,
                url: window.__tracetap_frame.url,
            };
        }
        // Send event to Python immediately via exposed function
        // This survives page navigation (events aren't lost)
        if (window.__tracetap_push) {
            window.__tracetap_push(JSON.stringify(evt));
        }
    }

    // Capture clicks
    document.addEventListener('click', (e) => {
        const el = e.target;
        pushEvent({
            type: 'click',
            timestamp: Date.now(),
            selector: getSelector(el),
            tag: el.tagName.toLowerCase(),
            metadata: {
                x: e.clientX,
                y: e.clientY,
                button: e.button,
            }
        });
    }, true);

    // Capture input changes (debounced per element)
    const inputTimers = new WeakMap();
    document.addEventListener('input', (e) => {
        const el = e.target;
        if (!['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName)) return;

        // Debounce: wait 500ms after last keystroke
        if (inputTimers.has(el)) clearTimeout(inputTimers.get(el));
        inputTimers.set(el, setTimeout(() => {
            const isPassword = el.type === 'password';
            pushEvent({
                type: 'fill',
                timestamp: Date.now(),
                selector: getSelector(el),
                value: isPassword ? '***REDACTED***' : el.value,
                tag: el.tagName.toLowerCase(),
                metadata: {
                    inputType: el.type || 'text',
                    isPassword: isPassword,
                }
            });
        }, 500));
    }, true);

    // Capture select changes
    document.addEventListener('change', (e) => {
        const el = e.target;
        if (el.tagName !== 'SELECT') return;
        pushEvent({
            type: 'select',
            timestamp: Date.now(),
            selector: getSelector(el),
            value: el.value,
            tag: 'select',
            metadata: {
                selectedText: el.options[el.selectedIndex]?.text,
            }
        });
    }, true);

    // Capture form submits
    document.addEventListener('submit', (e) => {
        const el = e.target;
        pushEvent({
            type: 'submit',
            timestamp: Date.now(),
            selector: getSelector(el),
            tag: 'form',
            metadata: {
                action: el.action,
                method: el.method,
            }
        });
    }, true);

    // Capture Enter key (often triggers actions without form submit)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === 'Escape' || e.key === 'Tab') {
            pushEvent({
                type: 'keypress',
                timestamp: Date.now(),
                selector: getSelector(e.target),
                value: e.key,
                tag: e.target.tagName.toLowerCase(),
            });
        }
    }, true);
}
"""


class InteractionRecorder:
    """Records real user interactions using Playwright with JS event injection.

    Launches a single headed browser, injects event listeners, and captures
    both UI interactions and network traffic with real timestamps.

    Example:
        recorder = InteractionRecorder()
        await recorder.start("https://example.com")
        # User interacts manually...
        result = await recorder.stop()
        print(f"Captured {len(result['ui_events'])} UI events")
        print(f"Captured {len(result['network_calls'])} network calls")
    """

    def __init__(self, options: Optional[RecorderOptions] = None):
        self.options = options or RecorderOptions()
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._ui_events: List[Dict[str, Any]] = []
        self._network_calls: List[NetworkCall] = []
        self._pending_requests: Dict[str, Dict[str, Any]] = {}
        self._recording = False
        self._start_time: Optional[float] = None

    async def start(self, url: str, proxy: Optional[str] = None) -> None:
        """Start recording at the given URL.

        Launches browser, injects event listeners, sets up network capture,
        and navigates to the URL. User can then interact manually.

        Args:
            url: Target URL to record
            proxy: Optional proxy URL (e.g. for mitmproxy)
        """
        if self._recording:
            raise RuntimeError("Recording already in progress.")

        logger.info(f"Starting interaction recorder for {url}")

        # Import here to give clear error if playwright not installed
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. Install with: pip install playwright && playwright install chromium"
            )

        self.playwright = await async_playwright().start()

        # Launch browser
        launch_args = ['--start-maximized']
        self.browser = await self.playwright.chromium.launch(
            headless=self.options.headless,
            args=launch_args,
        )

        # Create context
        context_options = {
            "viewport": {
                "width": self.options.viewport_width,
                "height": self.options.viewport_height,
            },
            "ignore_https_errors": True,
        }
        if proxy:
            context_options["proxy"] = {"server": proxy}

        self.context = await self.browser.new_context(**context_options)

        # Set up network capture
        if self.options.capture_network:
            self._setup_network_capture()

        # Expose function to receive events from JS (survives navigation)
        await self.context.expose_function(
            "__tracetap_push",
            self._on_ui_event,
        )

        # Create page and inject event listeners
        self.page = await self.context.new_page()

        # Re-inject on every navigation (SPA route changes, new pages, iframes)
        self.page.on("load", lambda: asyncio.ensure_future(self._inject_listeners()))
        self.page.on("framenavigated", lambda frame: asyncio.ensure_future(
            self._on_navigation(frame)
        ))
        # Inject into dynamically added iframes
        self.page.on("frameattached", lambda frame: asyncio.ensure_future(
            self._on_frame_attached(frame)
        ))

        # Navigate to URL
        self._start_time = time.time() * 1000
        self._recording = True

        logger.info(f"Navigating to {url}...")
        await self.page.goto(url, wait_until="domcontentloaded")
        await self._inject_listeners()

        logger.info("Recording started. Interact with the browser.")

    async def stop(self) -> Dict[str, Any]:
        """Stop recording and return captured events.

        Returns:
            Dictionary with 'ui_events', 'network_calls', and 'metadata'
        """
        if not self._recording:
            raise RuntimeError("Recording not started.")

        logger.info("Stopping recording...")

        # Collect UI events (already in Python via expose_function)
        ui_events = self._collect_ui_events()

        # Calculate duration
        end_time = time.time() * 1000
        duration = (end_time - self._start_time) / 1000 if self._start_time else 0

        # Close browser
        await self._cleanup()

        self._recording = False

        result = {
            "ui_events": ui_events,
            "network_calls": [asdict(nc) for nc in self._network_calls],
            "metadata": {
                "start_time": self._start_time,
                "end_time": end_time,
                "duration_seconds": duration,
                "ui_event_count": len(ui_events),
                "network_call_count": len(self._network_calls),
            }
        }

        logger.info(
            f"Recording complete: {len(ui_events)} UI events, "
            f"{len(self._network_calls)} network calls, "
            f"{duration:.1f}s duration"
        )

        return result

    async def wait_for_user(self) -> None:
        """Wait for user to finish interacting.

        Blocks until the user presses Enter or the browser is closed.
        """
        if not self._recording:
            raise RuntimeError("Recording not started.")

        try:
            import select
            import sys

            while self._recording:
                # Check if browser was closed
                if self.browser and not self.browser.is_connected():
                    logger.info("Browser closed by user.")
                    break

                # Check for Enter key (with timeout)
                if sys.stdin in select.select([sys.stdin], [], [], 1.0)[0]:
                    sys.stdin.readline()
                    break

                await asyncio.sleep(0.1)

        except (ImportError, OSError):
            # Fallback for systems without select (e.g. Windows)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, input, "Press ENTER to stop recording... ")

    async def _inject_listeners(self) -> None:
        """Inject JavaScript event listeners into all frames (main + iframes)."""
        if not self.page:
            return

        for frame in self.page.frames:
            await self._inject_into_frame(frame)

    async def _inject_into_frame(self, frame) -> None:
        """Inject event listeners into a single frame."""
        try:
            url = frame.url
            if not url or url == "about:blank":
                return

            # Build frame identifier for selectors
            # Main frame: no prefix. Iframes: prefix with frame locator.
            is_main = (frame == self.page.main_frame)
            frame_name = frame.name or ""
            frame_url = frame.url or ""

            # Inject the capture JS + frame metadata
            await frame.evaluate(f"""() => {{
                // Set frame metadata so events include iframe context
                window.__tracetap_frame = {{
                    isMain: {str(is_main).lower()},
                    name: "{frame_name}",
                    url: "{frame_url}"
                }};
            }}""")
            await frame.evaluate(INTERACTION_CAPTURE_JS)
            if not is_main:
                logger.debug(f"Listeners injected into iframe: {frame_name or frame_url[:60]}")

        except Exception as e:
            logger.debug(f"Failed to inject into frame: {e}")

    async def _on_frame_attached(self, frame) -> None:
        """Handle dynamically added iframe - wait for load then inject."""
        await asyncio.sleep(1)  # Wait for iframe content to load
        await self._inject_into_frame(frame)

    async def _on_navigation(self, frame) -> None:
        """Handle frame navigation - re-inject listeners into all frames."""
        url = frame.url
        if not url or url == "about:blank":
            return

        logger.debug(f"Navigation detected: {url[:80]}")
        await asyncio.sleep(0.5)  # Wait for page/frame to settle

        if frame == self.page.main_frame:
            # Main frame navigated - re-inject into all frames
            await self._inject_listeners()
        else:
            # Iframe navigated - inject into just that frame
            await self._inject_into_frame(frame)

    def _on_ui_event(self, event_json: str) -> None:
        """Receive a UI event from the browser JS context.

        Called via expose_function - events are pushed to Python immediately,
        surviving page navigation.
        """
        try:
            event = json.loads(event_json)
            self._ui_events.append(event)
            logger.debug(f"UI event: {event.get('type')} {event.get('selector', '')}")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse UI event: {e}")

    def _collect_ui_events(self) -> List[Dict[str, Any]]:
        """Return all captured UI events."""
        return list(self._ui_events)

    def _setup_network_capture(self) -> None:
        """Set up network request/response capture via Playwright events."""
        self.context.on("request", lambda req: self._on_request(req))
        self.context.on("response", lambda resp: asyncio.ensure_future(
            self._on_response(resp)
        ))

    def _on_request(self, request) -> None:
        """Handle outgoing network request."""
        # Filter out resource types we don't care about
        if request.resource_type in self.options.ignore_resource_types:
            return

        url = request.url
        # Skip data URLs and browser internals
        if url.startswith("data:") or url.startswith("chrome"):
            return

        # Use id(request) as key to handle parallel requests to same URL
        req_id = id(request)
        self._pending_requests[req_id] = {
            "method": request.method,
            "url": url,
            "timestamp": time.time() * 1000,
            "headers": dict(request.headers),
            "post_data": request.post_data,
            "_request_obj": request,
        }

    async def _on_response(self, response) -> None:
        """Handle incoming network response."""
        # Find the matching request by object identity
        req_id = id(response.request)
        if req_id not in self._pending_requests:
            return

        req_data = self._pending_requests.pop(req_id)
        parsed = urlparse(url)

        # Try to get response body for API calls
        response_body = None
        content_type = response.headers.get("content-type", "")
        if "json" in content_type or "text" in content_type:
            try:
                response_body = await response.text()
                # Truncate very large responses
                if len(response_body) > 10000:
                    response_body = response_body[:10000] + "...[truncated]"
            except Exception:
                pass

        network_call = NetworkCall(
            method=req_data["method"],
            url=url,
            timestamp=req_data["timestamp"],
            request_headers=req_data["headers"],
            request_body=req_data.get("post_data"),
            response_status=response.status,
            response_headers=dict(response.headers),
            response_body=response_body,
            duration=time.time() * 1000 - req_data["timestamp"],
        )

        self._network_calls.append(network_call)

    async def _cleanup(self) -> None:
        """Clean up browser resources."""
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
            logger.warning(f"Cleanup error: {e}")
        finally:
            self.page = None
