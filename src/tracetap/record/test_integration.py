#!/usr/bin/env python3
"""
Integration test for mitmproxy + recording session.

This script tests the full recording workflow:
1. Start mitmproxy
2. Start trace recording with proxy
3. Simulate manual interaction (or wait for user input)
4. Stop recording
5. Parse and correlate events
6. Verify results

Usage:
    python test_integration.py [url]

Example:
    python test_integration.py https://example.com
"""

import asyncio
import sys
from pathlib import Path

from session import RecordingSession, RecorderOptions


async def main():
    """Run integration test."""
    # Get URL from command line or use default
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"

    print("=" * 60)
    print("TraceTap Recording Session Integration Test")
    print("=" * 60)
    print(f"\nTarget URL: {url}")
    print("\nThis test will:")
    print("  1. Start mitmproxy proxy on port 8888")
    print("  2. Launch browser with proxy configured")
    print("  3. Record your interactions")
    print("  4. Capture network traffic")
    print("  5. Correlate UI events with network calls")
    print("\n" + "=" * 60 + "\n")

    # Create session
    session = RecordingSession(
        session_name="integration-test",
        output_dir="test_recordings",
        recorder_options=RecorderOptions(
            headless=False,  # Show browser for manual testing
            screenshots=True,
            snapshots=True,
        ),
        proxy_port=8888,
    )

    try:
        # Start recording
        print("Starting recording session...")
        metadata = await session.start(url)
        print(f"✅ Session started: {metadata.session_id}")
        print(f"   Output: {metadata.output_dir}")

        # Wait for user to complete interactions
        print("\n" + "=" * 60)
        print("👉 Interact with the browser now")
        print("👉 Press ENTER when done to stop recording")
        print("=" * 60 + "\n")
        input()

        # Stop recording
        print("Stopping recording session...")
        metadata = await session.stop()
        print(f"✅ Session stopped")
        print(f"   Duration: {metadata.duration:.1f}s")
        print(f"   Trace: {metadata.trace_file}")
        print(f"   Traffic: {metadata.traffic_path}")

        # Analyze session
        print("\nAnalyzing session...")
        result = await session.analyze()

        # Display results
        print("\n" + "=" * 60)
        print("Results")
        print("=" * 60)

        if result.parse_result:
            print(f"\n📊 UI Events: {len(result.parse_result.events)}")
            for i, event in enumerate(result.parse_result.events[:5], 1):
                print(f"   {i}. {event.type} - {getattr(event, 'selector', getattr(event, 'url', ''))}")
            if len(result.parse_result.events) > 5:
                print(f"   ... and {len(result.parse_result.events) - 5} more")

        if result.correlation_result:
            print(f"\n🔗 Correlation:")
            print(f"   Correlated Events: {len(result.correlation_result.correlated_events)}")
            print(f"   Correlation Rate: {result.correlation_result.stats['correlation_rate'] * 100:.1f}%")
            print(f"   Average Confidence: {result.correlation_result.stats['average_confidence'] * 100:.1f}%")

            # Show sample correlated events
            print(f"\n   Sample Correlations:")
            for event in result.correlation_result.correlated_events[:3]:
                print(f"   • {event.ui_event.type} → {len(event.network_calls)} network call(s)")
                for nc in event.network_calls:
                    print(f"      - {nc.method} {nc.path} ({nc.response_status})")

        # Save results
        print("\nSaving results...")
        session.save_results(result)
        print(f"✅ Results saved to: {metadata.output_dir}")

        print("\n" + "=" * 60)
        print("Test Complete!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        if session.metadata and session.metadata.status == "recording":
            print("Cleaning up...")
            await session.stop()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
