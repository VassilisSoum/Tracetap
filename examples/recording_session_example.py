#!/usr/bin/env python3
"""
Example: Complete Recording Session with Network Capture

This example demonstrates the full recording workflow with automatic
mitmproxy integration for network traffic capture.

Usage:
    python recording_session_example.py

Features demonstrated:
- Automatic mitmproxy proxy setup
- Browser recording with proxy configuration
- Network traffic capture
- Event correlation
- Result persistence
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tracetap.record import (
    RecordingSession,
    RecorderOptions,
    CorrelationOptions,
)


async def main():
    """Run complete recording session example."""

    print("\n" + "=" * 70)
    print("TraceTap Recording Session - Complete Example")
    print("=" * 70)

    # Configuration
    target_url = "https://example.com"
    session_name = "example-session"
    output_dir = "recordings"

    print(f"\nConfiguration:")
    print(f"  Target URL: {target_url}")
    print(f"  Session Name: {session_name}")
    print(f"  Output Directory: {output_dir}")
    print(f"  Proxy Port: 8888")

    # Create recording session
    session = RecordingSession(
        session_name=session_name,
        output_dir=output_dir,
        recorder_options=RecorderOptions(
            headless=False,  # Show browser for demo
            screenshots=True,
            snapshots=True,
            sources=True,
        ),
        proxy_port=8888,
    )

    try:
        # Phase 1: Start Recording
        print("\n" + "-" * 70)
        print("Phase 1: Starting Recording Session")
        print("-" * 70)

        metadata = await session.start(target_url)

        print(f"\n✅ Recording started!")
        print(f"   Session ID: {metadata.session_id}")
        print(f"   Output Dir: {metadata.output_dir}")
        print(f"   mitmproxy: http://localhost:{session.proxy_port}")

        # Phase 2: Manual Interaction
        print("\n" + "-" * 70)
        print("Phase 2: Manual Interaction")
        print("-" * 70)
        print("\n👉 Interact with the browser now:")
        print("   - Click links")
        print("   - Fill forms")
        print("   - Navigate pages")
        print("\n   Network traffic is being captured automatically!")
        print("\n👉 Press ENTER when done to stop recording\n")

        input()

        # Phase 3: Stop Recording
        print("\n" + "-" * 70)
        print("Phase 3: Stopping Recording Session")
        print("-" * 70)

        metadata = await session.stop()

        print(f"\n✅ Recording stopped!")
        print(f"   Duration: {metadata.duration:.1f} seconds")
        print(f"   Trace File: {metadata.trace_file}")
        print(f"   Traffic File: {metadata.traffic_path}")

        # Phase 4: Analysis & Correlation
        print("\n" + "-" * 70)
        print("Phase 4: Analyzing & Correlating Events")
        print("-" * 70)

        result = await session.analyze(
            correlation_options=CorrelationOptions(
                window_ms=500,  # 500ms correlation window
                min_confidence=0.5,  # Minimum 50% confidence
                include_orphans=False,  # Exclude events with no network calls
            )
        )

        print(f"\n✅ Analysis complete!")

        # Display Parse Results
        if result.parse_result:
            print(f"\n📊 UI Events Parsed: {len(result.parse_result.events)}")
            print(f"\n   Top 5 Events:")
            for i, event in enumerate(result.parse_result.events[:5], 1):
                event_info = getattr(event, 'selector', getattr(event, 'url', 'N/A'))
                print(f"   {i}. {event.type} - {event_info}")

            if len(result.parse_result.events) > 5:
                print(f"   ... and {len(result.parse_result.events) - 5} more events")

        # Display Correlation Results
        if result.correlation_result:
            stats = result.correlation_result.stats
            print(f"\n🔗 Event Correlation:")
            print(f"   Total UI Events: {stats['total_ui_events']}")
            print(f"   Total Network Calls: {stats['total_network_calls']}")
            print(f"   Correlated Events: {stats['correlated_ui_events']}")
            print(f"   Correlation Rate: {stats['correlation_rate'] * 100:.1f}%")
            print(f"   Average Confidence: {stats['average_confidence'] * 100:.1f}%")
            print(f"   Average Time Delta: {stats['average_time_delta']:.1f}ms")

            # Quality Assessment
            rate = stats['correlation_rate']
            confidence = stats['average_confidence']
            print(f"\n   Quality Assessment: ", end="")
            if rate >= 0.8 and confidence >= 0.7:
                print("✅ EXCELLENT")
            elif rate >= 0.6 and confidence >= 0.6:
                print("✅ GOOD")
            elif rate >= 0.4 or confidence >= 0.5:
                print("⚠️  MODERATE")
            else:
                print("❌ POOR")

            # Sample Correlations
            if result.correlation_result.correlated_events:
                print(f"\n   Sample Correlations (top 3):")
                for i, event in enumerate(result.correlation_result.correlated_events[:3], 1):
                    ui_info = getattr(event.ui_event, 'selector',
                                    getattr(event.ui_event, 'url', 'N/A'))
                    confidence = int(event.correlation.confidence * 100)
                    time_delta = int(event.correlation.time_delta)

                    print(f"\n   {i}. {event.ui_event.type} ({ui_info})")
                    print(f"      Confidence: {confidence}%, Time Delta: +{time_delta}ms")
                    print(f"      Network Calls: {len(event.network_calls)}")

                    for nc in event.network_calls:
                        status = nc.response_status or "?"
                        print(f"        • {nc.method} {nc.path} → {status}")

        # Phase 5: Save Results
        print("\n" + "-" * 70)
        print("Phase 5: Saving Results")
        print("-" * 70)

        session.save_results(result)

        print(f"\n✅ All results saved!")
        print(f"\n   Output Directory: {metadata.output_dir}")
        print(f"   Files:")
        print(f"     • metadata.json - Session metadata")
        print(f"     • trace.zip - Playwright trace file")
        print(f"     • traffic.json - Captured network traffic")
        print(f"     • events.json - Parsed UI events")
        print(f"     • correlation.json - Correlated events")

        # Final Summary
        print("\n" + "=" * 70)
        print("Recording Session Complete!")
        print("=" * 70)
        print(f"\nSession ID: {metadata.session_id}")
        print(f"Output: {metadata.output_dir}")
        print(f"\nNext Steps:")
        print(f"  1. View trace in Playwright: playwright show-trace {metadata.trace_file}")
        print(f"  2. Inspect traffic: cat {metadata.traffic_path} | jq")
        print(f"  3. Review correlation: cat {metadata.correlation_file} | jq")
        print(f"  4. Generate tests from correlated events")
        print()

    except KeyboardInterrupt:
        print("\n\n⚠️  Recording interrupted by user")
        if session.metadata and session.metadata.status == "recording":
            print("Cleaning up...")
            await session.stop()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
