"""
TraceTap CLI - unified entry point.

All commands are accessible via: tracetap <command>

Commands:
    record    - Record browser interactions and network traffic
    generate  - Generate Playwright tests from a recorded session
    proxy     - Run standalone HTTP/HTTPS proxy for API capture
    doctor    - Check prerequisites and system configuration
"""

import click

from tracetap import __version__


@click.group()
@click.version_option(version=__version__, prog_name="tracetap")
def cli():
    """TraceTap - Record browser tests, generate Playwright code with AI."""
    pass


# Import and register subcommands
from .cmd_record import record
from .cmd_generate import generate
from .cmd_proxy import proxy
from .cmd_doctor import doctor

cli.add_command(record)
cli.add_command(generate)
cli.add_command(proxy)
cli.add_command(doctor)
