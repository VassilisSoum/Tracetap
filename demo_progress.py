#!/usr/bin/env python3
"""
Demo script showing progress indicators in action
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from tracetap.common.progress import ProgressBar, Spinner, StatusLine


def demo_progress_bar():
    print("\n=== Progress Bar Demo ===\n")

    status = StatusLine(verbose=True)
    status.start("Processing 100 requests...")

    progress = ProgressBar(100, label="Requests", width=30)

    for i in range(1, 101):
        progress.update()
        time.sleep(0.02)  # Simulate work

    status.success("All 100 requests processed")
    print()


def demo_spinner():
    print("=== Spinner Demo ===\n")

    spinner = Spinner("Analyzing endpoints...", style='dots')
    spinner.start()

    for i in range(20):
        time.sleep(0.1)
        spinner.update()

    spinner.stop(final_label="✓ Analysis complete (25 endpoints found)")
    print()


def demo_status_line():
    print("=== Status Line Demo ===\n")

    status = StatusLine(verbose=True)

    status.start("Generating OpenAPI contract...")
    time.sleep(0.3)
    status.progress("Analyzed 150 requests")
    time.sleep(0.2)
    status.progress("Grouped into 23 endpoints")
    time.sleep(0.2)
    status.progress("Generated operations")
    time.sleep(0.2)
    status.success("Contract created with 23 endpoints")
    print()


def demo_multiple_bars():
    print("=== Multiple Operations Demo ===\n")

    print("Contract creation workflow:")

    # Step 1
    status = StatusLine(verbose=True)
    status.start("Analyzing 125 requests...")
    progress = ProgressBar(125, label="Analyzing", width=25)
    for i in range(125):
        progress.update()
        time.sleep(0.01)
    progress.finish()
    status.success("Analysis complete (50 endpoints)")

    # Step 2
    print()
    status.start("Generating OpenAPI operations...")
    progress = ProgressBar(50, label="Operations", width=25)
    for i in range(50):
        progress.update()
        time.sleep(0.02)
    progress.finish()
    status.success("Operations generated")

    # Step 3
    print()
    status.start("Building specification...")
    time.sleep(0.5)
    status.success("OpenAPI 3.0 specification complete")
    print()


if __name__ == '__main__':
    demo_progress_bar()
    demo_spinner()
    demo_status_line()
    demo_multiple_bars()

    print("=== All demos complete ===\n")
