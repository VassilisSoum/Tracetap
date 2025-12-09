"""
Main collection updater orchestrator.

Coordinates the update process: matching, merging, and handling new/removed requests.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .matcher import RequestMatcher, MatchResult
from .merger import ElementMerger, MergeResult

# Import common utilities
from ..common import CaptureLoader


@dataclass
class UpdateConfig:
    """Configuration for collection update."""
    match_threshold: float = 0.75
    preserve_tests: bool = True
    preserve_auth: bool = True
    preserve_descriptions: bool = True
    preserve_variables: bool = True
    new_requests_action: str = 'add'  # add, prompt, ignore
    removed_requests_action: str = 'deprecate'  # deprecate, archive, keep
    backup: bool = True
    dry_run: bool = False


@dataclass
class UpdateResult:
    """Result of collection update operation."""
    success: bool
    collection: Dict[str, Any]
    report: Dict[str, Any]
    backup_path: Optional[str] = None
    errors: List[str] = field(default_factory=list)


class CollectionUpdater:
    """Main orchestrator for collection updates."""

    def __init__(self, config: UpdateConfig):
        """
        Initialize updater.

        Args:
            config: Update configuration
        """
        self.config = config
        self.matcher = RequestMatcher(min_confidence=config.match_threshold)
        self.merger = ElementMerger(
            preserve_tests=config.preserve_tests,
            preserve_auth=config.preserve_auth,
            preserve_descriptions=config.preserve_descriptions,
            preserve_variables=config.preserve_variables
        )

    def update_collection(
        self,
        existing_path: str,
        captures_path: str,
        output_path: Optional[str] = None
    ) -> UpdateResult:
        """
        Update existing collection with new captures.

        Args:
            existing_path: Path to existing Postman collection JSON
            captures_path: Path to new captures JSON
            output_path: Output path (default: overwrite existing)

        Returns:
            UpdateResult with updated collection and report
        """
        try:
            # 1. Load data
            existing_collection = self._load_json(existing_path)
            # Load captures using standardized loader
            loader = CaptureLoader(captures_path)
            captures = loader.load()

            # 2. Backup
            backup_path = None
            if self.config.backup and not self.config.dry_run:
                backup_path = self._create_backup(existing_path)

            # 3. Extract requests and variables from collection
            existing_requests = self._extract_requests(existing_collection)
            collection_variables = self._extract_variables(existing_collection)

            # 4. Match requests (create matcher with variables)
            matcher = RequestMatcher(
                min_confidence=self.config.match_threshold,
                collection_variables=collection_variables
            )
            match_results = matcher.match_collections(existing_requests, captures)

            # 5. Merge matched requests
            merge_results = []
            for match in match_results:
                if match.matched and match.capture:
                    merge_result = self.merger.merge_request(
                        existing=match.existing_request,
                        capture=match.capture,
                        confidence=match.confidence
                    )
                    merge_results.append((match, merge_result))

            # 6. Find new requests (in captures but not in collection)
            new_requests = matcher.find_unmatched_captures(captures, match_results)

            # 7. Find removed requests (in collection but not in captures)
            removed_requests = [
                match.existing_request
                for match in match_results
                if not match.matched
            ]

            # 8. Update collection
            updated_collection = self._rebuild_collection(
                existing_collection,
                merge_results,
                new_requests,
                removed_requests
            )

            # 9. Generate report
            report = self._generate_report(
                match_results,
                merge_results,
                new_requests,
                removed_requests
            )

            # 10. Save (unless dry-run)
            if not self.config.dry_run:
                save_path = output_path or existing_path
                self._save_json(updated_collection, save_path)

            return UpdateResult(
                success=True,
                collection=updated_collection,
                report=report,
                backup_path=backup_path
            )

        except Exception as e:
            return UpdateResult(
                success=False,
                collection={},
                report={},
                errors=[str(e)]
            )

    def _load_json(self, path: str) -> Any:
        """Load JSON file."""
        with open(path, 'r') as f:
            return json.load(f)

    def _save_json(self, data: Any, path: str) -> None:
        """Save JSON file."""
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def _create_backup(self, path: str) -> str:
        """Create backup of existing collection."""
        backup_path = f"{path}.backup"
        shutil.copy2(path, backup_path)
        return backup_path

    def _extract_requests(self, collection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all requests from collection (including nested in folders)."""
        requests = []

        def extract_from_items(items: List[Dict[str, Any]]):
            for item in items:
                if 'request' in item:
                    # This is a request
                    requests.append(item)
                elif 'item' in item:
                    # This is a folder, recurse
                    extract_from_items(item['item'])

        items = collection.get('item', [])
        extract_from_items(items)

        return requests

    def _extract_variables(self, collection: Dict[str, Any]) -> Dict[str, str]:
        """Extract collection variables as key-value dictionary."""
        variables = {}

        for var in collection.get('variable', []):
            if isinstance(var, dict):
                key = var.get('key')
                value = var.get('value')
                if key and value:
                    variables[key] = value

        return variables

    def _rebuild_collection(
        self,
        existing_collection: Dict[str, Any],
        merge_results: List[tuple],
        new_requests: List[Dict[str, Any]],
        removed_requests: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Rebuild collection with merged requests."""
        updated_collection = existing_collection.copy()

        # Update matched requests
        def update_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            updated_items = []

            for item in items:
                if 'request' in item:
                    # This is a request - check if it was merged
                    merged_request = self._find_merged_request(item, merge_results)

                    if merged_request:
                        updated_items.append(merged_request)
                    elif self._is_removed(item, removed_requests):
                        # Handle removed request
                        handled_item = self._handle_removed_request(item)
                        if handled_item:
                            updated_items.append(handled_item)
                    else:
                        # Keep unchanged
                        updated_items.append(item)

                elif 'item' in item:
                    # This is a folder - recurse
                    item['item'] = update_items(item['item'])
                    updated_items.append(item)
                else:
                    updated_items.append(item)

            return updated_items

        updated_collection['item'] = update_items(updated_collection['item'])

        # Add new requests
        if new_requests and self.config.new_requests_action == 'add':
            new_folder = self._create_new_requests_folder(new_requests)
            updated_collection['item'].append(new_folder)

        return updated_collection

    def _find_merged_request(
        self,
        request: Dict[str, Any],
        merge_results: List[tuple]
    ) -> Optional[Dict[str, Any]]:
        """Find merged version of a request."""
        for match, merge_result in merge_results:
            if match.existing_request is request:
                return merge_result.request
        return None

    def _is_removed(
        self,
        request: Dict[str, Any],
        removed_requests: List[Dict[str, Any]]
    ) -> bool:
        """Check if request is in removed list."""
        return request in removed_requests

    def _handle_removed_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle removed request based on config."""
        if self.config.removed_requests_action == 'keep':
            # Keep unchanged
            return request

        elif self.config.removed_requests_action == 'deprecate':
            # Mark as deprecated
            deprecated = request.copy()
            deprecated['name'] = f"⚠️ DEPRECATED: {request.get('name', 'Unnamed')}"

            # Add deprecation note to description
            request_data = deprecated.get('request', {})
            current_desc = request_data.get('description', '')
            deprecation_note = f"\n\n⚠️ DEPRECATED: Not found in captures since {datetime.now().strftime('%Y-%m-%d')}\n"
            request_data['description'] = current_desc + deprecation_note
            deprecated['request'] = request_data

            return deprecated

        elif self.config.removed_requests_action == 'archive':
            # Return None - will be moved to archive folder
            return request

        return None

    def _create_new_requests_folder(self, new_requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create folder for new requests."""
        folder_name = f"New Captures - {datetime.now().strftime('%Y-%m-%d')}"

        # Convert captures to Postman requests
        postman_requests = []
        for idx, capture in enumerate(new_requests):
            method = capture.get('method', 'GET')
            url = capture.get('url', '')

            # Generate name from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split('/') if p]
            name = path_parts[-1] if path_parts else parsed.netloc
            name = f"{idx + 1}. {method} {name}"

            # Build request
            postman_request = {
                'name': name,
                'request': {
                    'method': method.upper(),
                    'url': url,
                    'header': []
                }
            }

            # Add headers
            if capture.get('req_headers'):
                for key, value in capture['req_headers'].items():
                    if key.lower() != 'content-length':
                        postman_request['request']['header'].append({
                            'key': key,
                            'value': str(value),
                            'type': 'text'
                        })

            # Add body
            if capture.get('req_body'):
                body_str = capture['req_body']
                try:
                    body_json = json.loads(body_str) if isinstance(body_str, str) else body_str
                    postman_request['request']['body'] = {
                        'mode': 'raw',
                        'raw': json.dumps(body_json, indent=2),
                        'options': {'raw': {'language': 'json'}}
                    }
                except (json.JSONDecodeError, TypeError):
                    postman_request['request']['body'] = {
                        'mode': 'raw',
                        'raw': str(body_str)
                    }

            postman_requests.append(postman_request)

        return {
            'name': folder_name,
            'item': postman_requests,
            'description': f'Requests captured on {datetime.now().strftime("%Y-%m-%d")} that were not found in the existing collection.'
        }

    def _generate_report(
        self,
        match_results: List[MatchResult],
        merge_results: List[tuple],
        new_requests: List[Dict[str, Any]],
        removed_requests: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate update report."""
        total_requests = len(match_results)
        matched = sum(1 for m in match_results if m.matched)
        updated = len(merge_results)

        # Collect changes and preserved items
        all_changes = []
        all_preserved = []
        all_warnings = []

        for match, merge in merge_results:
            if merge.changes:
                all_changes.extend(merge.changes)
            if merge.preserved:
                all_preserved.extend(merge.preserved)
            if merge.warnings:
                all_warnings.extend(merge.warnings)

        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'existing_requests': total_requests,
                'matched_requests': matched,
                'match_rate': matched / total_requests if total_requests > 0 else 0,
                'updated_requests': updated,
                'new_requests': len(new_requests),
                'removed_requests': len(removed_requests)
            },
            'changes': {
                'total': len(all_changes),
                'by_type': self._count_changes(all_changes)
            },
            'preserved': {
                'total': len(all_preserved),
                'items': list(set(all_preserved))
            },
            'warnings': all_warnings,
            'match_details': [
                {
                    'name': m.existing_request.get('name', 'Unnamed') if m.existing_request else 'Unknown',
                    'matched': m.matched,
                    'confidence': m.confidence,
                    'match_type': m.match_type,
                    'reason': m.reason
                }
                for m in match_results
            ]
        }

        return report

    def _count_changes(self, changes: List[str]) -> Dict[str, int]:
        """Count changes by type."""
        counts = {}
        for change in changes:
            counts[change] = counts.get(change, 0) + 1
        return counts
