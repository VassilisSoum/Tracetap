"""Enhanced CLI output with rich formatting.

Provides color-coded messages, progress indicators, and formatted output
for a professional CLI experience.
"""

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from contextlib import contextmanager
from typing import Optional, List, Tuple
import time

# Global console instance
console = Console()


# Color-coded output functions
def success(message: str):
    """Print success message in green."""
    console.print(f"✅ {message}", style="bold green")


def error(message: str):
    """Print error message in red."""
    console.print(f"❌ {message}", style="bold red")


def warning(message: str):
    """Print warning message in yellow."""
    console.print(f"⚠️  {message}", style="bold yellow")


def info(message: str):
    """Print info message in cyan."""
    console.print(f"ℹ️  {message}", style="cyan")


def section_header(title: str):
    """Print section header with horizontal rule."""
    console.rule(f"[bold cyan]{title}[/bold cyan]")


def print_panel(content: str, title: str = "", style: str = "cyan"):
    """Print content in a panel."""
    console.print(Panel(content, title=title, border_style=style))


def print_stats(stats: List[Tuple[str, str]]):
    """Print statistics in a formatted table."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="cyan", no_wrap=True)
    table.add_column(style="white")

    for label, value in stats:
        table.add_row(f"{label}:", value)

    console.print(table)


# Progress indicators
@contextmanager
def correlation_progress(total_events: int):
    """Context manager for correlation progress bar.

    Args:
        total_events: Total number of events to correlate

    Yields:
        Progress task object for updates

    Example:
        with correlation_progress(100) as progress:
            task = progress.add_task("Correlating events...", total=100)
            for i in range(100):
                # ... do work ...
                progress.update(task, advance=1)
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        yield progress


@contextmanager
def generation_progress(description: str = "Generating tests..."):
    """Context manager for indeterminate progress (spinning).

    Args:
        description: Description to display

    Yields:
        Progress task object

    Example:
        with generation_progress("Generating tests...") as progress:
            task = progress.add_task(description, total=None)
            # ... do work ...
            progress.update(task, description="Tests generated!")
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        yield progress


@contextmanager
def recording_progress():
    """Live progress display during recording.

    Yields:
        Dictionary with 'count' key to track event count

    Example:
        with recording_progress() as counter:
            for event in events:
                counter['count'] += 1
                # ... process event ...
    """
    table = Table.grid(padding=(0, 2))
    table.add_column(style="cyan", no_wrap=True)
    table.add_column(style="white")

    start_time = time.time()
    event_count = {"count": 0}

    def update_table():
        table.rows.clear()
        elapsed = time.time() - start_time
        table.add_row("⏱️  Elapsed:", f"{elapsed:.1f}s")
        table.add_row("📋 Events:", str(event_count["count"]))
        table.add_row("🌐 Status:", "[green]Recording...[/green]")
        return table

    with Live(update_table(), refresh_per_second=2, console=console) as live:
        yield event_count
        table.rows.clear()
        elapsed = time.time() - start_time
        table.add_row("⏱️  Elapsed:", f"{elapsed:.1f}s")
        table.add_row("📋 Events:", str(event_count["count"]))
        table.add_row("🌐 Status:", "[yellow]Stopping...[/yellow]")
        live.update(table)


def print_summary(
    title: str,
    stats: List[Tuple[str, str]],
    files: Optional[List[Tuple[str, int, str]]] = None,
):
    """Print completion summary with statistics and file list.

    Args:
        title: Summary title
        stats: List of (label, value) tuples for statistics
        files: Optional list of (path, lines, description) tuples

    Example:
        print_summary(
            "Tests Generated",
            [("Variations", "3"), ("Total lines", "450")],
            [("tests/login.spec.ts", 150, "Happy path")]
        )
    """
    console.print()
    success(title)

    if stats:
        console.print("\n   📊 Statistics:")
        for label, value in stats:
            console.print(f"      • {label}: [bold]{value}[/bold]")

    if files:
        console.print("\n   📝 Output files:")
        for file_path, lines, description in files:
            console.print(
                f"      • [magenta]{file_path}[/magenta] "
                f"({lines} lines) - {description}"
            )

    console.print()


def print_next_steps(steps: List[str]):
    """Print next steps guide.

    Args:
        steps: List of step descriptions

    Example:
        print_next_steps([
            "Review the generated test: cat tests/login.spec.ts",
            "Install Playwright: npm install -D @playwright/test",
            "Run tests: npx playwright test"
        ])
    """
    console.print("💡 Next steps:")
    for i, step in enumerate(steps, 1):
        console.print(f"   {i}. {step}")
    console.print()


def print_troubleshooting(issues: List[Tuple[str, str]]):
    """Print troubleshooting guide.

    Args:
        issues: List of (question, answer) tuples

    Example:
        print_troubleshooting([
            ("No correlation file?", "Run 'tracetap record' first"),
            ("API key error?", "Set ANTHROPIC_API_KEY environment variable")
        ])
    """
    console.print("\n🔍 Troubleshooting:")
    for question, answer in issues:
        console.print(f"   ❓ {question:<25} → {answer}")
    console.print()


def format_path(path: str) -> str:
    """Format file path for display with magenta color.

    Args:
        path: File path to format

    Returns:
        Formatted path string with markup

    Example:
        >>> info(f"Output: {format_path('/path/to/file.ts')}")
    """
    return f"[magenta]{path}[/magenta]"


def format_command(command: str) -> str:
    """Format command for display with bold white color.

    Args:
        command: Command to format

    Returns:
        Formatted command string with markup

    Example:
        >>> info(f"Run: {format_command('tracetap-record https://...')}")
    """
    return f"[bold white]{command}[/bold white]"


def prompt_confirm(question: str, default: bool = True) -> bool:
    """Prompt user for yes/no confirmation.

    Args:
        question: Question to ask
        default: Default answer (True for yes, False for no)

    Returns:
        User's answer as boolean

    Example:
        >>> if prompt_confirm("Continue with sanitization?"):
        ...     # proceed
    """
    from rich.prompt import Confirm

    return Confirm.ask(question, default=default)


def prompt_choice(question: str, choices: List[str], default: str = None) -> str:
    """Prompt user to select from choices.

    Args:
        question: Question to ask
        choices: List of valid choices
        default: Default choice (optional)

    Returns:
        Selected choice

    Example:
        >>> template = prompt_choice("Select template", ["basic", "comprehensive"])
    """
    from rich.prompt import Prompt

    return Prompt.ask(question, choices=choices, default=default)
