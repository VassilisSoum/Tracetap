# Contributing to TraceTap

Thank you for your interest in contributing to TraceTap! This document provides guidelines and instructions for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)
- [Testing](#testing)
- [Documentation](#documentation)

## 🤝 Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive experience for everyone. We pledge to:

- Be respectful and considerate
- Be collaborative and constructive
- Focus on what is best for the community
- Show empathy towards other community members

### Our Standards

**Positive behaviors include:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community

**Unacceptable behaviors include:**
- Harassment of any kind
- Trolling, insulting/derogatory comments
- Public or private harassment
- Publishing others' private information
- Other conduct inappropriate in a professional setting

## 🎯 How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates.

**Good bug reports include:**
- Clear, descriptive title
- Steps to reproduce the problem
- Expected vs actual behavior
- Screenshots (if applicable)
- Environment details (OS, Python version, mitmproxy version)
- Relevant logs or error messages

**Use this template:**

```markdown
**Description:**
Brief description of the bug

**To Reproduce:**
1. Start TraceTap with: `./tracetap --listen 8080`
2. Configure proxy in browser
3. Visit https://example.com
4. See error

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Environment:**
- OS: [e.g., Ubuntu 22.04, macOS 14, Windows 11]
- TraceTap Version: [e.g., 1.0.0]
- Python Version: [e.g., 3.12]
- Browser: [e.g., Chrome 120]

**Logs:**
```
Paste relevant logs here
```

**Screenshots:**
If applicable
```

### Suggesting Features

We welcome feature suggestions! Please:

1. **Check existing issues** for similar requests
2. **Provide clear use case** - explain the problem it solves
3. **Describe the solution** - how should it work?
4. **Consider alternatives** - are there other ways to solve this?

**Use this template:**

```markdown
**Feature Request:**
Brief description

**Problem:**
What problem does this solve?

**Proposed Solution:**
How should it work?

**Alternatives Considered:**
Other ways to solve this

**Additional Context:**
Any other information
```

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Test thoroughly**
5. **Commit your changes** (`git commit -m 'Add amazing feature'`)
6. **Push to your fork** (`git push origin feature/amazing-feature`)
7. **Open a Pull Request**

## 🛠️ Development Setup

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git

### Setup Instructions

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR-USERNAME/tracetap.git
cd tracetap

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Install development dependencies
pip install pytest pytest-cov black flake8 mypy

# 6. Run TraceTap to verify setup
python tracetap.py --listen 8080
# Press Ctrl+C to stop
```

### Development Workflow

```bash
# Create a feature branch
git checkout -b feature/my-feature

# Make changes and test
python tracetap.py --listen 8080 --verbose

# Run tests
pytest

# Format code
black tracetap.py

# Check code quality
flake8 tracetap.py

# Commit changes
git add .
git commit -m "feat: add my feature"

# Push and create PR
git push origin feature/my-feature
```

## 📝 Coding Standards

### Python Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some modifications:

**Line Length:**
- Maximum 100 characters (not 79)

**Imports:**
```python
# Standard library
import os
import sys

# Third-party
from mitmproxy import http

# Local
from tracetap import utils
```

**Naming Conventions:**
```python
# Classes: PascalCase
class TraceTapAddon:
    pass

# Functions/methods: snake_case
def capture_request():
    pass

# Constants: UPPER_SNAKE_CASE
MAX_BODY_SIZE = 64 * 1024

# Variables: snake_case
request_count = 0
```

**Docstrings:**
```python
def export_collection(records: List[Dict], output_path: str) -> None:
    """
    Export records to Postman collection format.
    
    Args:
        records: List of captured request/response records
        output_path: Path to output JSON file
        
    Returns:
        None
        
    Raises:
        IOError: If output file cannot be written
    """
    pass
```

### Shell Script Style

For bash scripts (certificate managers):

```bash
# Use shellcheck for validation
shellcheck script.sh

# Use functions for organization
function install_certificate() {
    # Function body
}

# Always quote variables
echo "$VARIABLE"

# Use meaningful variable names
CERT_PATH="$HOME/.mitmproxy/cert.pem"

# Add comments for complex logic
# Check if certificate already exists before installing
if [ -f "$CERT_PATH" ]; then
    # ...
fi
```

### PowerShell Style

For PowerShell scripts:

```powershell
# Use approved verbs (Get, Set, New, Remove, etc.)
function Get-CertificateStatus { }

# Use PascalCase for functions
function Install-Certificate { }

# Use full parameter names
Get-ChildItem -Path $Path -Recurse

# Use proper error handling
try {
    # Code
} catch {
    Write-Error "Error: $_"
}
```

### Code Formatting

We use **Black** for Python code formatting:

```bash
# Format single file
black tracetap.py

# Format all Python files
black .

# Check without modifying
black --check tracetap.py
```

### Linting

We use **flake8** for linting:

```bash
# Run flake8
flake8 tracetap.py

# With configuration
flake8 --max-line-length=100 tracetap.py
```

### Type Hints

Use type hints where possible:

```python
from typing import List, Dict, Optional

def process_records(
    records: List[Dict[str, Any]], 
    output_path: str,
    verbose: bool = False
) -> Optional[int]:
    """Process and export records."""
    pass
```

## 🔄 Submitting Changes

### Pull Request Process

1. **Update documentation** if you change functionality
2. **Add tests** for new features
3. **Ensure all tests pass**
4. **Update CHANGELOG.md** with your changes
5. **Follow commit message conventions**

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```bash
# Feature
git commit -m "feat: add WireMock stub generation"

# Bug fix
git commit -m "fix: handle empty response bodies correctly"

# Documentation
git commit -m "docs: update installation instructions for Windows"

# With body
git commit -m "feat: add regex filtering

Add support for filtering captured traffic using regex patterns.
Users can now use --filter-regex to capture only matching URLs.

Closes #42"
```

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## How Has This Been Tested?
Describe the tests you ran

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing unit tests pass locally
- [ ] Any dependent changes have been merged and published

## Screenshots (if applicable)
Add screenshots here
```

## 🐛 Reporting Bugs

### Security Vulnerabilities

**DO NOT** open public issues for security vulnerabilities.

Instead, email: [your-email@example.com] with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours.

### Bug Report Guidelines

**Before submitting:**
1. Search existing issues
2. Try latest version
3. Check documentation

**Include:**
- Minimal reproduction steps
- Expected vs actual behavior
- Environment details
- Error messages/logs
- Relevant configuration

## 💡 Suggesting Features

### Feature Request Guidelines

Good feature requests:
- Solve a real problem
- Align with project goals
- Are well-defined and scoped
- Consider existing functionality
- Include use cases

### Feature Request Process

1. **Open a discussion** in GitHub Discussions first
2. **Get community feedback**
3. **Refine the proposal**
4. **Create formal issue** if there's consensus
5. **Implement** (or wait for someone else to)

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tracetap

# Run specific test file
pytest tests/test_export.py

# Run specific test
pytest tests/test_export.py::test_postman_export

# Verbose output
pytest -v
```

### Writing Tests

```python
import pytest
from tracetap import export_collection

def test_export_postman_collection():
    """Test Postman collection export."""
    records = [
        {
            "method": "GET",
            "url": "https://api.example.com/users",
            "status": 200,
            # ... other fields
        }
    ]
    
    output_path = "test_output.json"
    export_collection(records, output_path)
    
    # Verify output
    assert os.path.exists(output_path)
    
    with open(output_path) as f:
        collection = json.load(f)
    
    assert collection["info"]["schema"].endswith("v2.1.0/collection.json")
    assert len(collection["item"]) == 1
```

### Test Coverage

We aim for **80%+ test coverage**:

```bash
# Generate coverage report
pytest --cov=tracetap --cov-report=html

# Open report
open htmlcov/index.html
```

### Manual Testing

Before submitting PR, test manually:

```bash
# Basic functionality
./tracetap --listen 8080 --export test.json

# Filtering
./tracetap --listen 8080 --filter-host "example.com"

# WireMock export
python tracetap2wiremock.py test.json -o stubs/

# Certificate installation (on each platform)
./chrome-cert-manager.sh install        # Linux
./macos-cert-manager.sh install         # macOS
.\windows-cert-manager.ps1 install      # Windows
```

## 📚 Documentation

### Documentation Standards

**Update documentation when you:**
- Add new features
- Change behavior
- Fix bugs that affect usage
- Add new command-line options

**Documentation files:**
- `README.md` - Main documentation
- `QUICK_START.md` - Getting started guide
- `CERTIFICATE_INSTALLATION.md` - Certificate setup
- `WIREMOCK_WORKFLOW.md` - WireMock integration
- Code comments and docstrings

### Writing Good Documentation

**Be clear and concise:**
```markdown
# ❌ Bad
The thing does stuff with the other thing.

# ✅ Good
TraceTap captures HTTP/HTTPS traffic through a proxy server.
```

**Provide examples:**
```markdown
# ❌ Bad
Use --filter-host to filter hosts.

# ✅ Good
Capture only specific hosts:
```bash
./tracetap --listen 8080 --filter-host "api.example.com"
```
```

**Use proper formatting:**
- Headers for structure
- Code blocks for commands
- Lists for steps
- Bold for emphasis
- Links for references

## 🏗️ Project Structure

```
tracetap/
├── tracetap.py                    # Main proxy script
├── tracetap2wiremock.py          # WireMock converter
├── build_executables.py          # Build script
├── requirements.txt              # Python dependencies
├── LICENSE                       # MIT License
├── README.md                     # Main documentation
├── CONTRIBUTING.md              # This file
├── QUICK_START.md               # Getting started
├── CERTIFICATE_INSTALLATION.md  # Cert setup guide
├── WIREMOCK_WORKFLOW.md         # WireMock guide
├── chrome-cert-manager.sh       # Linux cert script
├── macos-cert-manager.sh        # macOS cert script
├── windows-cert-manager.ps1     # Windows cert script
├── .github/
│   └── workflows/
│       └── release.yml          # CI/CD pipeline
└── tests/                       # Test files
    ├── test_capture.py
    ├── test_export.py
    └── test_wiremock.py
```

## 🎨 Design Principles

### Keep It Simple

- Favor simplicity over complexity
- One tool should do one thing well
- Clear error messages
- Sensible defaults

### User-Friendly

- Easy installation
- Clear documentation
- Helpful error messages
- Cross-platform support

### Reliable

- Comprehensive testing
- Error handling
- Input validation
- Graceful degradation

### Maintainable

- Clean code
- Good documentation
- Minimal dependencies
- Follow standards

## 🤔 Questions?

- **General questions:** Open a [Discussion](https://github.com/VassilisSoum/tracetap/discussions)
- **Bug reports:** Open an [Issue](https://github.com/VassilisSoum/tracetap/issues)
- **Feature requests:** Open a [Discussion](https://github.com/VassilisSoum/tracetap/discussions) first
- **Security issues:** Email [billsoumakis@gmail.com]

## 📜 License

By contributing to TraceTap, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in relevant documentation

Thank you for contributing to TraceTap! 🎉