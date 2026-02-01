# Contributing to TraceTap

Thank you for your interest in contributing to TraceTap! We welcome contributions from the community and are excited to work with you.

## Code of Conduct

This project adheres to the Contributor Covenant Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### Prerequisites
- Python 3.11+
- pip or Poetry package manager
- Git

### Development Setup

1. **Fork the repository**
   ```bash
   # Visit https://github.com/terminatorbill/Tracetap and click "Fork"
   ```

2. **Clone your fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Tracetap.git
   cd Tracetap
   ```

3. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   # or with Poetry
   poetry install
   ```

5. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or for bug fixes
   git checkout -b fix/your-bug-fix
   ```

## Development Workflow

### Running Tests
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=tracetap tests/

# Run specific test file
pytest tests/test_file.py
```

### Code Style Guidelines

We follow PEP 8 with some modifications. Use these tools:

```bash
# Format code
black .

# Sort imports
isort .

# Lint
ruff check .

# Type checking
mypy tracetap/
```

All code must pass these checks before submission.

### Commit Messages

Write clear, descriptive commit messages following this format:

```
[TYPE] Brief description (50 chars max)

Longer explanation of the change (wrap at 72 chars).
- Bullet point 1
- Bullet point 2

Fixes #123
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `style`, `chore`

Example:
```
[fix] Resolve race condition in proxy interceptor

The proxy interceptor had a race condition when multiple
connections were handled simultaneously. Fixed by adding
proper locking in the request queue handler.

Fixes #456
```

## Making Changes

### Finding Issues to Work On
- Check the [Issues](https://github.com/terminatorbill/Tracetap/issues) page
- Look for issues labeled `good first issue` or `help wanted`
- Comment on an issue to let maintainers know you're working on it

### Create a Feature Branch
```bash
git checkout -b feature/descriptive-name
```

### Write Tests First
We encourage test-driven development:
1. Write a failing test
2. Implement the feature
3. Ensure tests pass

### Local Testing
```bash
# Run the full test suite
pytest

# Test specific functionality
pytest tests/test_proxy.py::TestProxyInterceptor

# Generate coverage report
pytest --cov=tracetap --cov-report=html
```

### Code Review Checklist
Before submitting a PR, ensure:
- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] Commits are clear and focused
- [ ] No unrelated changes

## Submitting Changes

### Create a Pull Request

1. **Push your branch**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request**
   - Go to the repository on GitHub
   - Click "New Pull Request"
   - Select your branch and fill out the PR template
   - Link any related issues

3. **Respond to Reviews**
   - Address feedback promptly
   - Push additional commits to the same branch
   - Comment on resolved issues

### PR Requirements
- [ ] Passes all CI checks
- [ ] At least one approval from maintainers
- [ ] Clear commit history
- [ ] Updated tests and docs

## Project Structure

```
Tracetap/
├── tracetap/           # Main package
│   ├── proxy/          # Proxy interception logic
│   ├── mitmproxy/      # mitmproxy integration
│   ├── utils/          # Utility functions
│   └── __init__.py
├── tests/              # Test suite
│   ├── fixtures/       # Test fixtures and data
│   └── test_*.py       # Test files
├── docs/               # Documentation
├── README.md
├── CONTRIBUTING.md     # This file
├── pyproject.toml      # Project configuration
└── pytest.ini          # Pytest configuration
```

## Running the Application

```bash
# Start the proxy server
python -m tracetap.main

# With custom configuration
python -m tracetap.main --config config.yaml

# See available options
python -m tracetap.main --help
```

## Documentation

- Update `docs/` for significant changes
- Add docstrings to all public functions
- Include type hints for better clarity
- Update README.md if adding user-facing features

## Reporting Issues

### Security Issues
Please **do not** open public issues for security vulnerabilities. Email the maintainers directly.

### Bug Reports
Include:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or screenshots

### Feature Requests
Include:
- Use case and problem statement
- Proposed solution
- Alternative approaches
- Any relevant context

## Getting Help

- **Questions**: Open a Discussion or GitHub Issue
- **Documentation**: Check [docs/](docs/) and README.md
- **Chat**: Join our community discussions
- **Email**: Contact maintainers for sensitive issues

## Licensing

By contributing to TraceTap, you agree that your contributions will be licensed under the project's license.

## Recognition

Contributors will be recognized in:
- The project README
- Release notes
- GitHub contributors page

Thank you for contributing to TraceTap!
