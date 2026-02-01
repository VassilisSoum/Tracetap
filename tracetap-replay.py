#!/usr/bin/env python3
"""
TraceTap Replay & Mock CLI

Command-line interface for TraceTap traffic replay and mock server functionality.

Commands:
    replay              - Replay captured HTTP traffic
    mock                - Start mock HTTP server
    variables           - Extract variables from captures
    scenario            - Generate YAML replay scenario
    validate            - Validate captured traffic
    generate-regression - Generate Playwright regression tests
    suggest-tests       - Generate AI-powered test suggestions
    create-contract     - Generate OpenAPI contract from traffic
    verify-contract     - Verify contract compatibility and detect breaking changes

Examples:
    # Replay traffic to new endpoint
    python3 tracetap-replay.py replay session.json --target http://localhost:8080

    # Start mock server
    python3 tracetap-replay.py mock session.json --port 8080

    # Extract variables with AI
    python3 tracetap-replay.py variables session.json --ai

    # Generate YAML scenario with AI
    python3 tracetap-replay.py scenario session.json --output scenario.yaml --ai

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

from tracetap.replay import TrafficReplayer, VariableExtractor, ReplayConfig
from tracetap.replay.replay_config import AIScenarioGenerator
from tracetap.mock import MockServer, MockConfig, create_mock_server
from tracetap.common import get_api_key_from_env, CaptureLoader
from tracetap.generators.regression_generator import generate_regression_tests


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

    # Validate log file is readable JSON
    try:
        with open(args.log_file, 'r') as f:
            json.load(f)
    except json.JSONDecodeError as e:
        print(f"\n❌ Error: Invalid JSON in log file")
        print(f"   File: {args.log_file}")
        print(f"   Error at line {e.lineno}, column {e.colno}: {e.msg}")
        print(f"   Context: {e.doc[max(0, e.pos-20):e.pos+20]}")
        print(f"\nNext steps:")
        print(f"  • Fix JSON syntax (check for missing quotes, commas, etc)")
        print(f"  • Use a JSON validator: python3 -m json.tool {args.log_file}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: Cannot read log file")
        print(f"   File: {args.log_file}")
        print(f"   Reason: {e}")
        print(f"\nNext steps:")
        print(f"  • Ensure file is readable: chmod 644 {args.log_file}")
        print(f"  • Check disk space and permissions")
        sys.exit(1)

    # Load replayer
    try:
        replayer = TrafficReplayer(
            log_file=args.log_file,
            timeout=args.timeout,
            verify_ssl=not args.no_verify_ssl,
            max_retries=args.retries
        )
    except FileNotFoundError:
        print(f"\n❌ Error: Trace file not found")
        print(f"   File: {args.log_file}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Error: Invalid log file format")
        print(f"   Reason: {e}")
        print(f"\nExpected format: JSON with HTTP request/response captures")
        print(f"Example structure:")
        print(f"  [")
        print(f"    {{'method': 'GET', 'url': 'https://api.example.com/users', ...}},")
        print(f"    {{'method': 'POST', 'url': 'https://api.example.com/users', ...}}")
        print(f"  ]")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Failed to load captures")
        print(f"   File: {args.log_file}")
        print(f"   Error: {e}")
        print(f"\nNext steps:")
        print(f"  • Validate JSON: python3 -m json.tool {args.log_file}")
        print(f"  • Check file size: ls -lh {args.log_file}")
        print(f"  • Review examples: python3 tracetap-replay.py replay --help")
        sys.exit(1)

    # Validate target URL if provided
    if args.target:
        if not (args.target.startswith('http://') or args.target.startswith('https://')):
            print(f"\n❌ Error: Invalid target URL")
            print(f"   URL: {args.target}")
            print(f"   Must start with http:// or https://")
            print(f"\nExample:")
            print(f"  python3 tracetap-replay.py replay session.json --target http://localhost:8080")
            sys.exit(1)

    # Validate worker count
    if args.workers < 1:
        print(f"\n❌ Error: Invalid worker count")
        print(f"   Value: {args.workers}")
        print(f"   Must be at least 1")
        sys.exit(1)

    # Validate timeout
    if args.timeout < 1:
        print(f"\n❌ Error: Invalid timeout")
        print(f"   Value: {args.timeout} seconds")
        print(f"   Must be at least 1 second")
        sys.exit(1)

    # Prepare variables with validation
    variables = {}
    if args.variables:
        for var_pair in args.variables:
            if '=' not in var_pair:
                print(f"\n❌ Error: Invalid variable format")
                print(f"   Variable: {var_pair}")
                print(f"   Expected: KEY=VALUE")
                print(f"\nExample:")
                print(f"  python3 tracetap-replay.py replay session.json --variables userId=123 token=abc")
                sys.exit(1)
            key, value = var_pair.split('=', 1)
            if not key.strip():
                print(f"\n❌ Error: Variable key cannot be empty")
                print(f"   Variable: {var_pair}")
                print(f"   Expected: KEY=VALUE (KEY must not be empty)")
                sys.exit(1)
            variables[key] = value

    # Create filter function if provided
    filter_fn = None
    if args.filter_method:
        valid_methods = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'}
        methods = [m.upper() for m in args.filter_method]
        invalid = [m for m in methods if m not in valid_methods]
        if invalid:
            print(f"\n❌ Error: Invalid HTTP methods")
            print(f"   Invalid: {', '.join(invalid)}")
            print(f"   Valid methods: {', '.join(sorted(valid_methods))}")
            sys.exit(1)
        filter_fn = lambda c: c.get('method', '').upper() in methods
        print(f"   Filter methods: {', '.join(methods)}")

    # Run replay
    print()
    try:
        result = replayer.replay(
            target_base_url=args.target,
            variables=variables if variables else None,
            max_workers=args.workers,
            filter_fn=filter_fn,
            verbose=args.verbose
        )
    except ConnectionError as e:
        print(f"\n❌ Error: Cannot connect to target server")
        print(f"   Target: {args.target}")
        print(f"   Reason: {e}")
        print(f"\nNext steps:")
        print(f"  • Verify target server is running")
        print(f"  • Test connectivity: curl -v {args.target}")
        print(f"  • Check firewall/network settings")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during replay")
        print(f"   Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # Save results if output specified
    if args.output:
        try:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            replayer.save_result(result, args.output)
            print(f"\n✅ Results saved to {args.output}")
        except PermissionError:
            print(f"\n❌ Error: Permission denied writing to output file")
            print(f"   File: {args.output}")
            print(f"\nNext steps:")
            print(f"  • Check directory permissions: ls -ld {Path(args.output).parent}")
            print(f"  • Try different output path")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Error: Failed to save results")
            print(f"   File: {args.output}")
            print(f"   Error: {e}")
            sys.exit(1)

    # Report results
    print()
    print(f"📊 Results:")
    print(f"   Total replayed: {result.successful_replays + result.failed_replays}")
    print(f"   Successful: {result.successful_replays}")
    print(f"   Failed: {result.failed_replays}")

    # Exit with error code if failures
    if result.failed_replays > 0:
        print(f"\n❌ Some replays failed. Review verbose output for details.")
        sys.exit(1)
    else:
        print(f"\n✅ All replays successful!")
        sys.exit(0)


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

    # Validate chaos rate
    if not (0 <= args.chaos_rate <= 1):
        print(f"\n❌ Error: Invalid chaos failure rate")
        print(f"   Rate: {args.chaos_rate}")
        print(f"   Must be between 0 and 1 (0.1 = 10%)")
        print(f"\nExample:")
        print(f"  python3 tracetap-replay.py mock session.json --chaos --chaos-rate 0.2")
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


def cmd_variables(args):
    """
    Extract variables from captured traffic.

    Args:
        args: Parsed command-line arguments
    """
    print(f"🔍 TraceTap Variable Extraction")
    print(f"   Log file: {args.log_file}")

    # Validate log file exists
    if not Path(args.log_file).exists():
        print(f"\n❌ Error: Log file not found")
        print(f"   Path: {args.log_file}")
        print(f"   Expected file at: {Path(args.log_file).absolute()}")
        print(f"\nNext steps:")
        print(f"  • Check the file path is correct")
        print(f"  • Run: ls -la {args.log_file}")
        sys.exit(1)

    # Load captures using standardized loader
    try:
        loader = CaptureLoader(args.log_file)
        captures = loader.load()
    except json.JSONDecodeError as e:
        print(f"\n❌ Error: Invalid JSON in log file")
        print(f"   File: {args.log_file}")
        print(f"   Error at line {e.lineno}, column {e.colno}: {e.msg}")
        print(f"\nNext steps:")
        print(f"  • Validate JSON: python3 -m json.tool {args.log_file}")
        print(f"  • Fix syntax errors and try again")
        sys.exit(1)
    except FileNotFoundError:
        print(f"\n❌ Error: Log file not found")
        print(f"   File: {args.log_file}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Error: Invalid log file format")
        print(f"   Reason: {e}")
        print(f"\nExpected: JSON array of HTTP captures")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Failed to load captures")
        print(f"   Error: {e}")
        sys.exit(1)

    if not captures:
        print(f"\n⚠️  Warning: No captures found in log file")
        print(f"   File: {args.log_file}")
        print(f"   The file appears to be empty or contains no valid captures")
        print(f"\nNext steps:")
        print(f"  • Check file is not empty: wc -l {args.log_file}")
        print(f"  • Validate JSON structure: python3 -m json.tool {args.log_file}")
        print(f"  • Generate captures first, then extract variables")
        sys.exit(1)

    print(f"   Captures: {len(captures)}")
    print()

    # Create extractor (SECURITY: API key from environment only)
    api_key = get_api_key_from_env()
    if args.ai and not api_key:
        print("⚠️  Warning: --ai flag set but ANTHROPIC_API_KEY not configured")
        print("   Set it with: export ANTHROPIC_API_KEY=your_key")
        print("   Falling back to pattern-based extraction")
        print()

    extractor = VariableExtractor(
        captures=captures,
        api_key=api_key,
        use_ai=args.ai
    )

    # Extract variables
    try:
        variables = extractor.extract_variables(verbose=True)
    except Exception as e:
        print(f"\n❌ Error during variable extraction")
        print(f"   Error: {e}")
        sys.exit(1)

    if not variables:
        print(f"\n⚠️  No variables found in captures")
        print(f"   Checked {len(captures)} captures")
        print(f"\nPossible reasons:")
        print(f"  • Captures only contain static data")
        print(f"  • Variable patterns not recognized")
        print(f"  • All values are constant across requests")
        print(f"\nNext steps:")
        print(f"  • Try with --ai flag for smarter extraction")
        print(f"  • Review captures manually for variable patterns")
        sys.exit(0)

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
        try:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_data = [var.to_dict() for var in variables]
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"✅ Saved {len(variables)} variables to {args.output}")
        except PermissionError:
            print(f"\n❌ Error: Permission denied writing to output file")
            print(f"   File: {args.output}")
            print(f"\nNext steps:")
            print(f"  • Check directory permissions: ls -ld {Path(args.output).parent}")
            print(f"  • Try different output path")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Error: Failed to save variables")
            print(f"   File: {args.output}")
            print(f"   Error: {e}")
            sys.exit(1)


def cmd_scenario(args):
    """
    Generate YAML replay scenario from captures.

    Args:
        args: Parsed command-line arguments
    """
    print(f"📝 TraceTap Scenario Generation")
    print(f"   Log file: {args.log_file}")

    # Validate log file exists
    if not Path(args.log_file).exists():
        print(f"\n❌ Error: Log file not found")
        print(f"   Path: {args.log_file}")
        print(f"   Expected file at: {Path(args.log_file).absolute()}")
        print(f"\nNext steps:")
        print(f"  • Check the file path is correct")
        print(f"  • Run: ls -la {args.log_file}")
        sys.exit(1)

    # Load captures using standardized loader
    try:
        loader = CaptureLoader(args.log_file)
        captures = loader.load()
    except json.JSONDecodeError as e:
        print(f"\n❌ Error: Invalid JSON in log file")
        print(f"   File: {args.log_file}")
        print(f"   Error at line {e.lineno}, column {e.colno}: {e.msg}")
        print(f"\nNext steps:")
        print(f"  • Validate JSON: python3 -m json.tool {args.log_file}")
        print(f"  • Fix syntax errors")
        sys.exit(1)
    except FileNotFoundError:
        print(f"\n❌ Error: Log file not found")
        print(f"   File: {args.log_file}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Failed to load captures")
        print(f"   Error: {e}")
        sys.exit(1)

    if not captures:
        print(f"\n❌ Error: No captures found in log file")
        print(f"   File: {args.log_file}")
        print(f"   Cannot generate scenario from empty data")
        print(f"\nNext steps:")
        print(f"  • Check if file is not empty: wc -l {args.log_file}")
        print(f"  • Validate JSON: python3 -m json.tool {args.log_file}")
        print(f"  • Generate captures first")
        sys.exit(1)

    print(f"   Captures: {len(captures)}")

    if args.ai:
        # Use AI to generate scenario (SECURITY: API key from environment only)
        api_key = get_api_key_from_env()

        if not api_key:
            print("\n❌ Error: AI generation requires ANTHROPIC_API_KEY")
            print("   Set it with: export ANTHROPIC_API_KEY=your_key")
            print("\nObtain API key:")
            print("  • Visit: https://console.anthropic.com/")
            print("  • Create/manage API keys in account settings")
            print("  • Copy key and set environment variable")
            sys.exit(1)

        print("   Mode: AI-powered (using Claude)")
        print()

        try:
            generator = AIScenarioGenerator(api_key=api_key)

            scenario = generator.generate_scenario(
                captures=captures,
                intent=args.intent or "",
                scenario_name=args.name
            )

            if not scenario:
                print("❌ Failed to generate scenario with AI")
                print("   Claude returned empty scenario")
                sys.exit(1)

            print(f"✅ Generated scenario: {scenario.name}")
            print(f"   Steps: {len(scenario.steps)}")
        except ValueError as e:
            print(f"\n❌ Error: Invalid API key")
            print(f"   Reason: {e}")
            print(f"\nNext steps:")
            print(f"  • Check API key is valid: export ANTHROPIC_API_KEY=sk-...")
            print(f"  • Verify account has API access")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Error generating scenario with AI")
            print(f"   Error: {e}")
            print(f"\nNext steps:")
            print(f"  • Check internet connection")
            print(f"  • Verify API key is valid and has quota")
            print(f"  • Try again with --intent for better results")
            sys.exit(1)

    else:
        # Manual scenario creation (basic)
        print("   Mode: Manual (requires --ai for intelligent generation)")
        print()
        print("✨ Use --ai flag for intelligent scenario generation:")
        print(f"   python3 tracetap-replay.py scenario {args.log_file} --ai")
        print(f"   python3 tracetap-replay.py scenario {args.log_file} --ai --intent 'User registration flow'")
        sys.exit(1)

    # Save scenario
    output_path = args.output or 'scenario.yaml'
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        config = ReplayConfig()
        config.scenario = scenario
        config.save(output_path)
        print(f"\n✅ Saved scenario to {output_path}")
    except PermissionError:
        print(f"\n❌ Error: Permission denied writing to output file")
        print(f"   File: {output_path}")
        print(f"\nNext steps:")
        print(f"  • Check directory permissions: ls -ld {output_file.parent}")
        print(f"  • Try different output path")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: Failed to save scenario")
        print(f"   File: {output_path}")
        print(f"   Error: {e}")
        sys.exit(1)


def cmd_validate(args):
    """
    Validate captured traffic and report issues.

    Args:
        args: Parsed command-line arguments
    """
    print(f"✓ TraceTap Traffic Validation")
    print(f"   Log file: {args.log_file}")

    # Validate log file exists
    if not Path(args.log_file).exists():
        print(f"\n❌ Error: Log file not found")
        print(f"   Path: {args.log_file}")
        print(f"   Expected file at: {Path(args.log_file).absolute()}")
        print(f"\nNext steps:")
        print(f"  • Check the file path is correct")
        print(f"  • Run: ls -la {args.log_file}")
        sys.exit(1)

    # Load captures using standardized loader
    try:
        loader = CaptureLoader(args.log_file)
        captures = loader.load()
    except json.JSONDecodeError as e:
        print(f"\n❌ Error: Invalid JSON in log file")
        print(f"   File: {args.log_file}")
        print(f"   Error at line {e.lineno}, column {e.colno}: {e.msg}")
        print(f"\nNext steps:")
        print(f"  • Validate JSON: python3 -m json.tool {args.log_file}")
        print(f"  • Fix syntax errors (missing quotes, commas, etc)")
        sys.exit(1)
    except FileNotFoundError:
        print(f"\n❌ Error: Log file not found")
        print(f"   File: {args.log_file}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Failed to load captures")
        print(f"   Error: {e}")
        sys.exit(1)

    if not captures:
        print(f"\n❌ Error: No captures found")
        print(f"   File: {args.log_file} is empty")
        print(f"\nNext steps:")
        print(f"  • Check file size: ls -lh {args.log_file}")
        print(f"  • Generate captures using TraceTap first")
        sys.exit(1)

    print(f"   Total captures: {len(captures)}")
    print()

    # Validation checks
    errors = []
    warnings = []

    # Check for required fields
    for i, capture in enumerate(captures):
        if 'method' not in capture:
            errors.append(f"Capture {i}: Missing 'method' field (required: GET, POST, etc)")
        if 'url' not in capture:
            errors.append(f"Capture {i}: Missing 'url' field (required: https://...)")
        if 'status' not in capture:
            warnings.append(f"Capture {i}: Missing 'status' field (expected: 200, 404, etc)")

    # Check for error responses
    error_count = sum(1 for c in captures if c.get('status', 0) >= 400)
    if error_count > 0:
        error_pct = (error_count / len(captures)) * 100
        warnings.append(f"{error_count} captures ({error_pct:.1f}%) have error status codes (4xx/5xx)")

    # Check for missing response bodies
    missing_bodies = sum(1 for c in captures if not c.get('resp_body'))
    if missing_bodies > 0:
        body_pct = (missing_bodies / len(captures)) * 100
        warnings.append(f"{missing_bodies} captures ({body_pct:.1f}%) have empty response bodies")

    # Check for duplicate URLs
    urls = [c.get('url') for c in captures]
    unique_urls = len(set(urls))
    if unique_urls < len(urls):
        dup_count = len(urls) - unique_urls
        warnings.append(f"{dup_count} duplicate URL(s) detected")

    # Report results
    if errors:
        print("❌ ERRORS FOUND - Cannot use for replay:")
        for error in errors:
            print(f"   • {error}")
        print()

    if warnings:
        print("⚠️  WARNINGS - May impact replay:")
        for warning in warnings:
            print(f"   • {warning}")
        print()

    if not errors and not warnings:
        print("✅ All validations passed!")
        print(f"\n   Status:")
        print(f"   • All required fields present")
        print(f"   • No error responses detected")
        print(f"   • All responses have bodies")
        print(f"\n   Ready to use for:")
        print(f"   • Replay: python3 tracetap-replay.py replay {args.log_file} --target http://localhost:8080")
        print(f"   • Mock server: python3 tracetap-replay.py mock {args.log_file} --port 8080")
    else:
        print(f"📊 Summary:")
        print(f"   Errors: {len(errors)}")
        print(f"   Warnings: {len(warnings)}")
        print()
        if errors:
            print("   Fix errors before using for replay/mock")

    # Exit with error if there are errors
    if errors:
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
  # Replay traffic to localhost
  %(prog)s replay session.json --target http://localhost:8080

  # Start mock server with fuzzy matching
  %(prog)s mock session.json --port 8080 --strategy fuzzy

  # Extract variables with AI
  %(prog)s variables session.json --ai --output variables.json

  # Generate test scenario with AI
  %(prog)s scenario session.json --ai --intent "User registration flow" --output test.yaml

  # Generate Playwright regression tests
  %(prog)s generate-regression session.json -o tests/regression.spec.ts --assert-schema

  # Generate AI test suggestions
  %(prog)s suggest-tests session.json -o suggestions.md

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
