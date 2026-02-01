# Python API Reference

Use TraceTap as a library in your Python code.

## Table of Contents

- [Installation](#installation)
- [Traffic Capture](#traffic-capture)
- [Test Generation](#test-generation)
- [AI Transformation](#ai-transformation)
- [Contract Management](#contract-management)

---

## Installation

```bash
# Install with library dependencies
pip install -r requirements.txt
pip install -r requirements-ai.txt  # For AI features
```

---

## Traffic Capture

### Loading Captured Traffic

```python
import json

# Load captures from raw JSON log
with open('captures.json') as f:
    data = json.load(f)

# Access captured requests
for request in data.get('requests', []):
    print(f"{request['method']} {request['url']}")
    print(f"  Status: {request['response']['status']}")
    print(f"  Duration: {request.get('duration_ms', 0)}ms")
```

### Filtering Captures

```python
import json

with open('captures.json') as f:
    data = json.load(f)

# Filter by method
get_requests = [r for r in data['requests'] if r['method'] == 'GET']

# Filter by status
errors = [r for r in data['requests'] if r['response']['status'] >= 400]

# Filter by URL pattern
import re
api_requests = [r for r in data['requests']
                if re.search(r'/api/v\d+/', r['url'])]
```

---

## Test Generation

### Playwright Test Generation

```python
from src.tracetap.playwright import PlaywrightGenerator
import json

with open('captures.json') as f:
    data = json.load(f)

# Create generator
generator = PlaywrightGenerator(
    captures=data['requests'],
    class_name='TestAPIEndpoints',
    output_dir='tests/'
)

# Generate tests
generator.generate(
    include_assertions=True,
    include_docstrings=True,
    skip_timing=False
)

print("Tests generated in tests/")
```

### With AI Suggestions

```python
from src.tracetap.ai import TestSuggester, TestGenerator
import os

# Get AI suggestions
suggester = TestSuggester(
    api_key=os.getenv('ANTHROPIC_API_KEY')
)

suggestions = suggester.suggest_tests(
    captures=data['requests'],
    focus_areas=['edge_cases', 'error_handling', 'security']
)

# Generate test code from suggestions
generator = TestGenerator()

for category, tests in suggestions.items():
    for test_case in tests:
        code = generator.generate_test_code(
            test=test_case,
            language='python',
            framework='pytest'
        )

        # Save or use generated code
        print(code)
```

---

## AI Transformation

TraceTap uses AI to transform raw captures into various test artifacts. You can leverage this capability programmatically.

### Basic AI Transformation

```python
from src.tracetap.ai import AITransformer
import os

transformer = AITransformer(
    api_key=os.getenv('ANTHROPIC_API_KEY')
)

# Transform captures to test code
test_code = transformer.transform_to_tests(
    captures=data['requests'],
    format='pytest',
    include_assertions=True
)

# Write generated tests
with open('tests/test_generated.py', 'w') as f:
    f.write(test_code)
```

### Custom Transformation Prompts

```python
from src.tracetap.ai import AITransformer

transformer = AITransformer(
    api_key=os.getenv('ANTHROPIC_API_KEY')
)

# Custom prompt for specific transformation
custom_prompt = """
Transform these API captures into pytest tests that:
1. Focus on error handling scenarios
2. Include parameterized tests for different user types
3. Add security-focused assertions
"""

result = transformer.transform(
    captures=data['requests'],
    prompt=custom_prompt
)
```

---

## Contract Management

### Create Contract

```python
from src.tracetap.contract import ContractCreator
import json

with open('captures.json') as f:
    captures = json.load(f)

# Create contract
creator = ContractCreator(
    provider='my-service',
    consumer='client-app',
    base_url='https://api.example.com'
)

contract = creator.create_from_captures(
    captures['requests'],
    extract_parameters=True
)

# Save contract
with open('contract.json', 'w') as f:
    json.dump(contract, f, indent=2)
```

### Verify Contract

```python
from src.tracetap.contract import ContractVerifier
import json

with open('contract.json') as f:
    contract = json.load(f)

# Verify contract
verifier = ContractVerifier(contract)

result = verifier.verify(
    base_url='http://localhost:3000',
    verbose=True
)

if result.passed:
    print(f"All {result.total} interactions verified")
else:
    print(f"{result.failed} / {result.total} failed:")
    for failure in result.failures:
        print(f"  - {failure}")
```

### Generate Verification Tests

```python
from src.tracetap.contract import ContractVerifier
import json

with open('contract.json') as f:
    contract = json.load(f)

# Generate test file
verifier = ContractVerifier(contract)

test_code = verifier.generate_tests(
    language='python',
    framework='pytest',
    base_url='http://localhost:3000'
)

# Save test file
with open('tests/test_contract.py', 'w') as f:
    f.write(test_code)

print("Contract verification tests generated")
```

---

## Advanced Patterns

### Custom Request Processing

```python
import json

with open('captures.json') as f:
    data = json.load(f)

def process_request(request):
    """Modify request for analysis"""
    # Remove sensitive headers
    if 'Authorization' in request.get('headers', {}):
        request['headers']['Authorization'] = 'Bearer REDACTED'

    # Normalize URL
    request['url'] = request['url'].replace(
        'https://api.production.com',
        'http://localhost:8080'
    )

    return request

# Process all requests
processed = [process_request(r) for r in data['requests']]
```

### Extracting API Patterns

```python
from collections import defaultdict
import re

def extract_endpoints(captures):
    """Extract unique API endpoints from captures"""
    endpoints = defaultdict(set)

    for request in captures:
        method = request['method']
        url = request['url']

        # Extract path without query params
        path = url.split('?')[0]

        # Normalize IDs to placeholders
        path = re.sub(r'/\d+', '/{id}', path)

        endpoints[method].add(path)

    return dict(endpoints)

with open('captures.json') as f:
    data = json.load(f)

patterns = extract_endpoints(data['requests'])
for method, paths in patterns.items():
    print(f"{method}:")
    for path in sorted(paths):
        print(f"  {path}")
```

---

## Next Steps

- **[CLI Reference](cli-reference.md)** - Command-line tools
- **[Guides](../guides/)** - Learn workflows
