#!/usr/bin/env python3
"""
TraceTap Collection Updater

Updates an existing Postman collection with data from new captures
while preserving user customizations (test scripts, descriptions, etc.).
"""

import argparse
import sys
import json
from pathlib import Path

from src.tracetap.update import CollectionUpdater, UpdateConfig


def main():
    parser = argparse.ArgumentParser(
        description='Update existing Postman collection with new capture data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic update (auto mode with backup)
  python tracetap-update-collection.py existing.json captures.json

  # Update with custom output
  python tracetap-update-collection.py existing.json captures.json -o updated.json

  # Dry run to preview changes
  python tracetap-update-collection.py existing.json captures.json --dry-run

  # Update with custom match threshold
  python tracetap-update-collection.py existing.json captures.json \\
    --match-threshold 0.85

  # Ignore removed requests
  python tracetap-update-collection.py existing.json captures.json \\
    --removed-requests keep

  # Don't create backup
  python tracetap-update-collection.py existing.json captures.json \\
    --no-backup

  # Generate detailed report
  python tracetap-update-collection.py existing.json captures.json \\
    --report update_report.json
        """
    )

    parser.add_argument('existing',
                        help='Path to existing Postman collection (JSON)')

    parser.add_argument('captures',
                        help='Path to new capture log (JSON array)')

    parser.add_argument('-o', '--output',
                        help='Output file (default: overwrite existing)')

    parser.add_argument('--match-threshold',
                        type=float,
                        default=0.75,
                        help='Minimum confidence for auto-matching (0.0-1.0, default: 0.75)')

    parser.add_argument('--new-requests',
                        choices=['add', 'prompt', 'ignore'],
                        default='add',
                        help='How to handle new requests (default: add)')

    parser.add_argument('--removed-requests',
                        choices=['deprecate', 'archive', 'keep'],
                        default='deprecate',
                        help='How to handle removed requests (default: deprecate)')

    parser.add_argument('--no-backup',
                        action='store_true',
                        help='Don\'t create backup before updating')

    parser.add_argument('--dry-run',
                        action='store_true',
                        help='Show what would change without applying')

    parser.add_argument('--report',
                        help='Save update report to JSON file')

    parser.add_argument('--no-preserve-tests',
                        action='store_true',
                        help='Don\'t preserve test scripts (not recommended)')

    parser.add_argument('--no-preserve-auth',
                        action='store_true',
                        help='Don\'t preserve authentication settings')

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='Verbose output')

    parser.add_argument('-q', '--quiet',
                        action='store_true',
                        help='Minimal output')

    args = parser.parse_args()

    # Validate paths
    if not Path(args.existing).exists():
        print(f"Error: Existing collection not found: {args.existing}", file=sys.stderr)
        sys.exit(1)

    if not Path(args.captures).exists():
        print(f"Error: Captures file not found: {args.captures}", file=sys.stderr)
        sys.exit(1)

    # Create config
    config = UpdateConfig(
        match_threshold=args.match_threshold,
        preserve_tests=not args.no_preserve_tests,
        preserve_auth=not args.no_preserve_auth,
        preserve_descriptions=True,
        preserve_variables=True,
        new_requests_action=args.new_requests,
        removed_requests_action=args.removed_requests,
        backup=not args.no_backup,
        dry_run=args.dry_run
    )

    # Create updater
    updater = CollectionUpdater(config)

    # Print header
    if not args.quiet:
        print("TraceTap Collection Updater")
        print("=" * 50)
        if args.dry_run:
            print("🔍 DRY RUN MODE - No changes will be applied")
            print()

    # Update collection
    result = updater.update_collection(
        existing_path=args.existing,
        captures_path=args.captures,
        output_path=args.output
    )

    # Check for errors
    if not result.success:
        print(f"\n❌ Update failed:", file=sys.stderr)
        for error in result.errors:
            print(f"  {error}", file=sys.stderr)
        sys.exit(1)

    # Print results
    if not args.quiet:
        print_summary(result, args.verbose)

    # Save report
    if args.report:
        with open(args.report, 'w') as f:
            json.dump(result.report, f, indent=2)
        print(f"\n📄 Report saved to: {args.report}")

    # Final message
    if not args.quiet:
        if args.dry_run:
            print("\n✓ Dry run completed - no changes made")
            print(f"  To apply changes, run without --dry-run")
        else:
            output_path = args.output or args.existing
            print(f"\n✓ Collection updated successfully!")
            print(f"  Saved to: {output_path}")
            if result.backup_path:
                print(f"  Backup: {result.backup_path}")


def print_summary(result, verbose=False):
    """Print update summary."""
    report = result.report
    summary = report.get('summary', {})

    print("\n📊 SUMMARY")
    print(f"  Existing requests: {summary.get('existing_requests', 0)}")
    print(f"  Matched requests: {summary.get('matched_requests', 0)} ({summary.get('match_rate', 0):.0%})")
    print(f"  Updated requests: {summary.get('updated_requests', 0)}")
    print(f"  New requests: {summary.get('new_requests', 0)}")
    print(f"  Removed requests: {summary.get('removed_requests', 0)}")

    # Changes summary
    changes = report.get('changes', {})
    if changes.get('total', 0) > 0:
        print(f"\n✏️  CHANGES ({changes['total']} total)")
        by_type = changes.get('by_type', {})
        for change_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {change_type}: {count}")

    # Preserved items
    preserved = report.get('preserved', {})
    if preserved.get('total', 0) > 0:
        print(f"\n✓ PRESERVED ({preserved['total']} items)")
        items = preserved.get('items', [])
        for item in items[:5]:
            print(f"  - {item}")
        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")

    # Warnings
    warnings = report.get('warnings', [])
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)})")
        for warning in warnings[:5]:
            print(f"  - {warning}")
        if len(warnings) > 5:
            print(f"  ... and {len(warnings) - 5} more")

    # Verbose: show match details
    if verbose:
        print("\n📋 MATCH DETAILS")
        match_details = report.get('match_details', [])
        for detail in match_details[:10]:
            status = "✓" if detail['matched'] else "✗"
            confidence = detail.get('confidence', 0)
            print(f"  {status} {detail['name']} ({detail['match_type']}, {confidence:.0%})")
        if len(match_details) > 10:
            print(f"  ... and {len(match_details) - 10} more")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
