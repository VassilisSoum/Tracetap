"""
Tests for Contract Verifier

Tests OpenAPI contract compatibility verification and breaking change detection.
"""

import json
import pytest
import yaml
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from tracetap.contract.contract_verifier import (
    ContractVerifier,
    Change,
    Severity,
    verify_contracts
)


class TestChange:
    """Test Change class"""

    def test_change_creation(self):
        change = Change(
            severity=Severity.BREAKING,
            category='endpoint',
            path='/users',
            message='Endpoint removed',
            old_value='/users'
        )

        assert change.severity == Severity.BREAKING
        assert change.category == 'endpoint'
        assert change.path == '/users'
        assert change.message == 'Endpoint removed'
        assert change.old_value == '/users'

    def test_change_to_dict(self):
        change = Change(
            severity=Severity.WARNING,
            category='parameter',
            path='GET /users / param limit',
            message='Parameter removed',
            old_value={'name': 'limit', 'type': 'integer'}
        )

        result = change.to_dict()

        assert result['severity'] == 'WARNING'
        assert result['category'] == 'parameter'
        assert result['path'] == 'GET /users / param limit'
        assert result['message'] == 'Parameter removed'
        assert result['old_value'] == {'name': 'limit', 'type': 'integer'}

    def test_change_repr(self):
        change = Change(
            severity=Severity.INFO,
            category='endpoint',
            path='/new',
            message='New endpoint added'
        )

        repr_str = repr(change)
        assert '[INFO]' in repr_str
        assert '/new' in repr_str


class TestContractVerifier:
    """Test ContractVerifier core functionality"""

    def test_initialization(self):
        verifier = ContractVerifier()
        assert verifier.changes == []

    def test_verify_empty_contracts(self):
        verifier = ContractVerifier()
        baseline = {'openapi': '3.0.0', 'paths': {}}
        current = {'openapi': '3.0.0', 'paths': {}}

        changes = verifier.verify(baseline, current)

        assert len(changes) == 0
        assert not verifier.has_breaking_changes()

    def test_has_breaking_changes(self):
        verifier = ContractVerifier()

        # Add breaking change manually
        verifier.changes = [
            Change(Severity.BREAKING, 'endpoint', '/users', 'Removed'),
            Change(Severity.WARNING, 'param', '/users', 'Warning'),
            Change(Severity.INFO, 'endpoint', '/new', 'Added')
        ]

        assert verifier.has_breaking_changes()

    def test_no_breaking_changes(self):
        verifier = ContractVerifier()

        verifier.changes = [
            Change(Severity.WARNING, 'param', '/users', 'Warning'),
            Change(Severity.INFO, 'endpoint', '/new', 'Added')
        ]

        assert not verifier.has_breaking_changes()


class TestEndpointChanges:
    """Test endpoint/path change detection"""

    def test_detect_removed_endpoint(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {'get': {}},
                '/orders': {'get': {}}
            }
        }
        current = {
            'paths': {
                '/users': {'get': {}}
            }
        }

        changes = verifier.verify(baseline, current)

        assert len(changes) == 1
        assert changes[0].severity == Severity.BREAKING
        assert changes[0].category == 'endpoint'
        assert '/orders' in changes[0].path
        assert 'removed' in changes[0].message.lower()

    def test_detect_new_endpoint(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {'get': {}}
            }
        }
        current = {
            'paths': {
                '/users': {'get': {}},
                '/products': {'get': {}}
            }
        }

        changes = verifier.verify(baseline, current)

        assert len(changes) == 1
        assert changes[0].severity == Severity.INFO
        assert changes[0].category == 'endpoint'
        assert '/products' in changes[0].path
        assert 'added' in changes[0].message.lower()

    def test_detect_removed_operation(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {},
                    'post': {},
                    'delete': {}
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {},
                    'post': {}
                }
            }
        }

        changes = verifier.verify(baseline, current)

        assert len(changes) == 1
        assert changes[0].severity == Severity.BREAKING
        assert changes[0].category == 'operation'
        assert 'DELETE /users' in changes[0].path
        assert 'removed' in changes[0].message.lower()

    def test_detect_new_operation(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {}
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {},
                    'post': {}
                }
            }
        }

        changes = verifier.verify(baseline, current)

        assert len(changes) == 1
        assert changes[0].severity == Severity.INFO
        assert changes[0].category == 'operation'
        assert 'POST /users' in changes[0].path


class TestParameterChanges:
    """Test parameter change detection"""

    def test_detect_removed_required_parameter(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {
                        'parameters': [
                            {'name': 'id', 'in': 'query', 'required': True}
                        ]
                    }
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {
                        'parameters': []
                    }
                }
            }
        }

        changes = verifier.verify(baseline, current)

        breaking_changes = [c for c in changes if c.severity == Severity.BREAKING]
        assert len(breaking_changes) == 1
        assert 'id' in breaking_changes[0].path
        assert 'removed' in breaking_changes[0].message.lower()

    def test_detect_removed_optional_parameter(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {
                        'parameters': [
                            {'name': 'limit', 'in': 'query', 'required': False}
                        ]
                    }
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {
                        'parameters': []
                    }
                }
            }
        }

        changes = verifier.verify(baseline, current)

        # Optional parameter removal is WARNING, not BREAKING
        warnings = [c for c in changes if c.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert 'limit' in warnings[0].path

    def test_detect_new_required_parameter(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {
                        'parameters': []
                    }
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {
                        'parameters': [
                            {'name': 'api_key', 'in': 'header', 'required': True}
                        ]
                    }
                }
            }
        }

        changes = verifier.verify(baseline, current)

        # New required parameter is BREAKING (clients must provide it)
        breaking_changes = [c for c in changes if c.severity == Severity.BREAKING]
        assert len(breaking_changes) == 1
        assert 'api_key' in breaking_changes[0].path
        assert 'required' in breaking_changes[0].message.lower()

    def test_detect_new_optional_parameter(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {
                        'parameters': []
                    }
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {
                        'parameters': [
                            {'name': 'filter', 'in': 'query', 'required': False}
                        ]
                    }
                }
            }
        }

        changes = verifier.verify(baseline, current)

        # New optional parameter is INFO only
        info_changes = [c for c in changes if c.severity == Severity.INFO]
        assert len(info_changes) == 1
        assert 'filter' in info_changes[0].path

    def test_detect_parameter_made_required(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {
                        'parameters': [
                            {'name': 'sort', 'in': 'query', 'required': False, 'schema': {'type': 'string'}}
                        ]
                    }
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {
                        'parameters': [
                            {'name': 'sort', 'in': 'query', 'required': True, 'schema': {'type': 'string'}}
                        ]
                    }
                }
            }
        }

        changes = verifier.verify(baseline, current)

        breaking_changes = [c for c in changes if c.severity == Severity.BREAKING]
        assert len(breaking_changes) == 1
        assert 'made required' in breaking_changes[0].message.lower()

    def test_detect_parameter_type_change(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {
                        'parameters': [
                            {'name': 'id', 'in': 'query', 'schema': {'type': 'string'}}
                        ]
                    }
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {
                        'parameters': [
                            {'name': 'id', 'in': 'query', 'schema': {'type': 'integer'}}
                        ]
                    }
                }
            }
        }

        changes = verifier.verify(baseline, current)

        breaking_changes = [c for c in changes if c.severity == Severity.BREAKING]
        assert len(breaking_changes) == 1
        assert 'type changed' in breaking_changes[0].message.lower()
        assert 'string' in breaking_changes[0].message
        assert 'integer' in breaking_changes[0].message


class TestRequestBodyChanges:
    """Test request body change detection"""

    def test_detect_request_body_removed(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'post': {
                        'requestBody': {
                            'required': True,
                            'content': {
                                'application/json': {
                                    'schema': {'type': 'object'}
                                }
                            }
                        }
                    }
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'post': {}
                }
            }
        }

        changes = verifier.verify(baseline, current)

        breaking_changes = [c for c in changes if c.severity == Severity.BREAKING]
        assert len(breaking_changes) == 1
        assert 'requestBody' in breaking_changes[0].path
        assert 'removed' in breaking_changes[0].message.lower()

    def test_detect_required_request_body_added(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'post': {}
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'post': {
                        'requestBody': {
                            'required': True,
                            'content': {
                                'application/json': {
                                    'schema': {'type': 'object'}
                                }
                            }
                        }
                    }
                }
            }
        }

        changes = verifier.verify(baseline, current)

        breaking_changes = [c for c in changes if c.severity == Severity.BREAKING]
        assert len(breaking_changes) == 1
        assert 'required' in breaking_changes[0].message.lower()


class TestResponseChanges:
    """Test response change detection"""

    def test_detect_removed_response_code(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {'description': 'Success'},
                            '404': {'description': 'Not Found'}
                        }
                    }
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {'description': 'Success'}
                        }
                    }
                }
            }
        }

        changes = verifier.verify(baseline, current)

        breaking_changes = [c for c in changes if c.severity == Severity.BREAKING]
        assert len(breaking_changes) == 1
        assert '404' in breaking_changes[0].path
        assert 'removed' in breaking_changes[0].message.lower()

    def test_detect_new_response_code(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {'description': 'Success'}
                        }
                    }
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {'description': 'Success'},
                            '400': {'description': 'Bad Request'}
                        }
                    }
                }
            }
        }

        changes = verifier.verify(baseline, current)

        info_changes = [c for c in changes if c.severity == Severity.INFO]
        assert len(info_changes) == 1
        assert '400' in info_changes[0].path


class TestSchemaChanges:
    """Test JSON schema change detection"""

    def test_detect_response_type_change(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {
                                'content': {
                                    'application/json': {
                                        'schema': {'type': 'array'}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {
                                'content': {
                                    'application/json': {
                                        'schema': {'type': 'object'}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        changes = verifier.verify(baseline, current)

        breaking_changes = [c for c in changes if c.severity == Severity.BREAKING]
        assert len(breaking_changes) == 1
        assert 'type changed' in breaking_changes[0].message.lower()
        assert 'array' in breaking_changes[0].message
        assert 'object' in breaking_changes[0].message

    def test_detect_removed_required_property(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'id': {'type': 'integer'},
                                                'name': {'type': 'string'}
                                            },
                                            'required': ['id', 'name']
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'id': {'type': 'integer'}
                                            },
                                            'required': ['id']
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        changes = verifier.verify(baseline, current)

        breaking_changes = [c for c in changes if c.severity == Severity.BREAKING]
        assert any('name' in c.path and 'removed' in c.message.lower() for c in breaking_changes)

    def test_detect_removed_optional_property(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'id': {'type': 'integer'},
                                                'email': {'type': 'string'}
                                            },
                                            'required': ['id']
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'id': {'type': 'integer'}
                                            },
                                            'required': ['id']
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        changes = verifier.verify(baseline, current)

        # Optional property removal is WARNING
        warnings = [c for c in changes if c.severity == Severity.WARNING]
        assert any('email' in c.path for c in warnings)

    def test_detect_new_required_property(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'id': {'type': 'integer'}
                                            },
                                            'required': ['id']
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'id': {'type': 'integer'},
                                                'status': {'type': 'string'}
                                            },
                                            'required': ['id', 'status']
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        changes = verifier.verify(baseline, current)

        # New required property in response is BREAKING (client must handle it)
        breaking_changes = [c for c in changes if c.severity == Severity.BREAKING]
        assert any('status' in c.path and 'required' in c.message.lower() for c in breaking_changes)

    def test_detect_new_optional_property(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'id': {'type': 'integer'}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'id': {'type': 'integer'},
                                                'metadata': {'type': 'object'}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        changes = verifier.verify(baseline, current)

        # New optional property is INFO
        info_changes = [c for c in changes if c.severity == Severity.INFO]
        assert any('metadata' in c.path for c in info_changes)

    def test_detect_property_made_required(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'role': {'type': 'string'}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'role': {'type': 'string'}
                                            },
                                            'required': ['role']
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        changes = verifier.verify(baseline, current)

        breaking_changes = [c for c in changes if c.severity == Severity.BREAKING]
        assert any('role' in c.path and 'made required' in c.message.lower() for c in breaking_changes)


class TestReportFormatting:
    """Test report generation"""

    def test_get_report_text(self):
        verifier = ContractVerifier()
        verifier.changes = [
            Change(Severity.BREAKING, 'endpoint', '/users', 'Endpoint removed'),
            Change(Severity.WARNING, 'parameter', 'GET /items', 'Parameter removed'),
            Change(Severity.INFO, 'endpoint', '/new', 'New endpoint')
        ]

        report = verifier.get_report(format='text')

        assert 'Contract Changes' in report
        assert 'BREAKING CHANGES' in report
        assert 'WARNINGS' in report
        assert 'INFO' in report
        assert '/users' in report
        assert '/items' in report
        assert '/new' in report

    def test_get_report_json(self):
        verifier = ContractVerifier()
        verifier.changes = [
            Change(Severity.BREAKING, 'endpoint', '/users', 'Endpoint removed')
        ]

        report = verifier.get_report(format='json')

        data = json.loads(report)
        assert len(data) == 1
        assert data[0]['severity'] == 'BREAKING'
        assert data[0]['category'] == 'endpoint'
        assert data[0]['path'] == '/users'

    def test_get_report_markdown(self):
        verifier = ContractVerifier()
        verifier.changes = [
            Change(Severity.BREAKING, 'endpoint', '/users', 'Endpoint removed'),
            Change(Severity.INFO, 'endpoint', '/new', 'New endpoint')
        ]

        report = verifier.get_report(format='markdown')

        assert '# Contract Changes' in report
        assert '## 🔴 Breaking Changes' in report
        assert '## ℹ️ Info' in report
        assert '/users' in report
        assert '/new' in report

    def test_empty_report(self):
        verifier = ContractVerifier()
        verifier.changes = []

        text_report = verifier.get_report(format='text')
        assert 'No changes detected' in text_report

        md_report = verifier.get_report(format='markdown')
        assert 'No Changes Detected' in md_report


class TestFileIO:
    """Test file I/O operations"""

    def test_verify_files(self, tmp_path):
        # Create baseline contract
        baseline = {
            'openapi': '3.0.0',
            'paths': {
                '/users': {'get': {}}
            }
        }
        baseline_file = tmp_path / 'baseline.yaml'
        with open(baseline_file, 'w') as f:
            yaml.dump(baseline, f)

        # Create current contract with changes
        current = {
            'openapi': '3.0.0',
            'paths': {
                '/users': {'get': {}},
                '/products': {'get': {}}
            }
        }
        current_file = tmp_path / 'current.yaml'
        with open(current_file, 'w') as f:
            yaml.dump(current, f)

        verifier = ContractVerifier()
        changes = verifier.verify_files(str(baseline_file), str(current_file))

        assert len(changes) == 1
        assert changes[0].severity == Severity.INFO
        assert '/products' in changes[0].path

    def test_load_json_contract(self, tmp_path):
        contract = {
            'openapi': '3.0.0',
            'paths': {}
        }
        contract_file = tmp_path / 'contract.json'
        with open(contract_file, 'w') as f:
            json.dump(contract, f)

        verifier = ContractVerifier()
        loaded = verifier._load_contract(str(contract_file))

        assert loaded['openapi'] == '3.0.0'


class TestIntegrationWithFixtures:
    """Integration tests with fixture files"""

    def test_verify_fixture_contracts(self):
        verifier = ContractVerifier()

        baseline_file = Path(__file__).parent / 'fixtures' / 'baseline-contract.yaml'
        current_file = Path(__file__).parent / 'fixtures' / 'current-contract.yaml'

        changes = verifier.verify_files(str(baseline_file), str(current_file))

        # Should detect changes from fixtures
        assert len(changes) > 0

        # Should have at least one breaking change (endpoint removed)
        breaking = [c for c in changes if c.severity == Severity.BREAKING]
        assert len(breaking) > 0

    def test_has_breaking_changes_from_fixtures(self):
        verifier = ContractVerifier()

        baseline_file = Path(__file__).parent / 'fixtures' / 'baseline-contract.yaml'
        current_file = Path(__file__).parent / 'fixtures' / 'current-contract.yaml'

        verifier.verify_files(str(baseline_file), str(current_file))

        assert verifier.has_breaking_changes()


class TestConvenienceFunction:
    """Test verify_contracts convenience function"""

    def test_verify_contracts(self, tmp_path):
        # Create contracts
        baseline = {
            'openapi': '3.0.0',
            'paths': {
                '/users': {'get': {}, 'delete': {}}
            }
        }
        baseline_file = tmp_path / 'baseline.yaml'
        with open(baseline_file, 'w') as f:
            yaml.dump(baseline, f)

        current = {
            'openapi': '3.0.0',
            'paths': {
                '/users': {'get': {}}  # DELETE removed
            }
        }
        current_file = tmp_path / 'current.yaml'
        with open(current_file, 'w') as f:
            yaml.dump(current, f)

        is_compatible, changes = verify_contracts(
            str(baseline_file),
            str(current_file),
            verbose=False
        )

        assert not is_compatible  # Breaking change present
        assert len(changes) > 0

    def test_verify_contracts_with_output_file(self, tmp_path):
        # Create contracts
        baseline = {
            'openapi': '3.0.0',
            'paths': {
                '/users': {'get': {}}
            }
        }
        baseline_file = tmp_path / 'baseline.yaml'
        with open(baseline_file, 'w') as f:
            yaml.dump(baseline, f)

        current = {
            'openapi': '3.0.0',
            'paths': {
                '/users': {'get': {}},
                '/products': {'get': {}}
            }
        }
        current_file = tmp_path / 'current.yaml'
        with open(current_file, 'w') as f:
            yaml.dump(current, f)

        output_file = tmp_path / 'report.txt'

        is_compatible, changes = verify_contracts(
            str(baseline_file),
            str(current_file),
            output_file=str(output_file),
            format='text',
            verbose=False
        )

        assert is_compatible  # No breaking changes
        assert output_file.exists()

        report = output_file.read_text()
        assert 'Contract Changes' in report or 'No changes detected' in report


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_missing_components_section(self):
        verifier = ContractVerifier()
        baseline = {'paths': {}}
        current = {'paths': {}}

        # Should not crash when components section is missing
        changes = verifier.verify(baseline, current)
        assert len(changes) == 0

    def test_empty_paths(self):
        verifier = ContractVerifier()
        baseline = {'paths': {}}
        current = {'paths': {}}

        changes = verifier.verify(baseline, current)
        assert len(changes) == 0

    def test_nested_schema_changes(self):
        verifier = ContractVerifier()
        baseline = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'address': {
                                                    'type': 'object',
                                                    'properties': {
                                                        'street': {'type': 'string'}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        current = {
            'paths': {
                '/users': {
                    'get': {
                        'responses': {
                            '200': {
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'address': {
                                                    'type': 'object',
                                                    'properties': {
                                                        'street': {'type': 'integer'}  # Type changed
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        changes = verifier.verify(baseline, current)

        # Should detect nested type change
        breaking_changes = [c for c in changes if c.severity == Severity.BREAKING]
        assert len(breaking_changes) > 0
        assert any('street' in c.path for c in breaking_changes)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
