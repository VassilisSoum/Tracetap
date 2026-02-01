# Python API Reference

Use TraceTap as a library in your Python code.

## Table of Contents

- [Installation](#installation)
- [Traffic Replay](#traffic-replay)
- [Mock Server](#mock-server)
- [Variable Extraction](#variable-extraction)
- [Test Generation](#test-generation)
- [Contract Management](#contract-management)

---

## Installation

```bash
# Install with library dependencies
pip install -r requirements.txt
pip install -r requirements-ai.txt  # For AI features
pip install -r requirements-replay.txt  # For replay/mock
```

---

## Traffic Replay

### Basic Replay

```python
from src.tracetap.replay import TrafficReplayer
import json

# Load captures
with open('session.json') as f:
    data = json.load(f)

# Create replayer
replayer = TrafficReplayer('session.json')

# Replay to different server
result = replayer.replay(
    target_base_url='http://localhost:8080',
    max_workers=10,
    verbose=True
)

# Check results
print(f"Success rate: {result.success_rate}%")
print(f"Avg response time: {result.avg_duration_ms}ms")
print(f"Total requests: {result.total_requests}")

# Save results
replayer.save_result(result, 'replay-results.json')
```

### Variable Substitution

```python
from src.tracetap.replay import TrafficReplayer

replayer = TrafficReplayer('session.json')

# Define variables for substitution
variables = {
    'user_id': '12345',
    'auth_token': 'abc123xyz',
    'environment': 'staging'
}

# Replay with variables
result = replayer.replay(
    target_base_url='http://localhost:8080',
    variables=variables
)
```

### Filtering Requests

```python
from src.tracetap.replay import TrafficReplayer

replayer = TrafficReplayer('session.json')

# Only replay GET and POST requests
result = replayer.replay(
    target_base_url='http://localhost:8080',
    request_filter=lambda req: req['method'] in ['GET', 'POST']
)

# Only replay requests to /api/users
result = replayer.replay(
    target_base_url='http://localhost:8080',
    request_filter=lambda req: '/api/users' in req['url']
)
```

---

## Mock Server

### Start Mock Server

```python
from src.tracetap.mock import MockServer, MockConfig

# Configure server
config = MockConfig(
    host='0.0.0.0',
    port=8080,
    matching_strategy='fuzzy',  # or 'exact', 'pattern', 'semantic'
)

# Create server
server = MockServer('session.json', config=config)

# Start (blocking)
server.start()

# Or get app for custom deployment
app = server.get_app()
# Use with: uvicorn app:app --host 0.0.0.0 --port 8080
```

### With Chaos Engineering

```python
from src.tracetap.mock import MockServer, MockConfig

config = MockConfig(
    port=8080,
    matching_strategy='fuzzy',
    chaos_enabled=True,
    chaos_failure_rate=0.1,  # 10% failures
    chaos_error_status=503,   # Service Unavailable
    add_delay_ms=100          # 100ms delay
)

server = MockServer('session.json', config=config)
server.start()
```

### Request Matching

```python
from src.tracetap.mock import RequestMatcher
import json

# Load captures
with open('session.json') as f:
    data = json.load(f)

# Create matcher
matcher = RequestMatcher(
    captures=data['requests'],
    strategy='fuzzy',
    min_score=0.7
)

# Find match for request
result = matcher.find_match(
    method='GET',
    url='https://api.example.com/users/123',
    headers={'Authorization': 'Bearer token'},
    body=None
)

if result.matched:
    print(f"Match found! Score: {result.score.total_score}")
    print(f"Matched URL: {result.capture['url']}")
    print(f"Response: {result.capture['response']}")
else:
    print("No match found")
```

### Response Generation

```python
from src.tracetap.mock import ResponseGenerator
import os

# Create generator with AI
generator = ResponseGenerator(
    use_ai=True,
    api_key=os.getenv('ANTHROPIC_API_KEY')
)

# Generate intelligent response based on context
response = generator.generate_intelligent(
    capture=matched_capture,
    request_context={
        'method': 'GET',
        'url': 'https://api.example.com/users/123',
        'user_id': '123'
    },
    intent="Return user profile with all fields"
)

print(response['status'])
print(response['headers'])
print(response['body'])
```

### Response Transformers

```python
from src.tracetap.mock import ResponseGenerator
import json
from datetime import datetime

generator = ResponseGenerator()

# Built-in transformers
from src.tracetap.mock import (
    add_timestamp_transformer,
    cors_headers_transformer,
    pretty_json_transformer
)

generator.add_transformer(add_timestamp_transformer)
generator.add_transformer(cors_headers_transformer)
generator.add_transformer(pretty_json_transformer)

# Custom transformer
def add_version_transformer(response, context):
    """Add API version to response"""
    body = json.loads(response['resp_body'])
    body['api_version'] = '2.0'
    body['generated_at'] = datetime.now().isoformat()
    response['resp_body'] = json.dumps(body)
    return response

generator.add_transformer(add_version_transformer)
```

---

## Variable Extraction

### Basic Extraction

```python
from src.tracetap.replay import VariableExtractor
import json

# Load captures
with open('session.json') as f:
    data = json.load(f)

# Extract without AI (regex-based)
extractor = VariableExtractor(
    captures=data['requests'],
    use_ai=False
)

variables = extractor.extract_variables(verbose=True)

for var in variables:
    print(f"{var.name}: {var.type}")
    print(f"  Examples: {var.example_values}")
    print(f"  Locations: {var.locations}")
    print(f"  Pattern: {var.pattern}")
```

### AI-Powered Extraction

```python
from src.tracetap.replay import VariableExtractor
import os

# Extract with Claude AI
extractor = VariableExtractor(
    captures=data['requests'],
    use_ai=True,
    api_key=os.getenv('ANTHROPIC_API_KEY')
)

variables = extractor.extract_variables(verbose=True)

# Save to file
with open('variables.json', 'w') as f:
    json.dump(
        [v.__dict__ for v in variables],
        f,
        indent=2
    )
```

### Custom Variable Detection

```python
from src.tracetap.replay import VariableExtractor

class CustomExtractor(VariableExtractor):
    """Custom variable extraction logic"""

    def extract_variables(self, verbose=False):
        variables = super().extract_variables(verbose)

        # Add custom variable patterns
        for capture in self.captures:
            url = capture.get('url', '')

            # Custom: extract API version
            import re
            match = re.search(r'/v(\d+)/', url)
            if match:
                self._add_variable('api_version', match.group(1), 'version')

        return variables

extractor = CustomExtractor(captures=data['requests'])
variables = extractor.extract_variables()
```

---

## Test Generation

### Playwright Test Generation

```python
from src.tracetap.playwright import PlaywrightGenerator
import json

with open('session.json') as f:
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

### Postman Collection Generation

```python
from src.tracetap.playwright import PostmanGenerator
import json

with open('session.json') as f:
    data = json.load(f)

# Create generator
generator = PostmanGenerator(
    captures=data['requests'],
    collection_name='My API',
    description='API collection from traffic'
)

# Generate collection
collection = generator.generate()

# Save
with open('postman.json', 'w') as f:
    json.dump(collection, f, indent=2)
```

---

## Contract Management

### Create Contract

```python
from src.tracetap.contract import ContractCreator
import json

with open('api.json') as f:
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
    print(f"✓ All {result.total} interactions verified")
else:
    print(f"✗ {result.failed} / {result.total} failed:")
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

### Verify Specific Interaction

```python
from src.tracetap.contract import ContractVerifier
import json

with open('contract.json') as f:
    contract = json.load(f)

verifier = ContractVerifier(contract)

# Verify single interaction
for interaction in contract['interactions']:
    result = verifier.verify_interaction(
        interaction,
        base_url='http://localhost:3000',
        verbose=True
    )

    if result.passed:
        print(f"✓ {interaction['description']}")
    else:
        print(f"✗ {interaction['description']}")
        print(f"  Expected: {result.expected}")
        print(f"  Got: {result.actual}")
```

---

## Advanced Patterns

### Custom Request Processing

```python
from src.tracetap.replay import TrafficReplayer

class CustomReplayer(TrafficReplayer):
    """Custom replay with preprocessing"""

    def process_request(self, request):
        """Modify request before sending"""
        # Remove sensitive headers
        if 'Authorization' in request.get('headers', {}):
            request['headers']['Authorization'] = 'Bearer REDACTED'

        # Update host
        request['url'] = request['url'].replace(
            'https://api.production.com',
            'http://localhost:8080'
        )

        return request

replayer = CustomReplayer('session.json')
result = replayer.replay(target_base_url='http://localhost:8080')
```

### Conditional Matching

```python
from src.tracetap.mock import RequestMatcher

def custom_strategy(request, capture):
    """Custom matching logic"""
    # Match if method and path prefix match
    if request['method'] != capture['method']:
        return 0.0

    if not request['url'].startswith(capture['url'].split('?')[0]):
        return 0.0

    # Custom scoring
    return 0.8

matcher = RequestMatcher(
    captures=data['requests'],
    strategy='custom',
    custom_function=custom_strategy
)
```

---

## Next Steps

- **[CLI Reference](cli-reference.md)** - Command-line tools
- **[Guides](../guides/)** - Learn workflows
