"""
TraceTap Test Generator CLI

Command-line interface for generating Playwright tests from recorded sessions.
Reads correlation data from a session directory and uses AI to synthesize tests.
"""

import argparse
import asyncio
import sys
import json
import os
from pathlib import Path
from typing import Optional
import logging

from ..generators import TestGenerator, GenerationOptions
from ..record.correlator import (
    CorrelationResult,
    CorrelatedEvent,
    CorrelationMetadata,
    CorrelationMethod,
    NetworkRequest,
)
from ..record.parser import TraceTapEvent, EventType

logger = logging.getLogger(__name__)


def load_correlation_result(correlation_file: Path) -> CorrelationResult:
    """Load correlation result from JSON file.

    Args:
        correlation_file: Path to correlation.json

    Returns:
        CorrelationResult object

    Raises:
        ValueError: If correlation file is invalid
    """
    with open(correlation_file, "r") as f:
        data = json.load(f)

    # Reconstruct CorrelationResult from JSON
    correlated_events = []

    for event_data in data.get("correlated_events", []):
        # Reconstruct UI event
        ui_event_data = event_data["ui_event"]

        # Convert type string to EventType enum, fallback to CLICK if unknown
        event_type_str = ui_event_data.get("type", "click")
        try:
            event_type = EventType(event_type_str)
        except ValueError:
            event_type = EventType.CLICK

        ui_event = TraceTapEvent(
            type=event_type,
            timestamp=ui_event_data.get("timestamp", 0),
            duration=ui_event_data.get("duration", 0),
            selector=ui_event_data.get("selector"),
            value=ui_event_data.get("value"),
            url=ui_event_data.get("url"),
        )

        # Reconstruct network calls
        network_calls = []
        for nc_data in event_data.get("network_calls", []):
            network_call = NetworkRequest(
                method=nc_data["method"],
                url=nc_data["url"],
                host=nc_data.get("host", ""),
                path=nc_data.get("path", ""),
                timestamp=nc_data.get("timestamp", 0),
                request_headers=nc_data.get("request_headers", {}),
                request_body=nc_data.get("request_body"),
                response_status=nc_data.get("response_status"),
                response_headers=nc_data.get("response_headers"),
                response_body=nc_data.get("response_body"),
                duration=nc_data.get("duration"),
            )
            network_calls.append(network_call)

        # Reconstruct correlation metadata
        corr_data = event_data["correlation"]
        correlation = CorrelationMetadata(
            confidence=corr_data["confidence"],
            time_delta=corr_data["time_delta"],
            method=CorrelationMethod(corr_data["method"]),
            reasoning=corr_data["reasoning"],
        )

        # Create CorrelatedEvent
        correlated_event = CorrelatedEvent(
            sequence=event_data["sequence"],
            ui_event=ui_event,
            network_calls=network_calls,
            correlation=correlation,
        )
        correlated_events.append(correlated_event)

    # Get stats
    stats = data.get("stats", {})

    return CorrelationResult(correlated_events=correlated_events, stats=stats)


async def generate_tests_from_session(
    session_dir: Path,
    output_file: Path,
    template: str,
    output_format: str,
    confidence_threshold: float,
    api_key: Optional[str],
    base_url: Optional[str],
    verbose: bool,
) -> int:
    """Generate tests from a recorded session.

    Args:
        session_dir: Path to session directory
        output_file: Output file path
        template: Template type
        output_format: Output format
        confidence_threshold: Minimum confidence
        api_key: Anthropic API key
        base_url: Base URL for tests
        verbose: Enable verbose logging

    Returns:
        Exit code (0=success, 1=error)
    """
    # Load correlation result
    print(f"📂 Loading session from {session_dir}...")
    correlation_file = session_dir / "correlation.json"

    if not correlation_file.exists():
        print(f"❌ Error: No correlation file found at {correlation_file}")
        print("Hint: Run 'tracetap record' first to create a session")
        return 1

    try:
        correlation_result = load_correlation_result(correlation_file)
        print(f"✅ Loaded {len(correlation_result.correlated_events)} correlated events")
        print(
            f"   Correlation rate: {correlation_result.stats.get('correlation_rate', 0) * 100:.1f}%"
        )
        print(
            f"   Average confidence: {correlation_result.stats.get('average_confidence', 0) * 100:.1f}%"
        )
    except Exception as e:
        print(f"❌ Error loading correlation data: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1

    # Initialize generator
    print(f"\n🤖 Initializing AI test generator...")
    try:
        generator = TestGenerator(api_key=api_key)
    except Exception as e:
        print(f"❌ Error initializing generator: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1

    # Generate tests
    print(f"✨ Generating {template} tests...")
    print(f"   Output format: {output_format}")
    print(f"   Confidence threshold: {confidence_threshold}")

    options = GenerationOptions(
        template=template,
        output_format=output_format,
        confidence_threshold=confidence_threshold,
        base_url=base_url,
    )

    try:
        test_code = await generator.generate_tests(correlation_result, options)
    except Exception as e:
        print(f"\n❌ Error generating tests: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1

    # Save to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(test_code)

    # Display statistics
    lines = test_code.count("\n")
    file_size = len(test_code)

    print(f"\n✅ Tests generated successfully!")
    print(f"   Output file: {output_file}")
    print(f"   Lines: {lines}")
    print(f"   Size: {file_size} bytes")
    print(f"\n💡 Next steps:")
    print(f"   1. Review the generated test: {output_file}")

    if output_format in ["typescript", "javascript"]:
        print(f"   2. Run tests: npx playwright test {output_file}")
    else:
        print(f"   2. Run tests: pytest {output_file}")

    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="tracetap-generate-tests",
        description="Generate Playwright tests from TraceTap recording sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from session directory
  tracetap-generate-tests recordings/my-session -o tests/generated.spec.ts

  # Use comprehensive template
  tracetap-generate-tests recordings/my-session -o tests/full.spec.ts --template comprehensive

  # Generate Python tests
  tracetap-generate-tests recordings/my-session -o tests/test_flow.py --format python

  # Higher confidence threshold
  tracetap-generate-tests recordings/my-session -o tests/strict.spec.ts --min-confidence 0.8

  # Custom API key
  tracetap-generate-tests recordings/my-session -o tests/output.spec.ts --api-key sk-ant-...

  # Specify base URL
  tracetap-generate-tests recordings/my-session -o tests/output.spec.ts --base-url https://myapp.com
        """,
    )

    parser.add_argument(
        "session", type=Path, help="Path to recorded session directory (from tracetap record)"
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output file path for generated tests",
    )

    parser.add_argument(
        "-t",
        "--template",
        choices=["basic", "comprehensive", "regression"],
        default="comprehensive",
        help="Test generation template (default: comprehensive)",
    )

    parser.add_argument(
        "-f",
        "--format",
        choices=["typescript", "javascript", "python"],
        default="typescript",
        help="Output format (default: typescript)",
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        metavar="THRESHOLD",
        help="Minimum correlation confidence (0.0-1.0, default: 0.5)",
    )

    parser.add_argument(
        "--base-url",
        type=str,
        help="Base URL for the application under test",
    )

    parser.add_argument(
        "--api-key", type=str, help="Anthropic API key (or set ANTHROPIC_API_KEY env var)"
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG, format="%(levelname)s: %(message)s"
        )
    else:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    # Validation
    if not args.session.exists():
        print(f"❌ Error: Session directory not found: {args.session}")
        return 1

    if not args.session.is_dir():
        print(f"❌ Error: Not a directory: {args.session}")
        return 1

    if args.min_confidence < 0 or args.min_confidence > 1:
        print(f"❌ Error: --min-confidence must be between 0.0 and 1.0")
        return 1

    # Check for API key
    api_key = args.api_key
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("❌ Error: Anthropic API key required")
            print("   Set ANTHROPIC_API_KEY environment variable or use --api-key")
            print("\n💡 Get your API key at: https://console.anthropic.com/")
            return 1

    # Run generation
    try:
        return asyncio.run(
            generate_tests_from_session(
                session_dir=args.session,
                output_file=args.output,
                template=args.template,
                output_format=args.format,
                confidence_threshold=args.min_confidence,
                api_key=api_key,
                base_url=args.base_url,
                verbose=args.verbose,
            )
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
