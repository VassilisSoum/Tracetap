"""
AI-powered test generation from recording sessions.

This module orchestrates the conversion of correlated UI+network events into
executable Playwright tests using Claude AI. It uses templates to guide test
generation and provides validation of the generated code.

Key Features:
- Template-based test generation (basic, comprehensive, regression)
- Claude AI integration for intelligent code synthesis
- Syntax validation for generated tests
- Support for multiple output formats (TypeScript, JavaScript, Python)
- Configurable test generation strategies

Example:
    generator = TestGenerator(api_key="sk-...")
    result = await generator.generate_tests(
        correlation_result,
        template="comprehensive",
        output_format="typescript"
    )
    print(result)
"""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None
    ANTHROPIC_AVAILABLE = False

from ..record.correlator import CorrelationResult, CorrelatedEvent
from .pii_sanitizer import PIISanitizer, SanitizationConfig
from ..common.constants import DEFAULT_CLAUDE_MODEL, MAX_GENERATION_TOKENS, MODEL_FALLBACKS

logger = logging.getLogger(__name__)


class TemplateType(str, Enum):
    """Available test generation templates."""

    BASIC = "basic"
    COMPREHENSIVE = "comprehensive"
    REGRESSION = "regression"


class OutputFormat(str, Enum):
    """Supported output formats for generated tests."""

    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    PYTHON = "python"


@dataclass
class GenerationOptions:
    """Options for test generation."""

    template: str = "comprehensive"
    output_format: str = "typescript"
    confidence_threshold: float = 0.5
    include_comments: bool = True
    base_url: Optional[str] = None
    test_name: Optional[str] = None
    sanitize_pii: bool = True
    sanitization_config: Optional[SanitizationConfig] = None
    performance_thresholds: Optional[List] = None
    retry_context: Optional[str] = None  # Error feedback for retry attempts
    opaque_frames: Optional[List] = None  # Screenshots of iframes where JS was blocked


@dataclass
class GenerationConfig:
    """Configuration for test generation.

    Attributes:
        template: Template type to use (basic, comprehensive, regression)
        output_format: Output language/format
        include_comments: Whether to include explanatory comments
        include_assertions: Whether to include response validation
        use_data_testid: Prefer data-testid selectors when available
        include_imports: Whether to include import statements
    """

    template: TemplateType = TemplateType.COMPREHENSIVE
    output_format: OutputFormat = OutputFormat.TYPESCRIPT
    include_comments: bool = True
    include_assertions: bool = True
    use_data_testid: bool = True
    include_imports: bool = True


class TestTemplate:
    """Manages test generation templates.

    Templates are stored in src/tracetap/generators/templates/ directory
    and contain prompts and examples for guiding the AI code generation.

    Methods:
        load: Load template from file
        format_prompt: Format template with event data
        get_template_path: Get full path to template file
    """

    def __init__(self, template_dir: Optional[Path] = None):
        """Initialize template manager.

        Args:
            template_dir: Directory containing template files
                         (defaults to ./templates/ relative to this module)
        """
        if template_dir is None:
            # Default to templates/ directory next to this module
            template_dir = Path(__file__).parent / "templates"

        self.template_dir = template_dir

        if not self.template_dir.exists():
            logger.warning(f"Template directory not found: {self.template_dir}")

    def load(self, template_type: TemplateType) -> str:
        """Load template content from file.

        Args:
            template_type: Type of template to load

        Returns:
            Template content as string

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        template_path = self.template_dir / f"{template_type.value}.txt"

        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        logger.info(f"Loading template: {template_path}")

        with template_path.open("r", encoding="utf-8") as f:
            return f.read()

    def format_prompt(
        self, template_content: str, correlated_events: List[CorrelatedEvent]
    ) -> str:
        """Format template with actual event data.

        Replaces template placeholders with serialized event data
        for the AI prompt.

        Args:
            template_content: Raw template content
            correlated_events: List of correlated events to include

        Returns:
            Formatted prompt ready for AI submission
        """
        # TODO: Implement template variable substitution
        # For now, append serialized events to template
        event_data = self._serialize_events(correlated_events)
        return f"{template_content}\n\n## Input Data:\n```json\n{event_data}\n```"

    def _serialize_events(self, events: List[CorrelatedEvent]) -> str:
        """Serialize correlated events to JSON for prompt.

        Args:
            events: List of correlated events

        Returns:
            JSON string representation of events
        """
        # TODO: Implement proper serialization with dataclass conversion
        return json.dumps(
            [
                {
                    "sequence": e.sequence,
                    "ui_event": {
                        "type": getattr(e.ui_event, "type", "unknown"),
                        "timestamp": e.ui_event.timestamp,
                        "selector": getattr(e.ui_event, "selector", None),
                        "value": getattr(e.ui_event, "value", None),
                    },
                    "network_calls": [
                        {
                            "method": nc.method,
                            "url": nc.url,
                            "status": nc.response_status,
                            "request_body": nc.request_body,
                            "response_body": nc.response_body,
                        }
                        for nc in e.network_calls
                    ],
                    "correlation": {
                        "confidence": e.correlation.confidence,
                        "time_delta": e.correlation.time_delta,
                        "method": e.correlation.method.value,
                        "reasoning": e.correlation.reasoning,
                    },
                }
                for e in events
            ],
            indent=2,
        )

    def get_template_path(self, template_type: TemplateType) -> Path:
        """Get full path to template file.

        Args:
            template_type: Type of template

        Returns:
            Path to template file
        """
        return self.template_dir / f"{template_type.value}.txt"


class CodeSynthesizer:
    """Converts correlated events to executable test code.

    This class handles the interaction with Claude AI API and
    post-processes the generated code.

    Methods:
        synthesize: Generate code from events
        validate_syntax: Check generated code for syntax errors
        format_code: Apply code formatting
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize code synthesizer.

        Args:
            api_key: Claude AI API key (if not provided, will try to read from env)
        """
        if not ANTHROPIC_AVAILABLE:
            logger.warning(
                "Anthropic library not installed. Install with: pip install anthropic"
            )
            self.client = None
            self.api_key = None
            return

        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.warning(
                "No Anthropic API key found. Set ANTHROPIC_API_KEY environment variable."
            )
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    async def synthesize(
        self,
        prompt,
        config: GenerationConfig,
    ) -> str:
        """Synthesize test code from prompt.

        Args:
            prompt: Formatted prompt - either a string or list of content blocks
                    (text + images for opaque iframe screenshots)
            config: Generation configuration

        Returns:
            Generated test code

        Raises:
            RuntimeError: If API call fails
        """
        if not self.client:
            raise RuntimeError(
                "Claude API client not initialized. Set ANTHROPIC_API_KEY environment variable."
            )

        logger.info("Synthesizing test code...")
        logger.info(f"   Output format: {config.output_format.value}")
        logger.info(f"   Template: {config.template.value}")

        # Build message content (supports both string and content blocks)
        if isinstance(prompt, str):
            message_content = prompt
        else:
            message_content = prompt  # List of content blocks (text + images)

        # Try default model, then fallbacks if 404
        models_to_try = [DEFAULT_CLAUDE_MODEL] + [
            m for m in MODEL_FALLBACKS if m != DEFAULT_CLAUDE_MODEL
        ]
        last_error = None

        for model in models_to_try:
            try:
                logger.info(f"   Trying model: {model}")
                message = self.client.messages.create(
                    model=model,
                    max_tokens=MAX_GENERATION_TOKENS,
                    messages=[{"role": "user", "content": message_content}],
                )

                if not message.content:
                    raise RuntimeError("Claude returned empty response")
                generated_text = message.content[0].text
                logger.info(f"Generated {len(generated_text)} characters of code (model: {model})")

                return self._extract_code_from_response(generated_text, config.output_format)

            except Exception as e:
                last_error = e
                error_str = str(e)
                # Only try fallback for model-not-found errors
                if "not_found" in error_str or "404" in error_str:
                    logger.warning(f"   Model {model} not available, trying next...")
                    continue
                # For other errors (auth, rate limit, etc.), don't retry with different model
                logger.error(f"Claude API call failed: {e}")
                raise RuntimeError(f"Failed to generate test code: {e}")

        logger.error(f"All models failed. Last error: {last_error}")
        raise RuntimeError(f"Failed to generate test code: no working model found. Last error: {last_error}")

    def _extract_code_from_response(self, response: str, output_format: OutputFormat) -> str:
        """Extract code from Claude response (handles markdown code blocks).

        Args:
            response: Raw response from Claude
            output_format: Expected output format

        Returns:
            Extracted code
        """
        if "```" not in response:
            return response.strip()

        code_blocks = response.split("```")
        format_name = output_format.value

        for i, block in enumerate(code_blocks):
            if i == 0:
                continue

            block_stripped = block.strip()

            if block_stripped.startswith(format_name):
                return block_stripped[len(format_name) :].strip()
            elif block_stripped.startswith("typescript") and format_name == "typescript":
                return block_stripped[len("typescript") :].strip()
            elif block_stripped.startswith("python") and format_name == "python":
                return block_stripped[len("python") :].strip()
            elif not block_stripped.startswith("#") and not block_stripped.startswith("//"):
                return block_stripped

        return response.strip()

    def validate_syntax(self, code: str, output_format: OutputFormat) -> bool:
        """Validate syntax of generated code.

        Args:
            code: Generated test code
            output_format: Expected code format

        Returns:
            True if syntax is valid, False otherwise
        """
        if output_format == OutputFormat.TYPESCRIPT or output_format == OutputFormat.JAVASCRIPT:
            required_patterns = ["import", "test(", "expect("]
            for pattern in required_patterns:
                if pattern not in code:
                    logger.warning(f"Generated code missing '{pattern}' - may not be valid")
                    return False
        elif output_format == OutputFormat.PYTHON:
            try:
                compile(code, "<generated>", "exec")
            except SyntaxError as e:
                logger.error(f"Generated Python code has syntax error: {e}")
                return False

        return True

    def format_code(self, code: str, output_format: OutputFormat) -> str:
        """Format generated code using standard formatters.

        Args:
            code: Raw generated code
            output_format: Code format

        Returns:
            Formatted code

        Raises:
            RuntimeError: If formatting fails
        """
        logger.info("Code formatting not implemented - returning raw code")
        return code

    @staticmethod
    def generate_playwright_action(ui_event: Any) -> str:
        """Convert UI event to Playwright action code.

        Args:
            ui_event: UI event from trace

        Returns:
            Playwright action code string
        """
        event_type = getattr(ui_event, "type", "").lower()
        selector = getattr(ui_event, "selector", None)
        value = getattr(ui_event, "value", None)

        if event_type == "click" and selector:
            return f'await page.click("{selector}");'
        elif event_type == "fill" and selector and value:
            return f'await page.fill("{selector}", "{value}");'
        elif event_type == "navigate":
            url = getattr(ui_event, "url", "")
            return f'await page.goto("{url}");'
        else:
            return f"// {event_type} event"

    @staticmethod
    def generate_network_assertion(network_call: Any, confidence: float) -> str:
        """Convert network call to assertion code.

        Args:
            network_call: Network call data
            confidence: Correlation confidence

        Returns:
            Assertion code string
        """
        method = network_call.method
        url = network_call.url
        status = network_call.response_status

        if confidence < 0.6:
            return f"// Low confidence assertion for {method} {url}"

        if status:
            return f"expect(response.status()).toBe({status});"
        else:
            return f"// Assert {method} {url}"

    @staticmethod
    def generate_test_name(events: List[CorrelatedEvent]) -> str:
        """Generate descriptive test name from events.

        Args:
            events: List of correlated events

        Returns:
            Descriptive test name
        """
        if not events:
            return "generated test"

        event_types = [getattr(e.ui_event, "type", "action") for e in events[:3]]
        return " and ".join(event_types).lower()


class TestGenerator:
    """Main orchestrator for test generation from recordings.

    This class coordinates the entire workflow:
    1. Load appropriate template
    2. Build AI prompt from correlated events
    3. Call Claude AI API to generate code
    4. Validate and format the generated code
    5. Return executable test code

    Example:
        from tracetap.record import RecordingSession
        from tracetap.generators import TestGenerator, GenerationOptions

        # Load correlation result
        session = RecordingSession.load_session("my-session")
        result = await session.analyze()

        # Generate tests
        generator = TestGenerator()
        test_code = await generator.generate_tests(
            result.correlation_result,
            options=GenerationOptions(
                template="comprehensive",
                output_format="typescript",
                confidence_threshold=0.7
            )
        )

        # Save to file
        Path("generated.spec.ts").write_text(test_code)
    """

    def __init__(self, api_key: Optional[str] = None, sanitize_pii: bool = True):
        """Initialize test generator with Claude AI API key.

        Args:
            api_key: Claude API key (if not provided, reads from ANTHROPIC_API_KEY env var)
            sanitize_pii: Enable PII sanitization before sending to AI (default: True)
        """
        self.api_key = api_key
        self.sanitize_pii = sanitize_pii
        self.sanitization_config = SanitizationConfig()
        self.pii_sanitizer = PIISanitizer(self.sanitization_config) if sanitize_pii else None
        self.template_manager = TestTemplate()
        self.synthesizer = CodeSynthesizer(api_key)
        self.templates_dir = Path(__file__).parent / "templates"

        if sanitize_pii:
            logger.info("TestGenerator initialized with PII sanitization ENABLED")
        else:
            logger.warning("TestGenerator initialized with PII sanitization DISABLED - sensitive data will be sent to AI")

    async def generate_tests(
        self,
        correlation_result: CorrelationResult,
        options: Optional[GenerationOptions] = None,
    ) -> str:
        """Generate Playwright tests from correlation result.

        This is the main entry point for test generation. It coordinates
        the entire workflow from correlated events to executable tests.

        Args:
            correlation_result: Result from EventCorrelator
            options: Generation options

        Returns:
            Generated test code as string

        Raises:
            ValueError: If template or format is invalid
            RuntimeError: If generation fails
        """
        options = options or GenerationOptions()

        logger.info("Starting test generation...")
        logger.info(f"   Events: {len(correlation_result.correlated_events)}")
        logger.info(f"   Template: {options.template}")
        logger.info(f"   Output format: {options.output_format}")
        logger.info(f"   Confidence threshold: {options.confidence_threshold}")

        # Filter by confidence threshold
        filtered_events = self._filter_by_confidence(
            correlation_result.correlated_events, options.confidence_threshold
        )
        logger.info(f"   Filtered events: {len(filtered_events)}")

        # Load template
        template_content = self._load_template(options.template)

        # Build AI prompt
        prompt = self._build_ai_prompt(filtered_events, template_content, options)

        # Call Claude API
        generated_code = await self._call_claude_api(prompt, options.output_format)

        # Fix iframe selectors that Claude missed
        generated_code = self._fix_iframe_selectors(generated_code, filtered_events)

        # Post-process
        formatted_code = self._format_generated_code(generated_code, options)

        # Validate syntax
        self._validate_test_syntax(formatted_code, options.output_format)

        logger.info("Test generation complete!")
        return formatted_code

    def _filter_by_confidence(
        self, events: List[CorrelatedEvent], threshold: float
    ) -> List[CorrelatedEvent]:
        """Filter events by confidence threshold.

        Args:
            events: All correlated events
            threshold: Minimum confidence threshold

        Returns:
            Filtered list of events
        """
        return [event for event in events if event.correlation.confidence >= threshold]

    def _fix_iframe_selectors(self, code: str, events: List[CorrelatedEvent]) -> str:
        """Post-process generated code to fix iframe selectors Claude missed.

        Scans the code for page.click/fill/locator calls using selectors that
        were recorded inside iframes, and wraps them in frameLocator() calls.

        This is deterministic — we know exactly which selectors came from iframes
        and what the iframe URL was. No AI guessing needed.
        """
        import re
        from urllib.parse import urlparse

        # Build map: selector -> iframe domain from event metadata
        iframe_selectors: Dict[str, str] = {}
        for event in events:
            metadata = getattr(event.ui_event, "metadata", None) or {}
            frame = metadata.get("frame")
            selector = getattr(event.ui_event, "selector", None)

            if frame and selector:
                frame_url = frame.get("url", "")
                if frame_url:
                    domain = urlparse(frame_url).netloc
                    if domain:
                        iframe_selectors[selector] = domain

        if not iframe_selectors:
            return code

        logger.info(f"Post-processing: fixing {len(iframe_selectors)} iframe selector(s)")

        fixed_code = code
        for selector, domain in iframe_selectors.items():
            # Escape selector for regex
            escaped_sel = re.escape(selector)

            # Match patterns like:
            #   page.click('#cvv')
            #   page.fill('#cvv', '123')
            #   page.locator('#cvv')
            #   await page.click('#cvv')
            #   await page.fill("#cvv", "123")
            # But NOT:
            #   paysafeFrame.locator('#cvv')  (already fixed)
            #   page.frameLocator(...).locator('#cvv')  (already fixed)

            for method in ['click', 'fill', 'locator', 'type', 'press']:
                # Match page.method('selector'...) but not someFrame.locator('selector')
                # Negative lookbehind for frameLocator or any variable.locator
                patterns = [
                    # page.click('selector') or page.click("selector")
                    (rf"(page\.{method}\s*\(\s*)['\"]({escaped_sel})['\"]",
                     rf"page.frameLocator('iframe[src*=\"{domain}\"]').locator('{selector}').{method}("),
                ]

                for pattern, replacement in patterns:
                    # Only replace if not already inside a frameLocator chain
                    new_code = re.sub(pattern, replacement, fixed_code)
                    if new_code != fixed_code:
                        # Clean up double method calls from replacement
                        # e.g. .locator('#cvv').click(.click( -> .locator('#cvv').click(
                        new_code = re.sub(
                            rf"\.{method}\(\.{method}\(",
                            f".{method}(",
                            new_code
                        )
                        fixed_code = new_code

        if fixed_code != code:
            fixes = sum(1 for s in iframe_selectors if s in code and f"frameLocator" not in code.split(s)[0][-50:])
            logger.info(f"Post-processing: applied iframe frameLocator fixes")

        return fixed_code

    def _load_template(self, template_name: str) -> str:
        """Load template file.

        Args:
            template_name: Name of template

        Returns:
            Template content

        Raises:
            FileNotFoundError: If template doesn't exist
        """
        template_path = self.templates_dir / f"{template_name}.txt"
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_name}")
        return template_path.read_text()

    def _build_ai_prompt(
        self, events: List[CorrelatedEvent], template: str, options: GenerationOptions
    ) -> List[Dict[str, Any]]:
        """Build Claude AI prompt content from template and events.

        Returns a list of content blocks (text + optional images for opaque iframes).

        Args:
            events: Filtered correlated events
            template: Template content
            options: Generation options

        Returns:
            List of content blocks for Claude messages API
        """
        events_json = json.dumps([self._serialize_event(e) for e in events], indent=2)

        prompt_text = template.format(
            events_json=events_json,
            output_format=options.output_format,
            confidence_threshold=options.confidence_threshold,
            base_url=options.base_url or "REPLACE_WITH_YOUR_BASE_URL",
        )

        # Inject retry context if this is a retry attempt
        if options.retry_context:
            prompt_text += f"\n\nIMPORTANT: {options.retry_context}\n"

        # Inject performance context if thresholds provided
        if options.performance_thresholds:
            from .performance_analyzer import PerformanceAnalyzer

            analyzer = PerformanceAnalyzer()
            perf_context = analyzer.format_for_prompt(options.performance_thresholds)
            prompt_text += f"\n\n{perf_context}\n"

        # Build content blocks
        content = [{"type": "text", "text": prompt_text}]

        # Add opaque iframe data (DOM or screenshots) for cross-origin iframes
        if options.opaque_frames:
            has_dom = any(f.get("dom_html") for f in options.opaque_frames)
            has_screenshots = any(f.get("screenshot_base64") for f in options.opaque_frames)

            if has_dom:
                iframe_context = (
                    "\n\nIMPORTANT: The following iframe DOM structures were extracted from "
                    "cross-origin iframes (e.g. payment forms) where TraceTap could not "
                    "inject event listeners. Generate page.frameLocator() code to interact "
                    "with these elements. Use the exact attributes (id, name, placeholder, "
                    "aria-label, data-testid) from the DOM to create precise selectors. "
                    "Use the iframe name or src URL for the frameLocator selector."
                )
            else:
                iframe_context = (
                    "\n\nIMPORTANT: The following screenshots show iframes where TraceTap "
                    "could not inject event listeners. Analyze each screenshot to identify "
                    "form fields and generate page.frameLocator() interactions."
                )
            content.append({"type": "text", "text": iframe_context})

            for frame_data in options.opaque_frames:
                frame_name = frame_data.get('frame_name', '')
                frame_url = frame_data.get('frame_url', '')
                frame_desc = f"\nIframe: name=\"{frame_name}\" url=\"{frame_url}\""
                content.append({"type": "text", "text": frame_desc})

                # Prefer DOM HTML (exact selectors) over screenshot (visual inference)
                if frame_data.get("dom_html"):
                    content.append({
                        "type": "text",
                        "text": f"\nIframe DOM (form elements):\n```html\n{frame_data['dom_html']}\n```"
                    })
                elif frame_data.get("screenshot_base64"):
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": frame_data["screenshot_base64"],
                        }
                    })

        return content

    def _serialize_event(self, event: CorrelatedEvent) -> Dict[str, Any]:
        """Convert CorrelatedEvent to JSON-serializable dict with PII sanitization.

        Args:
            event: Correlated event

        Returns:
            Dictionary representation (sanitized if PII sanitization is enabled)
        """
        # Extract frame info from metadata (preserved during TraceTapEvent conversion)
        metadata = getattr(event.ui_event, "metadata", None) or {}
        frame_info = metadata.get("frame")

        ui_event_dict = {
            "type": getattr(event.ui_event, "type", "unknown"),
            "timestamp": event.ui_event.timestamp,
            "selector": getattr(event.ui_event, "selector", None),
            "value": getattr(event.ui_event, "value", None),
            "url": getattr(event.ui_event, "url", None),
        }
        if frame_info:
            ui_event_dict["frame"] = frame_info

        raw_event = {
            "sequence": event.sequence,
            "ui_event": ui_event_dict,
            "network_calls": [
                {
                    "method": call.method,
                    "url": call.url,
                    "request": call.request_body,
                    "response": call.response_body,
                    "timestamp": call.timestamp,
                    "duration": call.duration,
                }
                for call in event.network_calls
            ],
            "correlation": {
                "confidence": event.correlation.confidence,
                "time_delta": event.correlation.time_delta,
                "method": event.correlation.method.value,
                "reasoning": event.correlation.reasoning,
            },
        }

        # Apply PII sanitization if enabled (default ON)
        if self.sanitize_pii and self.pii_sanitizer:
            return self.pii_sanitizer.sanitize_event(raw_event)

        return raw_event

    async def _call_claude_api(self, prompt, output_format: str) -> str:
        """Call Claude API to generate test code.

        Args:
            prompt: Formatted prompt (string or list of content blocks)
            output_format: Expected output format

        Returns:
            Generated code

        Raises:
            RuntimeError: If API call fails
        """
        try:
            output_format_enum = OutputFormat(output_format)
        except ValueError:
            raise ValueError(f"Invalid output format: {output_format}")

        config = GenerationConfig(
            template=TemplateType.COMPREHENSIVE, output_format=output_format_enum
        )

        return await self.synthesizer.synthesize(prompt, config)

    def _format_generated_code(self, code: str, options: GenerationOptions) -> str:
        """Format generated code (add header, clean up).

        Args:
            code: Raw generated code
            options: Generation options

        Returns:
            Formatted code with header
        """
        header = self._generate_header(options)
        return f"{header}\n\n{code}"

    def _generate_header(self, options: GenerationOptions) -> str:
        """Generate file header comment.

        Args:
            options: Generation options

        Returns:
            Header comment string
        """
        base_url = options.base_url or ""
        if options.output_format == "typescript" or options.output_format == "javascript":
            header = f"""// Generated by TraceTap
// Template: {options.template}
// Confidence threshold: {options.confidence_threshold}"""
            if base_url:
                header += f"\n// Base URL: {base_url} (configured in playwright.config.ts)"
            header += "\n// DO NOT EDIT - This file is auto-generated"
            return header
        else:
            header = f'''"""
Generated by TraceTap
Template: {options.template}
Confidence threshold: {options.confidence_threshold}'''
            if base_url:
                header += f"\nBase URL: {base_url} (configured in playwright.config.ts)"
            header += '\nDO NOT EDIT - This file is auto-generated'
            return header + '\n"""'

    def _validate_test_syntax(self, code: str, output_format: str) -> None:
        """Validate generated code syntax.

        Args:
            code: Generated code
            output_format: Expected format

        Raises:
            RuntimeError: If validation fails
        """
        try:
            output_format_enum = OutputFormat(output_format)
        except ValueError:
            raise ValueError(f"Invalid output format: {output_format}")

        is_valid = self.synthesizer.validate_syntax(code, output_format_enum)
        if not is_valid:
            logger.warning("Generated code failed syntax validation")
