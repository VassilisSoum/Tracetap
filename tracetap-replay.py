#!/usr/bin/env python3
"""
TraceTap Replay & Mock CLI

Command-line interface for TraceTap traffic replay and mock server functionality.

Commands:
    mock                - Start mock HTTP server
    generate-regression - Generate Playwright regression tests
    suggest-tests       - Generate AI-powered test suggestions
    create-contract     - Generate OpenAPI contract from traffic
    verify-contract     - Verify contract compatibility and detect breaking changes

Examples:
    # Start mock server
    python3 tracetap-replay.py mock session.json --port 8080

    # Generate Playwright regression tests
    python3 tracetap-replay.py generate-regression session.json -o tests/regression.spec.ts

    # Generate AI test suggestions
    python3 tracetap-replay.py suggest-tests session.json -o suggestions.md

    # Generate OpenAPI contract
    python3 tracetap-replay.py create-contract session.json -o contract.yaml

    # Verify contract compatibility
    python3 tracetap-replay.py verify-contract baseline.yaml current.yaml --fail-on-breaking
"""

import argparse
import sys
import json
import os
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from tracetap.mock import MockServer, MockConfig, create_mock_server
from tracetap.common import get_api_key_from_env, CaptureLoader
from tracetap.generators.regression_generator import generate_regression_tests


def cmd_mock(args):
    """
    Start mock HTTP server serving captured responses.

    Args:
        args: Parsed command-line arguments
    """
    print(f"🎭 TraceTap Mock Server")

    # Validate log file exists
    if not Path(args.log_file).exists():
        print(f"\n❌ Error: Log file not found")
        print(f"   Path: {args.log_file}")
        print(f"   Expected file at: {Path(args.log_file).absolute()}")
        print(f"\nNext steps:")
        print(f"  • Check the file path is correct")
        print(f"  • Run: ls -la {args.log_file}")
        print(f"  • Use --help to see examples")
        sys.exit(1)

    # Validate port number
    if not (1 <= args.port <= 65535):
        print(f"\n❌ Error: Invalid port number")
        print(f"   Port: {args.port}")
        print(f"   Valid range: 1-65535")
        print(f"\nNext steps:")
        print(f"  • Use a port between 1 and 65535")
        print(f"  • Ports < 1024 require root/admin")
        print(f"  • Try: python3 tracetap-replay.py mock session.json --port 8080")
        sys.exit(1)

    # Validate delay value
    if args.delay < 0:
        print(f"\n❌ Error: Invalid delay value")
        print(f"   Delay: {args.delay}ms")
        print(f"   Must be 0 or positive")
        sys.exit(1)

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
        cache_enabled=not (hasattr(args, 'no_cache') and args.no_cache),
        cache_max_size=args.cache_size if hasattr(args, 'cache_size') else 1000
    )

    # Create server
    try:
        server = MockServer(args.log_file, config=config)
    except FileNotFoundError:
        print(f"\n❌ Error: Log file not found")
        print(f"   File: {args.log_file}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Error: Invalid log file format")
        print(f"   Reason: {e}")
        print(f"\nExpected JSON format with HTTP captures")
        sys.exit(1)
    except PermissionError as e:
        print(f"\n❌ Error: Permission denied")
        print(f"   Reason: {e}")
        print(f"\nPossible causes:")
        print(f"  • Port {args.port} already in use")
        print(f"  • Port < 1024 requires root/sudo")
        print(f"  • Insufficient permissions on log file")
        print(f"\nNext steps:")
        print(f"  • Try a different port: --port 8081")
        print(f"  • Check if port is in use: lsof -i :{args.port}")
        print(f"  • Use sudo for ports < 1024: sudo python3 tracetap-replay.py mock ...")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Failed to create mock server")
        print(f"   Error: {e}")
        print(f"\nNext steps:")
        print(f"  • Validate log file: python3 -m json.tool {args.log_file}")
        print(f"  • Check server logs for more details")
        sys.exit(1)

    # Start server (blocking)
    try:
        print(f"\n🚀 Starting mock server at http://{args.host}:{args.port}")
        print(f"   Press Ctrl+C to stop")
        print()
        server.start()
    except OSError as e:
        print(f"\n❌ Error: Failed to start server")
        print(f"   Reason: {e}")
        print(f"\nCommon causes:")
        print(f"  • Port {args.port} is already in use")
        print(f"  • Address {args.host} is invalid")
        print(f"\nNext steps:")
        print(f"  • Find what's using port {args.port}: lsof -i :{args.port}")
        print(f"  • Use a different port: --port 8081")
        print(f"  • Or kill the process: kill -9 <PID>")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Mock server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)

def cmd_generate_regression(args):
    """
    Generate Playwright regression tests from captured traffic.

    Args:
        args: Parsed command-line arguments
    """
    print(f"🎯 TraceTap Regression Test Generator")
    print(f"   Input: {args.log_file}")
    print(f"   Output: {args.output}")

    # Validate input file exists
    if not Path(args.log_file).exists():
        print(f"\n❌ Error: Input file not found")
        print(f"   Path: {args.log_file}")
        print(f"   Expected file at: {Path(args.log_file).absolute()}")
        print(f"\nNext steps:")
        print(f"  • Check the file path is correct")
        print(f"  • Run: ls -la {args.log_file}")
        sys.exit(1)

    # Validate output directory is writable
    output_path = Path(args.output)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Test write permission
        test_file = output_path.parent / '.test_write'
        test_file.touch()
        test_file.unlink()
    except PermissionError:
        print(f"\n❌ Error: Cannot write to output directory")
        print(f"   Path: {output_path.parent}")
        print(f"\nNext steps:")
        print(f"  • Check directory permissions: ls -ld {output_path.parent}")
        print(f"  • Try different output path: -o tests/my_tests.spec.ts")
        print(f"  • Use sudo if necessary")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: Cannot access output directory")
        print(f"   Path: {output_path.parent}")
        print(f"   Error: {e}")
        sys.exit(1)

    # Determine grouping strategy
    grouping = args.grouping if hasattr(args, 'grouping') and args.grouping else 'endpoint'
    if grouping not in ['endpoint', 'flow']:
        print(f"\n❌ Error: Invalid grouping strategy")
        print(f"   Value: {grouping}")
        print(f"   Valid options: endpoint, flow")
        sys.exit(1)
    print(f"   Grouping: {grouping}")

    # Parse assertion types
    assert_types = []
    if hasattr(args, 'assert_status') and args.assert_status:
        assert_types.append('status-codes')
    if hasattr(args, 'assert_schema') and args.assert_schema:
        assert_types.append('response-schemas')
    if hasattr(args, 'assert_fields') and args.assert_fields:
        assert_types.append('critical-fields')
    if hasattr(args, 'assert_snapshot') and args.assert_snapshot:
        assert_types.append('snapshots')

    # Default to status codes if none specified
    if not assert_types:
        assert_types = ['status-codes']

    print(f"   Assertions: {', '.join(assert_types)}")

    # Parse and validate critical fields
    critical_fields = None
    if hasattr(args, 'critical_fields') and args.critical_fields:
        critical_fields = [f.strip() for f in args.critical_fields.split(',')]
        if any(not f for f in critical_fields):
            print(f"\n❌ Error: Invalid critical fields format")
            print(f"   Value: {args.critical_fields}")
            print(f"   Format: comma-separated paths (e.g., user.id,order.total)")
            sys.exit(1)
        print(f"   Critical fields: {', '.join(critical_fields)}")
    elif hasattr(args, 'assert_fields') and args.assert_fields:
        print(f"\n⚠️  Warning: --assert-fields enabled but no critical fields specified")
        print(f"   Use: --critical-fields user.id,order.total")

    print()

    # Generate regression tests
    try:
        success = generate_regression_tests(
            json_file=args.log_file,
            output_file=args.output,
            grouping=grouping,
            base_url=args.base_url if hasattr(args, 'base_url') else None,
            assert_types=assert_types,
            critical_fields=critical_fields
        )

        if success:
            print()
            print(f"🎉 Success! Regression tests generated")
            print(f"   File: {args.output}")
            print()
            print(f"Next steps:")
            print(f"  1. Review generated tests:")
            print(f"     cat {args.output}")
            print(f"  2. Install Playwright (if not already):")
            print(f"     npm install -D @playwright/test")
            print(f"  3. Configure base URL in playwright.config.ts (if needed)")
            print(f"  4. Run tests:")
            print(f"     npx playwright test {args.output}")
            print(f"  5. View report:")
            print(f"     npx playwright show-report")
            print()
        else:
            print(f"\n❌ Failed to generate regression tests")
            print(f"   File: {args.log_file}")
            print(f"\nPossible causes:")
            print(f"  • Empty or invalid capture file")
            print(f"  • Missing required fields in captures")
            print(f"\nNext steps:")
            print(f"  • Validate file: python3 tracetap-replay.py validate {args.log_file}")
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"\n❌ Error: Input file not found")
        print(f"   File: {args.log_file}")
        print(f"   Error: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"\n❌ Error: Invalid JSON in input file")
        print(f"   File: {args.log_file}")
        print(f"   Error at line {e.lineno}: {e.msg}")
        print(f"\nNext steps:")
        print(f"  • Validate JSON: python3 -m json.tool {args.log_file}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error generating regression tests")
        print(f"   Error: {e}")
        if hasattr(args, 'verbose') and args.verbose:
            import traceback
            traceback.print_exc()
        print(f"\nNext steps:")
        print(f"  • Try with --verbose for detailed error info")
        print(f"  • Check that captures are valid: python3 tracetap-replay.py validate {args.log_file}")
        sys.exit(1)


def cmd_suggest_tests(args):
    """
    Generate AI-powered test suggestions from captured traffic.

    Args:
        args: Parsed command-line arguments
    """
    print(f"🤖 TraceTap AI Test Suggestion Engine")
    print(f"   Input: {args.log_file}")

    # Validate input file exists
    if not Path(args.log_file).exists():
        print(f"\n❌ Error: Input file not found")
        print(f"   Path: {args.log_file}")
        print(f"   Expected file at: {Path(args.log_file).absolute()}")
        print(f"\nNext steps:")
        print(f"  • Check the file path is correct")
        print(f"  • Run: ls -la {args.log_file}")
        sys.exit(1)

    # Determine output destination
    if args.output:
        print(f"   Output: {args.output}")
        # Validate output directory
        output_path = Path(args.output)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            print(f"\n❌ Error: Cannot write to output directory")
            print(f"   Path: {output_path.parent}")
            print(f"\nNext steps:")
            print(f"  • Check directory permissions")
            print(f"  • Try different output path")
            sys.exit(1)
    else:
        print(f"   Output: stdout")

    # Check AI availability
    use_ai = not args.no_ai
    if use_ai:
        print(f"   AI Enhancement: Enabled")
    else:
        print(f"   AI Enhancement: Disabled (--no-ai)")

    print()

    try:
        from tracetap.ai.test_suggester import generate_test_suggestions

        # Generate suggestions
        markdown = generate_test_suggestions(
            json_file=args.log_file,
            output_file=args.output,
            use_ai=use_ai,
            verbose=True
        )

        # If no output file, print to stdout
        if not args.output:
            if not markdown:
                print("\n⚠️  No suggestions generated")
                print("   Possible causes:")
                print("   • Input file is empty")
                print("   • No suitable test patterns found")
                sys.exit(0)
            print()
            print(markdown)

        print()
        print(f"🎉 Success! Test suggestions generated")
        print()

        if args.output:
            file_size = Path(args.output).stat().st_size if Path(args.output).exists() else 0
            print(f"   Saved to: {args.output} ({file_size} bytes)")
            print()
            print(f"Next steps:")
            print(f"  1. Review suggestions:")
            print(f"     cat {args.output}")
            print(f"  2. Identify high-priority tests")
            print(f"  3. Implement as Playwright tests:")
            print(f"     npx playwright test")
            print()
        else:
            print(f"Tip: Use -o to save suggestions to a file:")
            print(f"  python3 tracetap-replay.py suggest-tests {args.log_file} -o suggestions.md")
            print()

    except ImportError as e:
        print(f"\n❌ Error: Missing dependencies")
        print(f"   {e}")
        print(f"\nInstall required packages:")
        print(f"   pip install anthropic")
        print(f"\nOr install all optional dependencies:")
        print(f"   pip install -e .[ai]")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n❌ Error: File not found")
        print(f"   File: {args.log_file}")
        print(f"   Error: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"\n❌ Error: Invalid JSON in input file")
        print(f"   File: {args.log_file}")
        print(f"   Error at line {e.lineno}: {e.msg}")
        print(f"\nNext steps:")
        print(f"  • Validate JSON: python3 -m json.tool {args.log_file}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Error: Invalid input data")
        print(f"   Reason: {e}")
        print(f"\nNext steps:")
        print(f"  • Validate captures: python3 tracetap-replay.py validate {args.log_file}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error generating test suggestions")
        print(f"   Error: {e}")
        if hasattr(args, 'verbose') and args.verbose:
            import traceback
            traceback.print_exc()
        print(f"\nNext steps:")
        print(f"  • Try with --no-ai to disable AI enhancement")
        print(f"  • Validate input: python3 tracetap-replay.py validate {args.log_file}")
        print(f"  • Use --verbose for detailed error info")
        sys.exit(1)


def cmd_create_contract(args):
    """
    Generate OpenAPI contract from captured traffic.

    Args:
        args: Parsed command-line arguments
    """
    print(f"📋 TraceTap Contract Creator")
    print(f"   Input: {args.log_file}")
    print(f"   Output: {args.output}")

    # Validate input file exists
    if not Path(args.log_file).exists():
        print(f"\n❌ Error: Input file not found")
        print(f"   Path: {args.log_file}")
        print(f"   Expected file at: {Path(args.log_file).absolute()}")
        print(f"\nNext steps:")
        print(f"  • Check the file path is correct")
        print(f"  • Run: ls -la {args.log_file}")
        sys.exit(1)

    # Validate output directory
    output_path = Path(args.output)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        print(f"\n❌ Error: Cannot write to output directory")
        print(f"   Path: {output_path.parent}")
        print(f"\nNext steps:")
        print(f"  • Check directory permissions")
        print(f"  • Try different output path")
        sys.exit(1)

    if hasattr(args, 'title') and args.title:
        print(f"   Title: {args.title}")
    if hasattr(args, 'version') and args.version:
        print(f"   Version: {args.version}")

    print()

    try:
        from tracetap.contract.contract_creator import create_contract_from_traffic

        # Create contract
        success = create_contract_from_traffic(
            json_file=args.log_file,
            output_file=args.output,
            title=args.title if hasattr(args, 'title') and args.title else "API",
            version=args.version if hasattr(args, 'version') and args.version else "1.0.0",
            verbose=True
        )

        if success:
            file_size = Path(args.output).stat().st_size if Path(args.output).exists() else 0
            print()
            print(f"🎉 Success! OpenAPI contract generated")
            print(f"   File: {args.output} ({file_size} bytes)")
            print()
            print(f"Next steps:")
            print(f"  1. Review contract:")
            print(f"     cat {args.output}")
            print(f"  2. Validate OpenAPI schema:")
            print(f"     pip install openapi-spec-validator")
            print(f"     python3 -m openapi_spec_validator {args.output}")
            print(f"  3. Use as baseline for contract verification:")
            print(f"     cp {args.output} baseline-contract.yaml")
            print(f"  4. Generate new contract from current API:")
            print(f"     python3 tracetap-replay.py create-contract session.json -o current-contract.yaml")
            print(f"  5. Verify compatibility:")
            print(f"     python3 tracetap-replay.py verify-contract baseline-contract.yaml current-contract.yaml")
            print()
        else:
            print(f"\n❌ Failed to generate contract")
            print(f"   File: {args.log_file}")
            print(f"\nPossible causes:")
            print(f"  • Empty or invalid capture file")
            print(f"  • Missing required fields in captures")
            print(f"\nNext steps:")
            print(f"  • Validate file: python3 tracetap-replay.py validate {args.log_file}")
            sys.exit(1)

    except ImportError as e:
        print(f"\n❌ Error: Missing dependencies")
        print(f"   Module: {e}")
        print(f"\nInstall required packages:")
        print(f"   pip install pyyaml")
        print(f"\nOr install all optional dependencies:")
        print(f"   pip install -e .[contract]")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n❌ Error: File not found")
        print(f"   File: {args.log_file}")
        print(f"   Error: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"\n❌ Error: Invalid JSON in input file")
        print(f"   File: {args.log_file}")
        print(f"   Error at line {e.lineno}: {e.msg}")
        print(f"\nNext steps:")
        print(f"  • Validate JSON: python3 -m json.tool {args.log_file}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Error: Invalid input data")
        print(f"   Reason: {e}")
        print(f"\nNext steps:")
        print(f"  • Validate captures: python3 tracetap-replay.py validate {args.log_file}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error generating contract")
        print(f"   Error: {e}")
        if hasattr(args, 'verbose') and args.verbose:
            import traceback
            traceback.print_exc()
        print(f"\nNext steps:")
        print(f"  • Validate input: python3 tracetap-replay.py validate {args.log_file}")
        print(f"  • Use --verbose for detailed error info")
        sys.exit(1)


def cmd_verify_contract(args):
    """
    Verify contract compatibility and detect breaking changes.

    Args:
        args: Parsed command-line arguments
    """
    print(f"🔍 TraceTap Contract Verifier")
    print(f"   Baseline: {args.baseline}")
    print(f"   Current: {args.current}")

    # Validate baseline file exists
    if not Path(args.baseline).exists():
        print(f"\n❌ Error: Baseline contract not found")
        print(f"   Path: {args.baseline}")
        print(f"   Expected file at: {Path(args.baseline).absolute()}")
        print(f"\nNext steps:")
        print(f"  • Generate baseline contract:")
        print(f"    python3 tracetap-replay.py create-contract captures.json -o {args.baseline}")
        print(f"  • Or check the file path is correct")
        sys.exit(1)

    # Validate current file exists
    if not Path(args.current).exists():
        print(f"\n❌ Error: Current contract not found")
        print(f"   Path: {args.current}")
        print(f"   Expected file at: {Path(args.current).absolute()}")
        print(f"\nNext steps:")
        print(f"  • Generate current contract:")
        print(f"    python3 tracetap-replay.py create-contract captures.json -o {args.current}")
        print(f"  • Or check the file path is correct")
        sys.exit(1)

    if args.output:
        print(f"   Report: {args.output}")
        # Validate output directory
        output_path = Path(args.output)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            print(f"\n❌ Error: Cannot write to output directory")
            print(f"   Path: {output_path.parent}")
            sys.exit(1)

    # Validate format
    valid_formats = ['text', 'json', 'markdown']
    format_arg = args.format if hasattr(args, 'format') else 'text'
    if format_arg not in valid_formats:
        print(f"\n❌ Error: Invalid report format")
        print(f"   Format: {format_arg}")
        print(f"   Valid formats: {', '.join(valid_formats)}")
        sys.exit(1)

    print()

    try:
        from tracetap.contract.contract_verifier import verify_contracts

        # Verify contracts
        is_compatible, changes = verify_contracts(
            baseline_file=args.baseline,
            current_file=args.current,
            output_file=args.output,
            format=format_arg,
            verbose=True
        )

        print()

        if is_compatible:
            print(f"✓ Contracts are compatible")
            print(f"  No breaking changes detected")
            print()
            if changes:
                print(f"Non-breaking changes:")
                for change in changes:
                    print(f"  • {change}")
                print()
            print(f"✅ Safe to deploy!")
            sys.exit(0)
        else:
            print(f"✗ BREAKING CHANGES DETECTED!")
            print()
            if changes:
                print(f"Changes:")
                for change in changes:
                    print(f"  • {change}")
                print()

            if args.fail_on_breaking:
                print(f"❌ Failing due to --fail-on-breaking flag")
                if args.output:
                    print(f"   Full report: {args.output}")
                sys.exit(1)
            else:
                print(f"⚠️  Breaking changes found")
                print(f"   Use --fail-on-breaking to fail CI builds")
                if args.output:
                    print(f"   Report saved to: {args.output}")
                sys.exit(0)

    except ImportError as e:
        print(f"\n❌ Error: Missing dependencies")
        print(f"   Module: {e}")
        print(f"\nInstall required packages:")
        print(f"   pip install pyyaml")
        print(f"\nOr install all optional dependencies:")
        print(f"   pip install -e .[contract]")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n❌ Error: Contract file not found")
        print(f"   Error: {e}")
        print(f"\nNext steps:")
        print(f"  • Verify file exists: ls -la {args.baseline} {args.current}")
        print(f"  • Generate contracts if missing:")
        print(f"    python3 tracetap-replay.py create-contract captures.json -o {args.baseline}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"\n❌ Error: Invalid JSON in contract file")
        print(f"   Error at line {e.lineno}: {e.msg}")
        print(f"\nNext steps:")
        print(f"  • Validate JSON: python3 -m json.tool {args.baseline}")
        print(f"  • Or: python3 -m json.tool {args.current}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Error: Invalid contract format")
        print(f"   Reason: {e}")
        print(f"\nExpected format: OpenAPI 3.0 YAML or JSON")
        print(f"\nNext steps:")
        print(f"  • Regenerate contracts using:")
        print(f"    python3 tracetap-replay.py create-contract captures.json -o {args.baseline}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error verifying contracts")
        print(f"   Error: {e}")
        if hasattr(args, 'verbose') and args.verbose:
            import traceback
            traceback.print_exc()
        print(f"\nNext steps:")
        print(f"  • Use --verbose for detailed error info")
        print(f"  • Check contract files are valid OpenAPI format")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TraceTap Replay & Mock - Traffic replay and mock server for captured HTTP traffic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start mock server with fuzzy matching
  %(prog)s mock session.json --port 8080 --strategy fuzzy

  # Generate Playwright regression tests
  %(prog)s generate-regression session.json -o tests/regression.spec.ts --assert-schema

  # Generate AI test suggestions
  %(prog)s suggest-tests session.json -o suggestions.md

  # Generate OpenAPI contract
  %(prog)s create-contract session.json -o contract.yaml

  # Verify contract compatibility
  %(prog)s verify-contract baseline.yaml current.yaml --fail-on-breaking

For more information: https://github.com/yourusername/tracetap
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # --- MOCK command ---
    mock_parser = subparsers.add_parser('mock', help='Start mock HTTP server')
    mock_parser.add_argument('log_file', help='TraceTap JSON log file')
    mock_parser.add_argument('--host', default='127.0.0.1', help='Host to bind (default: 127.0.0.1)')
    mock_parser.add_argument('-p', '--port', type=int, default=8080, help='Port to bind (default: 8080)')
    mock_parser.add_argument('-s', '--strategy', choices=['exact', 'fuzzy', 'pattern', 'semantic'], default='fuzzy',
                           help='Matching strategy (default: fuzzy)')
    mock_parser.add_argument('--delay', type=int, default=0, help='Add fixed delay in ms (default: 0)')
    mock_parser.add_argument('--ai', action='store_true', help='Enable AI-powered features (semantic matching, intelligent responses). Requires ANTHROPIC_API_KEY env var')
    mock_parser.add_argument('--response-mode', choices=['static', 'template', 'transform', 'ai', 'intelligent'],
                           default='static', help='Response generation mode (default: static)')
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

    # --- GENERATE-REGRESSION command ---
    regression_parser = subparsers.add_parser('generate-regression',
                                             help='Generate Playwright regression tests from captured traffic')
    regression_parser.add_argument('log_file', help='TraceTap JSON log file')
    regression_parser.add_argument('-o', '--output', required=True,
                                  help='Output test file (e.g., tests/regression.spec.ts)')
    regression_parser.add_argument('-g', '--grouping', choices=['endpoint', 'flow'], default='endpoint',
                                  help='Grouping strategy: endpoint (by API endpoint) or flow (by time-based sessions)')
    regression_parser.add_argument('--base-url', help='Base URL for API (optional)')
    regression_parser.add_argument('--assert-status', action='store_true',
                                  help='Assert HTTP status codes (default: enabled)')
    regression_parser.add_argument('--assert-schema', action='store_true',
                                  help='Assert response JSON schema validation')
    regression_parser.add_argument('--assert-fields', action='store_true',
                                  help='Assert critical fields (use with --critical-fields)')
    regression_parser.add_argument('--critical-fields',
                                  help='Comma-separated list of critical field paths (e.g., user.id,order.total)')
    regression_parser.add_argument('--assert-snapshot', action='store_true',
                                  help='Assert full response snapshots')
    regression_parser.add_argument('--verbose', action='store_true', help='Verbose output')

    # --- SUGGEST-TESTS command ---
    suggest_parser = subparsers.add_parser('suggest-tests',
                                           help='Generate AI-powered test suggestions from captured traffic')
    suggest_parser.add_argument('log_file', help='TraceTap JSON log file')
    suggest_parser.add_argument('-o', '--output',
                               help='Output markdown file (default: print to stdout)')
    suggest_parser.add_argument('--no-ai', action='store_true',
                               help='Disable AI enhancement (use statistical analysis only)')
    suggest_parser.add_argument('--verbose', action='store_true', help='Verbose output')

    # --- CREATE-CONTRACT command ---
    create_contract_parser = subparsers.add_parser('create-contract',
                                                   help='Generate OpenAPI contract from captured traffic')
    create_contract_parser.add_argument('log_file', help='TraceTap JSON log file')
    create_contract_parser.add_argument('-o', '--output', required=True,
                                       help='Output contract file (e.g., contract.yaml)')
    create_contract_parser.add_argument('--title', default='API',
                                       help='API title (default: API)')
    create_contract_parser.add_argument('--version', default='1.0.0',
                                       help='API version (default: 1.0.0)')
    create_contract_parser.add_argument('--verbose', action='store_true', help='Verbose output')

    # --- VERIFY-CONTRACT command ---
    verify_contract_parser = subparsers.add_parser('verify-contract',
                                                   help='Verify contract compatibility and detect breaking changes')
    verify_contract_parser.add_argument('baseline', help='Baseline contract file (YAML or JSON)')
    verify_contract_parser.add_argument('current', help='Current contract file (YAML or JSON)')
    verify_contract_parser.add_argument('-o', '--output',
                                       help='Output report file (optional)')
    verify_contract_parser.add_argument('--format', choices=['text', 'json', 'markdown'], default='text',
                                       help='Report format (default: text)')
    verify_contract_parser.add_argument('--fail-on-breaking', action='store_true',
                                       help='Exit with error code if breaking changes detected')
    verify_contract_parser.add_argument('--verbose', action='store_true', help='Verbose output')

    # Parse arguments
    args = parser.parse_args()

    # Dispatch to command handler
    if args.command == 'mock':
        cmd_mock(args)
    elif args.command == 'generate-regression':
        cmd_generate_regression(args)
    elif args.command == 'suggest-tests':
        cmd_suggest_tests(args)
    elif args.command == 'create-contract':
        cmd_create_contract(args)
    elif args.command == 'verify-contract':
        cmd_verify_contract(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
