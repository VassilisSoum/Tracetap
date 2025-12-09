#!/usr/bin/env python3
"""
TraceTap Playwright Test Generator

Convert Postman Collection v2.1 JSON files to Playwright API tests.
"""

import sys
import argparse
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from tracetap.playwright import PlaywrightGenerator
from tracetap.common import get_api_key_from_env


def main():
    parser = argparse.ArgumentParser(
        description='Generate Playwright API tests from Postman collections',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with AI conversion
  python tracetap-playwright.py collection.json --output tests/

  # Without AI (pattern-based only)
  python tracetap-playwright.py collection.json --output tests/ --no-ai

  # Generate config template
  python tracetap-playwright.py --config-template > playwright.config.ts

Environment Variables:
  ANTHROPIC_API_KEY - API key for Claude AI (required for --use-ai)
  BASE_URL - Default base URL for API endpoints
        """
    )

    # Positional arguments
    parser.add_argument(
        'collection',
        nargs='?',
        help='Path to Postman collection JSON file'
    )

    # Output options
    parser.add_argument(
        '--output', '-o',
        required='--config-template' not in sys.argv,
        help='Output directory for generated test files'
    )

    # AI options
    parser.add_argument(
        '--use-ai',
        action='store_true',
        default=True,
        help='Use AI for intelligent test script conversion (default: enabled)'
    )

    parser.add_argument(
        '--no-ai',
        action='store_true',
        help='Disable AI conversion, use pattern matching only'
    )

    # Code generation options
    parser.add_argument(
        '--no-comments',
        action='store_true',
        help='Omit comments in generated code'
    )

    # Utility options
    parser.add_argument(
        '--config-template',
        action='store_true',
        help='Print Playwright config template and exit'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Handle config template
    if args.config_template:
        config_template = """import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',

  // API testing doesn't need browser
  use: {
    baseURL: process.env.BASE_URL || 'https://api.example.com',
    extraHTTPHeaders: {
      // Add any default headers here
    },
  },

  // Timeouts
  timeout: 30000,
  expect: {
    timeout: 5000,
  },

  // Reporters
  reporter: [
    ['html'],
    ['list'],
  ],

  // Run tests in parallel
  workers: process.env.CI ? 1 : undefined,
});
"""
        print(config_template)
        return 0

    # Validate required arguments
    if not args.collection:
        parser.error("collection path is required")

    # Check collection file exists
    if not Path(args.collection).exists():
        print(f"Error: Collection file not found: {args.collection}", file=sys.stderr)
        return 1

    # Determine if AI should be used
    use_ai = args.use_ai and not args.no_ai

    # SECURITY: Get API key from environment only (never accept via CLI)
    api_key = get_api_key_from_env()

    if use_ai and not api_key:
        print("Warning: AI conversion enabled but ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        print("Set it with: export ANTHROPIC_API_KEY=your_key", file=sys.stderr)
        print("Falling back to pattern-based conversion...\n", file=sys.stderr)
        use_ai = False

    try:
        # Print header
        print("=" * 50)
        print("TraceTap Playwright Test Generator")
        print("=" * 50)
        print(f"\nInput: {args.collection}")
        print(f"Output: {args.output}")
        print(f"AI Conversion: {'Enabled' if use_ai else 'Disabled'}")
        print()

        # Create generator (SECURITY: API key from environment only)
        generator = PlaywrightGenerator(
            collection_path=args.collection,
            output_dir=args.output,
            use_ai=use_ai,
            include_comments=not args.no_comments
        )

        # Generate tests
        result = generator.generate()

        if result.success:
            print("\n" + "=" * 50)
            print("✅ Generation Complete!")
            print("=" * 50)
            print(f"\nGenerated {result.tests_generated} tests")
            print(f"Generated {result.fixtures_generated} fixtures")
            print(f"Output file: {result.output_file}")

            print("\n📖 Next Steps:")
            print("1. Install Playwright: npm install -D @playwright/test")
            print("2. Review generated tests and adjust as needed")
            print("3. Set environment variables (BASE_URL, AUTH_TOKEN, etc.)")
            print("4. Run tests: npx playwright test")

            if result.warnings:
                print("\n⚠️  Warnings:")
                for warning in result.warnings:
                    print(f"  - {warning}")

            return 0
        else:
            print("\n❌ Generation Failed")
            if result.errors:
                print("\nErrors:")
                for error in result.errors:
                    print(f"  - {error}")
            return 1

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
