# TraceTap Test Suite

Comprehensive tests for TraceTap certificate installer and core functionality.

## Setup

### Install Test Dependencies

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Or install just testing tools
pip install pytest pytest-cov pytest-mock
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_cert_installer.py
```

### Run with Coverage
```bash
pytest --cov=src/tracetap --cov-report=html
```

### Run with Verbose Output
```bash
pytest -v
```

### Run Specific Test
```bash
pytest tests/test_cert_installer.py::TestCertificateInstaller::test_platform_detection
```

## Test Structure

```
tests/
├── __init__.py
├── README.md
├── test_cert_installer.py      # Certificate installer tests (✅ Complete)
├── test_filters.py              # Filter logic tests (TODO)
├── test_exporters.py            # Exporter tests (TODO)
├── test_integration.py          # Integration tests (TODO)
└── fixtures/                    # Test data and fixtures
    ├── sample_captures.json
    └── sample_certificates/
```

## Test Coverage

Current test coverage by module:

| Module | Coverage | Tests |
|--------|----------|-------|
| `cert_installer.py` | ~90% | 40+ tests |
| `filters.py` | 0% | TODO |
| `exporters.py` | 0% | TODO |
| `tracetap_addon.py` | 0% | TODO |

**Goal:** 70%+ overall coverage

## Writing Tests

### Test Organization

- One test file per module
- Group related tests in classes
- Use descriptive test names: `test_<what>_<condition>_<expected>`
- Use fixtures for common setup

### Example Test

```python
def test_certificate_validation_with_valid_cert(installer_with_mock_cert):
    """Test that valid certificates pass validation."""
    assert installer_with_mock_cert.validate_certificate() is True
```

### Mocking Guidelines

- Mock external commands (`subprocess.run`)
- Mock file system operations when testing logic
- Don't mock the code under test
- Use `pytest-mock` for cleaner mocking

### Test Categories

**Unit Tests:**
- Test individual functions/methods
- Mock all dependencies
- Fast execution (<1s per test)

**Integration Tests:**
- Test module interactions
- May use real file system (temp directories)
- Moderate execution time

**E2E Tests:**
- Test complete workflows
- May start actual proxy
- Slower execution

## CI/CD Integration

Tests run automatically on:
- Every push to main branch
- Every pull request
- All supported platforms (Ubuntu, macOS, Windows)

See `.github/workflows/test.yml` for CI configuration.

## Troubleshooting

### Import Errors

If you see import errors when running tests:

```bash
# Ensure src/tracetap is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src/tracetap"
```

### Pytest Not Found

```bash
pip install pytest
```

### Coverage Report Not Generated

```bash
pip install pytest-cov
```

## Test Checklist for New Features

When adding new features, ensure:

- [ ] Unit tests for all new functions/methods
- [ ] Integration tests for module interactions
- [ ] Edge cases covered (errors, missing data, etc.)
- [ ] Documentation strings for test functions
- [ ] Tests pass on all platforms
- [ ] Coverage ≥70% for new code

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)
