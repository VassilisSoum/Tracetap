"""
Progress Indicators - Text-based progress bars and spinners for CLI

Simple, dependency-free progress indicators for long-running operations.
"""

import sys
import time
from typing import Optional


class ProgressBar:
    """Simple progress bar with percentage and visual indicator"""

    def __init__(self, total: int, label: str = "", width: int = 30):
        """
        Initialize progress bar

        Args:
            total: Total number of items to process
            label: Optional label to display
            width: Width of progress bar in characters (default: 30)
        """
        self.total = max(total, 1)  # Avoid division by zero
        self.label = label
        self.width = width
        self.current = 0
        self.start_time = time.time()

    def update(self, amount: int = 1):
        """
        Update progress by amount

        Args:
            amount: Number of items processed (default: 1)
        """
        self.current = min(self.current + amount, self.total)
        self.print()

    def set(self, current: int):
        """
        Set progress to exact value

        Args:
            current: Current progress value
        """
        self.current = min(current, self.total)
        self.print()

    def finish(self):
        """Mark progress as complete"""
        self.current = self.total
        self.print()

    def print(self):
        """Print progress bar"""
        percentage = (self.current / self.total) * 100
        filled = int((self.current / self.total) * self.width)
        bar = "=" * filled + ">" + " " * (self.width - filled - 1)

        # Elapsed time
        elapsed = time.time() - self.start_time
        elapsed_str = self._format_time(elapsed)

        # ETA (if not complete)
        eta_str = ""
        if self.current > 0 and self.current < self.total:
            rate = self.current / elapsed
            remaining = (self.total - self.current) / rate
            eta_str = f" ETA: {self._format_time(remaining)}"

        # Build output
        label_str = f"{self.label} " if self.label else ""
        output = f"\r{label_str}[{bar}] {percentage:.0f}% ({self.current}/{self.total}) {elapsed_str}{eta_str}"

        # Pad to clear previous output
        sys.stdout.write(output.ljust(100))
        sys.stdout.flush()

        # Newline when done
        if self.current >= self.total:
            sys.stdout.write("\n")

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds to human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            mins = seconds / 60
            return f"{mins:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"


class Spinner:
    """Animated text spinner for indeterminate progress"""

    SPINNERS = {
        'dots': ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
        'line': ['-', '\\', '|', '/'],
        'arrow': ['←', '↖', '↑', '↗', '→', '↘', '↓', '↙'],
        'box': ['◰', '◳', '◲', '◱'],
        'simple': ['.', '..', '...', '']
    }

    def __init__(self, label: str = "", style: str = 'dots'):
        """
        Initialize spinner

        Args:
            label: Label to display
            style: Spinner style ('dots', 'line', 'arrow', 'box', 'simple')
        """
        self.label = label
        self.style = style if style in self.SPINNERS else 'dots'
        self.frames = self.SPINNERS[self.style]
        self.index = 0
        self.running = False

    def start(self):
        """Start spinner"""
        self.running = True
        self.index = 0
        self.print()

    def update(self, label: Optional[str] = None):
        """
        Update spinner frame and optionally label

        Args:
            label: New label (optional)
        """
        if label:
            self.label = label
        if self.running:
            self.index = (self.index + 1) % len(self.frames)
            self.print()

    def stop(self, final_label: Optional[str] = None):
        """
        Stop spinner and optionally show final message

        Args:
            final_label: Final message to display (optional)
        """
        self.running = False
        if final_label:
            self.label = final_label
            sys.stdout.write(f"\r{self.label}\n")
        else:
            sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()

    def print(self):
        """Print spinner frame"""
        frame = self.frames[self.index]
        output = f"\r{frame} {self.label}"
        sys.stdout.write(output.ljust(80))
        sys.stdout.flush()


class StatusLine:
    """Simple status message printer"""

    def __init__(self, verbose: bool = False):
        """
        Initialize status line

        Args:
            verbose: If True, show intermediate messages; if False, show final only
        """
        self.verbose = verbose

    def start(self, message: str):
        """Print start message"""
        if self.verbose:
            print(f"→ {message}")

    def progress(self, message: str):
        """Print progress message"""
        if self.verbose:
            print(f"  • {message}")

    def success(self, message: str):
        """Print success message"""
        print(f"✓ {message}")

    def error(self, message: str):
        """Print error message"""
        print(f"✗ {message}")

    def warning(self, message: str):
        """Print warning message"""
        print(f"⚠ {message}")

    def info(self, message: str):
        """Print info message"""
        if self.verbose:
            print(f"ℹ {message}")


def create_progress_bar(total: int, label: str = "", width: int = 30) -> ProgressBar:
    """Create a progress bar"""
    return ProgressBar(total, label, width)


def create_spinner(label: str = "", style: str = 'dots') -> Spinner:
    """Create a spinner"""
    return Spinner(label, style)


def create_status_line(verbose: bool = False) -> StatusLine:
    """Create a status line printer"""
    return StatusLine(verbose)
