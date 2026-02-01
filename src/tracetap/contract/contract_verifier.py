"""
Contract Verifier - Detect Breaking API Changes

Compares two OpenAPI contracts to detect breaking and non-breaking changes.
Generates diff reports with severity levels for CI/CD integration.
"""

import json
import yaml
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ..common.progress import ProgressBar, StatusLine


class Severity(Enum):
    """Change severity levels"""
    BREAKING = "BREAKING"
    WARNING = "WARNING"
    INFO = "INFO"


class Change:
    """Represents a contract change"""

    def __init__(
        self,
        severity: Severity,
        category: str,
        path: str,
        message: str,
        old_value: Any = None,
        new_value: Any = None
    ):
        self.severity = severity
        self.category = category
        self.path = path
        self.message = message
        self.old_value = old_value
        self.new_value = new_value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'severity': self.severity.value,
            'category': self.category,
            'path': self.path,
            'message': self.message
        }
        if self.old_value is not None:
            result['old_value'] = self.old_value
        if self.new_value is not None:
            result['new_value'] = self.new_value
        return result

    def __repr__(self) -> str:
        return f"[{self.severity.value}] {self.path}: {self.message}"


class ContractVerifier:
    """
    Verifies OpenAPI contract compatibility

    Detects:
    - Breaking changes: Removed endpoints, changed types, removed required fields
    - Warnings: Changed optional fields, new required fields
    - Info: New endpoints, new optional fields
    """

    def __init__(self):
        self.changes: List[Change] = []

    def verify(
        self,
        baseline_contract: Dict[str, Any],
        current_contract: Dict[str, Any],
        verbose: bool = False
    ) -> List[Change]:
        """
        Verify contract compatibility

        Args:
            baseline_contract: Original/baseline OpenAPI contract
            current_contract: New/current OpenAPI contract
            verbose: Show progress indicators

        Returns:
            List of detected changes
        """
        self.changes = []
        status = StatusLine(verbose)

        # Verify paths (endpoints)
        baseline_paths = baseline_contract.get('paths', {})
        current_paths = current_contract.get('paths', {})

        status.start(f"Comparing {len(baseline_paths)} endpoints...")
        progress = ProgressBar(len(baseline_paths), label="Endpoints", width=20)

        self._verify_paths(baseline_paths, current_paths)

        progress.finish()
        status.progress(f"Detected {len(self.changes)} changes so far")

        # Verify components/schemas
        baseline_schemas = baseline_contract.get('components', {}).get('schemas', {})
        current_schemas = current_contract.get('components', {}).get('schemas', {})

        if baseline_schemas or current_schemas:
            status.start(f"Comparing schemas...")
            self._verify_schemas(baseline_schemas, current_schemas)
            status.progress(f"Total changes: {len(self.changes)}")

        return self.changes

    def verify_files(
        self,
        baseline_file: str,
        current_file: str,
        verbose: bool = False
    ) -> List[Change]:
        """
        Verify contracts from YAML/JSON files

        Args:
            baseline_file: Path to baseline contract
            current_file: Path to current contract
            verbose: Show progress indicators

        Returns:
            List of detected changes
        """
        status = StatusLine(verbose)

        status.start(f"Loading baseline contract...")
        baseline = self._load_contract(baseline_file)

        status.start(f"Loading current contract...")
        current = self._load_contract(current_file)

        return self.verify(baseline, current, verbose=verbose)

    def has_breaking_changes(self) -> bool:
        """Check if there are any breaking changes"""
        return any(c.severity == Severity.BREAKING for c in self.changes)

    def get_report(self, format: str = 'text') -> str:
        """
        Generate report of changes

        Args:
            format: 'text', 'json', or 'markdown'

        Returns:
            Formatted report string
        """
        if format == 'json':
            return json.dumps([c.to_dict() for c in self.changes], indent=2)
        elif format == 'markdown':
            return self._format_markdown()
        else:
            return self._format_text()

    def _verify_paths(
        self,
        baseline_paths: Dict[str, Any],
        current_paths: Dict[str, Any]
    ):
        """Verify API paths/endpoints"""
        baseline_keys = set(baseline_paths.keys())
        current_keys = set(current_paths.keys())

        # Removed paths (BREAKING)
        for path in baseline_keys - current_keys:
            self.changes.append(Change(
                severity=Severity.BREAKING,
                category='endpoint',
                path=path,
                message=f'Endpoint removed: {path}',
                old_value=path
            ))

        # New paths (INFO)
        for path in current_keys - baseline_keys:
            self.changes.append(Change(
                severity=Severity.INFO,
                category='endpoint',
                path=path,
                message=f'New endpoint added: {path}',
                new_value=path
            ))

        # Compare existing paths
        for path in baseline_keys & current_keys:
            self._verify_path_item(
                path,
                baseline_paths[path],
                current_paths[path]
            )

    def _verify_path_item(
        self,
        path: str,
        baseline_item: Dict[str, Any],
        current_item: Dict[str, Any]
    ):
        """Verify a single path item (all operations on that path)"""
        # HTTP methods
        methods = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}

        baseline_methods = {m for m in methods if m in baseline_item}
        current_methods = {m for m in methods if m in current_item}

        # Removed operations (BREAKING)
        for method in baseline_methods - current_methods:
            self.changes.append(Change(
                severity=Severity.BREAKING,
                category='operation',
                path=f'{method.upper()} {path}',
                message=f'Operation removed: {method.upper()} {path}',
                old_value=method
            ))

        # New operations (INFO)
        for method in current_methods - baseline_methods:
            self.changes.append(Change(
                severity=Severity.INFO,
                category='operation',
                path=f'{method.upper()} {path}',
                message=f'New operation added: {method.upper()} {path}',
                new_value=method
            ))

        # Compare existing operations
        for method in baseline_methods & current_methods:
            self._verify_operation(
                f'{method.upper()} {path}',
                baseline_item[method],
                current_item[method]
            )

    def _verify_operation(
        self,
        operation_path: str,
        baseline_op: Dict[str, Any],
        current_op: Dict[str, Any]
    ):
        """Verify a single operation"""
        # Verify parameters
        baseline_params = baseline_op.get('parameters', [])
        current_params = current_op.get('parameters', [])
        self._verify_parameters(operation_path, baseline_params, current_params)

        # Verify request body
        baseline_body = baseline_op.get('requestBody')
        current_body = current_op.get('requestBody')
        if baseline_body or current_body:
            self._verify_request_body(operation_path, baseline_body, current_body)

        # Verify responses
        baseline_responses = baseline_op.get('responses', {})
        current_responses = current_op.get('responses', {})
        self._verify_responses(operation_path, baseline_responses, current_responses)

    def _verify_parameters(
        self,
        operation_path: str,
        baseline_params: List[Dict],
        current_params: List[Dict]
    ):
        """Verify operation parameters"""
        # Create lookup by (name, in)
        def param_key(param):
            return (param.get('name'), param.get('in'))

        baseline_map = {param_key(p): p for p in baseline_params}
        current_map = {param_key(p): p for p in current_params}

        baseline_keys = set(baseline_map.keys())
        current_keys = set(current_map.keys())

        # Removed parameters
        for key in baseline_keys - current_keys:
            name, location = key
            param = baseline_map[key]
            required = param.get('required', False)

            severity = Severity.BREAKING if required else Severity.WARNING

            self.changes.append(Change(
                severity=severity,
                category='parameter',
                path=f'{operation_path} / parameter {name}',
                message=f'Parameter removed: {name} ({location})',
                old_value=param
            ))

        # New parameters
        for key in current_keys - baseline_keys:
            name, location = key
            param = current_map[key]
            required = param.get('required', False)

            # New required parameter is BREAKING (clients must provide it)
            severity = Severity.BREAKING if required else Severity.INFO

            self.changes.append(Change(
                severity=severity,
                category='parameter',
                path=f'{operation_path} / parameter {name}',
                message=f'New {"required" if required else "optional"} parameter: {name} ({location})',
                new_value=param
            ))

        # Compare existing parameters
        for key in baseline_keys & current_keys:
            name, location = key
            baseline_param = baseline_map[key]
            current_param = current_map[key]

            # Check if required status changed
            baseline_required = baseline_param.get('required', False)
            current_required = current_param.get('required', False)

            if not baseline_required and current_required:
                # Making parameter required is BREAKING
                self.changes.append(Change(
                    severity=Severity.BREAKING,
                    category='parameter',
                    path=f'{operation_path} / parameter {name}',
                    message=f'Parameter made required: {name} ({location})',
                    old_value={'required': False},
                    new_value={'required': True}
                ))

            # Check type changes
            baseline_type = baseline_param.get('schema', {}).get('type')
            current_type = current_param.get('schema', {}).get('type')

            if baseline_type and current_type and baseline_type != current_type:
                self.changes.append(Change(
                    severity=Severity.BREAKING,
                    category='parameter',
                    path=f'{operation_path} / parameter {name}',
                    message=f'Parameter type changed: {baseline_type} → {current_type}',
                    old_value=baseline_type,
                    new_value=current_type
                ))

    def _verify_request_body(
        self,
        operation_path: str,
        baseline_body: Optional[Dict],
        current_body: Optional[Dict]
    ):
        """Verify request body"""
        if baseline_body and not current_body:
            # Request body removed (BREAKING)
            self.changes.append(Change(
                severity=Severity.BREAKING,
                category='request_body',
                path=f'{operation_path} / requestBody',
                message='Request body removed',
                old_value=baseline_body
            ))
        elif not baseline_body and current_body:
            # Request body added
            required = current_body.get('required', False)
            severity = Severity.BREAKING if required else Severity.INFO

            self.changes.append(Change(
                severity=severity,
                category='request_body',
                path=f'{operation_path} / requestBody',
                message=f'Request body {"required" if required else "added"}',
                new_value=current_body
            ))
        elif baseline_body and current_body:
            # Compare schemas
            baseline_content = baseline_body.get('content', {})
            current_content = current_body.get('content', {})

            for content_type in baseline_content:
                if content_type in current_content:
                    baseline_schema = baseline_content[content_type].get('schema', {})
                    current_schema = current_content[content_type].get('schema', {})

                    self._verify_schema(
                        f'{operation_path} / requestBody',
                        baseline_schema,
                        current_schema
                    )

    def _verify_responses(
        self,
        operation_path: str,
        baseline_responses: Dict[str, Any],
        current_responses: Dict[str, Any]
    ):
        """Verify operation responses"""
        baseline_codes = set(baseline_responses.keys())
        current_codes = set(current_responses.keys())

        # Removed response codes (BREAKING - client expects these)
        for code in baseline_codes - current_codes:
            self.changes.append(Change(
                severity=Severity.BREAKING,
                category='response',
                path=f'{operation_path} / response {code}',
                message=f'Response code removed: {code}',
                old_value=code
            ))

        # New response codes (INFO - might be errors)
        for code in current_codes - baseline_codes:
            self.changes.append(Change(
                severity=Severity.INFO,
                category='response',
                path=f'{operation_path} / response {code}',
                message=f'New response code: {code}',
                new_value=code
            ))

        # Compare existing responses
        for code in baseline_codes & current_codes:
            baseline_response = baseline_responses[code]
            current_response = current_responses[code]

            baseline_content = baseline_response.get('content', {})
            current_content = current_response.get('content', {})

            for content_type in baseline_content:
                if content_type in current_content:
                    baseline_schema = baseline_content[content_type].get('schema', {})
                    current_schema = current_content[content_type].get('schema', {})

                    self._verify_schema(
                        f'{operation_path} / response {code}',
                        baseline_schema,
                        current_schema
                    )

    def _verify_schema(
        self,
        path: str,
        baseline_schema: Dict[str, Any],
        current_schema: Dict[str, Any]
    ):
        """Verify JSON schema compatibility"""
        # Check type change
        baseline_type = baseline_schema.get('type')
        current_type = current_schema.get('type')

        if baseline_type and current_type and baseline_type != current_type:
            self.changes.append(Change(
                severity=Severity.BREAKING,
                category='schema',
                path=f'{path} / type',
                message=f'Type changed: {baseline_type} → {current_type}',
                old_value=baseline_type,
                new_value=current_type
            ))

        # For objects, check properties
        if baseline_type == 'object' and current_type == 'object':
            self._verify_object_properties(path, baseline_schema, current_schema)

        # For arrays, check items
        if baseline_type == 'array' and current_type == 'array':
            baseline_items = baseline_schema.get('items', {})
            current_items = current_schema.get('items', {})
            if baseline_items and current_items:
                self._verify_schema(f'{path} / items', baseline_items, current_items)

    def _verify_object_properties(
        self,
        path: str,
        baseline_schema: Dict[str, Any],
        current_schema: Dict[str, Any]
    ):
        """Verify object properties"""
        baseline_props = baseline_schema.get('properties', {})
        current_props = current_schema.get('properties', {})

        baseline_required = set(baseline_schema.get('required', []))
        current_required = set(current_schema.get('required', []))

        baseline_keys = set(baseline_props.keys())
        current_keys = set(current_props.keys())

        # Removed properties
        for prop in baseline_keys - current_keys:
            was_required = prop in baseline_required
            severity = Severity.BREAKING if was_required else Severity.WARNING

            self.changes.append(Change(
                severity=severity,
                category='property',
                path=f'{path} / {prop}',
                message=f'Property removed: {prop} ({"required" if was_required else "optional"})',
                old_value=baseline_props[prop]
            ))

        # New properties
        for prop in current_keys - baseline_keys:
            is_required = prop in current_required
            severity = Severity.BREAKING if is_required else Severity.INFO

            self.changes.append(Change(
                severity=severity,
                category='property',
                path=f'{path} / {prop}',
                message=f'New {"required" if is_required else "optional"} property: {prop}',
                new_value=current_props[prop]
            ))

        # Compare existing properties
        for prop in baseline_keys & current_keys:
            # Check if required status changed
            was_required = prop in baseline_required
            is_required = prop in current_required

            if not was_required and is_required:
                # Making property required is BREAKING
                self.changes.append(Change(
                    severity=Severity.BREAKING,
                    category='property',
                    path=f'{path} / {prop}',
                    message=f'Property made required: {prop}',
                    old_value={'required': False},
                    new_value={'required': True}
                ))

            # Recursively check property schemas
            self._verify_schema(
                f'{path} / {prop}',
                baseline_props[prop],
                current_props[prop]
            )

    def _verify_schemas(
        self,
        baseline_schemas: Dict[str, Any],
        current_schemas: Dict[str, Any]
    ):
        """Verify component schemas"""
        baseline_keys = set(baseline_schemas.keys())
        current_keys = set(current_schemas.keys())

        # Removed schemas (WARNING - might be breaking if used)
        for schema_name in baseline_keys - current_keys:
            self.changes.append(Change(
                severity=Severity.WARNING,
                category='schema',
                path=f'components/schemas/{schema_name}',
                message=f'Schema removed: {schema_name}',
                old_value=schema_name
            ))

        # New schemas (INFO)
        for schema_name in current_keys - baseline_keys:
            self.changes.append(Change(
                severity=Severity.INFO,
                category='schema',
                path=f'components/schemas/{schema_name}',
                message=f'New schema added: {schema_name}',
                new_value=schema_name
            ))

        # Compare existing schemas
        for schema_name in baseline_keys & current_keys:
            self._verify_schema(
                f'components/schemas/{schema_name}',
                baseline_schemas[schema_name],
                current_schemas[schema_name]
            )

    def _load_contract(self, file_path: str) -> Dict[str, Any]:
        """Load contract from YAML or JSON file"""
        path = Path(file_path)

        with open(path, 'r') as f:
            if path.suffix in ['.yaml', '.yml']:
                return yaml.safe_load(f)
            else:
                return json.load(f)

    def _format_text(self) -> str:
        """Format changes as plain text"""
        if not self.changes:
            return "No changes detected."

        lines = ["Contract Changes:", "=" * 50, ""]

        # Group by severity
        breaking = [c for c in self.changes if c.severity == Severity.BREAKING]
        warnings = [c for c in self.changes if c.severity == Severity.WARNING]
        info = [c for c in self.changes if c.severity == Severity.INFO]

        if breaking:
            lines.append(f"BREAKING CHANGES ({len(breaking)}):")
            lines.append("-" * 50)
            for change in breaking:
                lines.append(f"  • {change.path}")
                lines.append(f"    {change.message}")
            lines.append("")

        if warnings:
            lines.append(f"WARNINGS ({len(warnings)}):")
            lines.append("-" * 50)
            for change in warnings:
                lines.append(f"  • {change.path}")
                lines.append(f"    {change.message}")
            lines.append("")

        if info:
            lines.append(f"INFO ({len(info)}):")
            lines.append("-" * 50)
            for change in info:
                lines.append(f"  • {change.path}")
                lines.append(f"    {change.message}")
            lines.append("")

        lines.append(f"Summary: {len(breaking)} breaking, {len(warnings)} warnings, {len(info)} info")

        return "\n".join(lines)

    def _format_markdown(self) -> str:
        """Format changes as markdown"""
        if not self.changes:
            return "## No Changes Detected\n"

        lines = ["# Contract Changes", ""]

        # Summary
        breaking = [c for c in self.changes if c.severity == Severity.BREAKING]
        warnings = [c for c in self.changes if c.severity == Severity.WARNING]
        info = [c for c in self.changes if c.severity == Severity.INFO]

        lines.append(f"**Summary:** {len(breaking)} breaking, {len(warnings)} warnings, {len(info)} info")
        lines.append("")

        if breaking:
            lines.append("## 🔴 Breaking Changes")
            lines.append("")
            for change in breaking:
                lines.append(f"- **{change.path}**")
                lines.append(f"  - {change.message}")
            lines.append("")

        if warnings:
            lines.append("## ⚠️ Warnings")
            lines.append("")
            for change in warnings:
                lines.append(f"- **{change.path}**")
                lines.append(f"  - {change.message}")
            lines.append("")

        if info:
            lines.append("## ℹ️ Info")
            lines.append("")
            for change in info:
                lines.append(f"- **{change.path}**")
                lines.append(f"  - {change.message}")
            lines.append("")

        return "\n".join(lines)


def verify_contracts(
    baseline_file: str,
    current_file: str,
    output_file: Optional[str] = None,
    format: str = 'text',
    verbose: bool = True
) -> Tuple[bool, List[Change]]:
    """
    Convenience function to verify contracts

    Args:
        baseline_file: Path to baseline contract
        current_file: Path to current contract
        output_file: Optional path to save report
        format: Report format ('text', 'json', 'markdown')
        verbose: Print status messages

    Returns:
        Tuple of (is_compatible, changes)
    """
    status = StatusLine(verbose)

    status.start("Verifying contracts...")
    verifier = ContractVerifier()
    changes = verifier.verify_files(baseline_file, current_file, verbose=verbose)

    is_compatible = not verifier.has_breaking_changes()

    if verbose:
        print()
        if is_compatible:
            status.success("Contracts are compatible - no breaking changes")
        else:
            status.error("Breaking changes detected!")

        print(f"\nChanges detected:")
        print(f"  • {len(changes)} total changes")
        print(f"  • {sum(1 for c in changes if c.severity == Severity.BREAKING)} breaking")
        print(f"  • {sum(1 for c in changes if c.severity == Severity.WARNING)} warnings")
        print(f"  • {sum(1 for c in changes if c.severity == Severity.INFO)} info")

    # Generate report
    report = verifier.get_report(format=format)

    if output_file:
        Path(output_file).write_text(report)
        if verbose:
            status.progress(f"Report saved to {output_file}")

    if verbose and not is_compatible:
        print("\n" + report)

    return is_compatible, changes
