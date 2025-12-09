#!/usr/bin/env python3
"""
TraceTap Replay & Mock CLI

Command-line interface for TraceTap traffic replay and mock server functionality.

Commands:
    replay      - Replay captured HTTP traffic
    mock        - Start mock HTTP server
    variables   - Extract variables from captures
    scenario    - Generate YAML replay scenario
    validate    - Validate captured traffic

Examples:
    # Replay traffic to new endpoint
    python3 tracetap-replay.py replay session.json --target http://localhost:8080

    # Start mock server
    python3 tracetap-replay.py mock session.json --port 8080

    # Extract variables with AI
    python3 tracetap-replay.py variables session.json --ai

    # Generate YAML scenario with AI
    python3 tracetap-replay.py scenario session.json --output scenario.yaml --ai
"""

import argparse
import sys
import json
import os
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from tracetap.replay import TrafficReplayer, VariableExtractor, ReplayConfig
from tracetap.replay.replay_config import AIScenarioGenerator
from tracetap.mock import MockServer, MockConfig, create_mock_server
from tracetap.common import get_api_key_from_env, CaptureLoader


def cmd_replay(args):
    """
    Replay captured traffic to a target server.

    Args:
        args: Parsed command-line arguments
    """
    print(f"📡 TraceTap Traffic Replay")
    print(f"   Log file: {args.log_file}")

    if args.target:
        print(f"   Target: {args.target}")

    # Load replayer
    try:
        replayer = TrafficReplayer(
            log_file=args.log_file,
            timeout=args.timeout,
            verify_ssl=not args.no_verify_ssl,
            max_retries=args.retries
        )
    except Exception as e:
        print(f"❌ Failed to load captures: {e}")
        sys.exit(1)

    # Prepare variables
    variables = {}
    if args.variables:
        for var_pair in args.variables:
            if '=' in var_pair:
                key, value = var_pair.split('=', 1)
                variables[key] = value

    # Create filter function if provided
    filter_fn = None
    if args.filter_method:
        methods = [m.upper() for m in args.filter_method]
        filter_fn = lambda c: c.get('method', '').upper() in methods

    # Run replay
    print()
    result = replayer.replay(
        target_base_url=args.target,
        variables=variables if variables else None,
        max_workers=args.workers,
        filter_fn=filter_fn,
        verbose=args.verbose
    )

    # Save results if output specified
    if args.output:
        replayer.save_result(result, args.output)

    # Exit with error code if failures
    if result.failed_replays > 0:
        sys.exit(1)


def cmd_mock(args):
    """
    Start mock HTTP server serving captured responses.

    Args:
        args: Parsed command-line arguments
    """
    print(f"🎭 TraceTap Mock Server")

    # Get API key from environment only (SECURITY: Never accept API keys via CLI)
    api_key = get_api_key_from_env()

    # Show AI status
    if args.ai:
        if not api_key:
            print("⚠️  Warning: --ai enabled but ANTHROPIC_API_KEY environment variable not set")
            print("   Set it with: export ANTHROPIC_API_KEY=your_key")
            print("   AI features will be disabled")
        else:
            print(f"🤖 AI features enabled")

    # Show recording status
    if hasattr(args, 'record') and args.record:
        limit_desc = f"limit: {args.record_limit}" if args.record_limit > 0 else "unlimited"
        print(f"📹 Request recording enabled ({limit_desc})")

    # Show diff tracking status
    if hasattr(args, 'diff') and args.diff:
        print(f"🔍 Diff tracking enabled (threshold: {args.diff_threshold}, limit: {args.diff_limit})")

    # Show Faker status
    if hasattr(args, 'faker') and args.faker:
        locale_info = f"locale: {args.faker_locale}" if hasattr(args, 'faker_locale') else "locale: en_US"
        seed_info = f", seed: {args.faker_seed}" if hasattr(args, 'faker_seed') and args.faker_seed else ""
        print(f"🎲 Faker enabled ({locale_info}{seed_info})")

    # Show cache status
    cache_enabled = not (hasattr(args, 'no_cache') and args.no_cache)
    if cache_enabled:
        cache_size = args.cache_size if hasattr(args, 'cache_size') else 1000
        print(f"💾 Match caching enabled (max size: {cache_size})")
    else:
        print(f"💾 Match caching disabled")

    # Show verbose status
    if hasattr(args, 'verbose') and args.verbose:
        print(f"📋 Verbose mode enabled (detailed match logging)")

    # Create config
    config = MockConfig(
        host=args.host,
        port=args.port,
        matching_strategy=args.strategy,
        add_delay_ms=args.delay,
        chaos_enabled=args.chaos,
        chaos_failure_rate=args.chaos_rate,
        ai_enabled=args.ai if hasattr(args, 'ai') else False,
        ai_api_key=api_key,
        response_mode=args.response_mode if hasattr(args, 'response_mode') else 'static',
        admin_enabled=not args.no_admin,
        log_level=args.log_level,
        verbose_mode=args.verbose if hasattr(args, 'verbose') else False,
        recording_enabled=args.record if hasattr(args, 'record') else False,
        recording_limit=args.record_limit if hasattr(args, 'record_limit') else 1000,
        diff_enabled=args.diff if hasattr(args, 'diff') else False,
        diff_threshold=args.diff_threshold if hasattr(args, 'diff_threshold') else 0.8,
        diff_limit=args.diff_limit if hasattr(args, 'diff_limit') else 100,
        faker_enabled=args.faker if hasattr(args, 'faker') else False,
        faker_locale=args.faker_locale if hasattr(args, 'faker_locale') else 'en_US',
        faker_seed=args.faker_seed if hasattr(args, 'faker_seed') else None,
        cache_enabled=not (hasattr(args, 'no_cache') and args.no_cache),
        cache_max_size=args.cache_size if hasattr(args, 'cache_size') else 1000
    )

    # Create server
    try:
        server = MockServer(args.log_file, config=config)
    except Exception as e:
        print(f"❌ Failed to create mock server: {e}")
        sys.exit(1)

    # Start server (blocking)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n\n👋 Mock server stopped")


def cmd_variables(args):
    """
    Extract variables from captured traffic.

    Args:
        args: Parsed command-line arguments
    """
    print(f"🔍 TraceTap Variable Extraction")
    print(f"   Log file: {args.log_file}")

    # Load captures using standardized loader
    try:
        loader = CaptureLoader(args.log_file)
        captures = loader.load()
    except Exception as e:
        print(f"❌ Failed to load captures: {e}")
        sys.exit(1)

    print(f"   Captures: {len(captures)}")
    print()

    # Create extractor (SECURITY: API key from environment only)
    api_key = get_api_key_from_env()
    extractor = VariableExtractor(
        captures=captures,
        api_key=api_key,
        use_ai=args.ai
    )

    # Extract variables
    variables = extractor.extract_variables(verbose=True)

    print(f"\n📊 Found {len(variables)} variables:\n")

    # Display results
    for var in variables:
        print(f"  • {var.name} ({var.type})")
        print(f"    Locations: {', '.join(var.locations)}")
        print(f"    Examples: {', '.join(var.example_values[:3])}")
        if var.description:
            print(f"    Description: {var.description}")
        if var.pattern:
            print(f"    Pattern: {var.pattern}")
        print()

    # Save to JSON if output specified
    if args.output:
        output_data = [var.to_dict() for var in variables]
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"✅ Saved variables to {args.output}")


def cmd_scenario(args):
    """
    Generate YAML replay scenario from captures.

    Args:
        args: Parsed command-line arguments
    """
    print(f"📝 TraceTap Scenario Generation")
    print(f"   Log file: {args.log_file}")

    # Load captures using standardized loader
    try:
        loader = CaptureLoader(args.log_file)
        captures = loader.load()
    except Exception as e:
        print(f"❌ Failed to load captures: {e}")
        sys.exit(1)

    print(f"   Captures: {len(captures)}")

    if args.ai:
        # Use AI to generate scenario (SECURITY: API key from environment only)
        api_key = get_api_key_from_env()

        if not api_key:
            print("❌ AI generation requires ANTHROPIC_API_KEY environment variable")
            print("   Set it with: export ANTHROPIC_API_KEY=your_key")
            sys.exit(1)

        print("   Mode: AI-powered (using Claude)")
        print()

        generator = AIScenarioGenerator(api_key=api_key)

        scenario = generator.generate_scenario(
            captures=captures,
            intent=args.intent or "",
            scenario_name=args.name
        )

        if not scenario:
            print("❌ Failed to generate scenario with AI")
            sys.exit(1)

        print(f"✅ Generated scenario: {scenario.name}")
        print(f"   Steps: {len(scenario.steps)}")

    else:
        # Manual scenario creation (basic)
        print("   Mode: Basic (manual)")
        print()
        print("⚠️  Use --ai flag for intelligent scenario generation with Claude")
        print("    Example: python3 tracetap-replay.py scenario session.json --ai --intent 'User registration flow'")
        sys.exit(1)

    # Save scenario
    output_path = args.output or 'scenario.yaml'
    config = ReplayConfig()
    config.scenario = scenario
    config.save(output_path)

    print(f"\n✅ Saved scenario to {output_path}")


def cmd_validate(args):
    """
    Validate captured traffic and report issues.

    Args:
        args: Parsed command-line arguments
    """
    print(f"✓ TraceTap Traffic Validation")
    print(f"   Log file: {args.log_file}")

    # Load captures using standardized loader
    try:
        loader = CaptureLoader(args.log_file)
        captures = loader.load()
    except Exception as e:
        print(f"❌ Failed to load captures: {e}")
        sys.exit(1)

    print(f"   Total captures: {len(captures)}")
    print()

    # Validation checks
    errors = []
    warnings = []

    # Check for required fields
    for i, capture in enumerate(captures):
        if 'method' not in capture:
            errors.append(f"Capture {i}: Missing 'method' field")
        if 'url' not in capture:
            errors.append(f"Capture {i}: Missing 'url' field")
        if 'status' not in capture:
            warnings.append(f"Capture {i}: Missing 'status' field")

    # Check for error responses
    error_count = sum(1 for c in captures if c.get('status', 0) >= 400)
    if error_count > 0:
        warnings.append(f"{error_count} captures have error status codes (4xx/5xx)")

    # Check for missing response bodies
    missing_bodies = sum(1 for c in captures if not c.get('resp_body'))
    if missing_bodies > 0:
        warnings.append(f"{missing_bodies} captures have empty response bodies")

    # Report results
    if errors:
        print("❌ Errors found:")
        for error in errors:
            print(f"   • {error}")
        print()

    if warnings:
        print("⚠️  Warnings:")
        for warning in warnings:
            print(f"   • {warning}")
        print()

    if not errors and not warnings:
        print("✅ All validations passed!")
    else:
        print(f"📊 Summary:")
        print(f"   Errors: {len(errors)}")
        print(f"   Warnings: {len(warnings)}")

    # Exit with error if there are errors
    if errors:
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TraceTap Replay & Mock - Traffic replay and mock server for captured HTTP traffic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Replay traffic to localhost
  %(prog)s replay session.json --target http://localhost:8080

  # Start mock server with fuzzy matching
  %(prog)s mock session.json --port 8080 --strategy fuzzy

  # Extract variables with AI
  %(prog)s variables session.json --ai --output variables.json

  # Generate test scenario with AI
  %(prog)s scenario session.json --ai --intent "User registration flow" --output test.yaml

  # Validate captured traffic
  %(prog)s validate session.json

For more information: https://github.com/yourusername/tracetap
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # --- REPLAY command ---
    replay_parser = subparsers.add_parser('replay', help='Replay captured traffic')
    replay_parser.add_argument('log_file', help='TraceTap JSON log file')
    replay_parser.add_argument('-t', '--target', help='Target base URL (e.g., http://localhost:8080)')
    replay_parser.add_argument('-v', '--variables', nargs='+', help='Variables (key=value)')
    replay_parser.add_argument('-w', '--workers', type=int, default=5, help='Concurrent workers (default: 5)')
    replay_parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds (default: 30)')
    replay_parser.add_argument('--retries', type=int, default=3, help='Max retries per request (default: 3)')
    replay_parser.add_argument('--no-verify-ssl', action='store_true', help='Disable SSL verification')
    replay_parser.add_argument('--filter-method', nargs='+', help='Filter by HTTP methods (e.g., GET POST)')
    replay_parser.add_argument('-o', '--output', help='Save results to JSON file')
    replay_parser.add_argument('--verbose', action='store_true', help='Verbose output')

    # --- MOCK command ---
    mock_parser = subparsers.add_parser('mock', help='Start mock HTTP server')
    mock_parser.add_argument('log_file', help='TraceTap JSON log file')
    mock_parser.add_argument('--host', default='127.0.0.1', help='Host to bind (default: 127.0.0.1)')
    mock_parser.add_argument('-p', '--port', type=int, default=8080, help='Port to bind (default: 8080)')
    mock_parser.add_argument('-s', '--strategy', choices=['exact', 'fuzzy', 'pattern', 'semantic'], default='fuzzy',
                           help='Matching strategy (default: fuzzy)')
    mock_parser.add_argument('--delay', type=int, default=0, help='Add fixed delay in ms (default: 0)')
    mock_parser.add_argument('--chaos', action='store_true', help='Enable chaos engineering')
    mock_parser.add_argument('--chaos-rate', type=float, default=0.1, help='Chaos failure rate (default: 0.1)')
    mock_parser.add_argument('--ai', action='store_true', help='Enable AI-powered features (semantic matching, intelligent responses). Requires ANTHROPIC_API_KEY env var')
    mock_parser.add_argument('--response-mode', choices=['static', 'template', 'transform', 'faker', 'ai', 'intelligent'],
                           default='static', help='Response generation mode (default: static)')
    mock_parser.add_argument('--faker', action='store_true', help='Enable Faker for realistic data generation')
    mock_parser.add_argument('--faker-locale', default='en_US', help='Faker locale (default: en_US)')
    mock_parser.add_argument('--faker-seed', type=int, help='Faker seed for reproducible data')
    mock_parser.add_argument('--no-admin', action='store_true', help='Disable admin API')
    mock_parser.add_argument('--log-level', default='info', choices=['debug', 'info', 'warning', 'error'],
                           help='Log level (default: info)')
    mock_parser.add_argument('--verbose', action='store_true', help='Show detailed match information for each request')
    mock_parser.add_argument('--record', action='store_true', help='Enable request recording during mock operation')
    mock_parser.add_argument('--record-limit', type=int, default=1000, help='Maximum requests to record (default: 1000, 0=unlimited)')
    mock_parser.add_argument('--diff', action='store_true', help='Enable request diff tracking for debugging')
    mock_parser.add_argument('--diff-threshold', type=float, default=0.8, help='Track diffs when match score below this (default: 0.8)')
    mock_parser.add_argument('--diff-limit', type=int, default=100, help='Maximum diffs to store (default: 100, 0=unlimited)')
    mock_parser.add_argument('--no-cache', action='store_true', help='Disable match result caching')
    mock_parser.add_argument('--cache-size', type=int, default=1000, help='Maximum cache entries (default: 1000)')

    # --- VARIABLES command ---
    variables_parser = subparsers.add_parser('variables', help='Extract variables from captures')
    variables_parser.add_argument('log_file', help='TraceTap JSON log file')
    variables_parser.add_argument('--ai', action='store_true', help='Use Claude AI for intelligent extraction. Requires ANTHROPIC_API_KEY env var')
    variables_parser.add_argument('-o', '--output', help='Save variables to JSON file')

    # --- SCENARIO command ---
    scenario_parser = subparsers.add_parser('scenario', help='Generate YAML replay scenario')
    scenario_parser.add_argument('log_file', help='TraceTap JSON log file')
    scenario_parser.add_argument('--ai', action='store_true', help='Use Claude AI for intelligent generation. Requires ANTHROPIC_API_KEY env var')
    scenario_parser.add_argument('--intent', help='Scenario intent description for AI')
    scenario_parser.add_argument('--name', help='Scenario name')
    scenario_parser.add_argument('-o', '--output', help='Output YAML file (default: scenario.yaml)')

    # --- VALIDATE command ---
    validate_parser = subparsers.add_parser('validate', help='Validate captured traffic')
    validate_parser.add_argument('log_file', help='TraceTap JSON log file')

    # Parse arguments
    args = parser.parse_args()

    # Dispatch to command handler
    if args.command == 'replay':
        cmd_replay(args)
    elif args.command == 'mock':
        cmd_mock(args)
    elif args.command == 'variables':
        cmd_variables(args)
    elif args.command == 'scenario':
        cmd_scenario(args)
    elif args.command == 'validate':
        cmd_validate(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
