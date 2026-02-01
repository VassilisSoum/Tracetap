# Contract Testing with TraceTap

Ensure API providers and consumers stay in sync. Use contracts to prevent breaking changes before they happen.

## Table of Contents

- [Overview](#overview)
- [How Contract Testing Works](#how-contract-testing-works)
- [Getting Started](#getting-started)
- [Creating Contracts](#creating-contracts)
- [Verifying Contracts](#verifying-contracts)
- [CI/CD Integration](#cicd-integration)
- [Real-World Examples](#real-world-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

Contract testing solves a critical problem in microservices:

**The Problem:**
- Service A depends on Service B's API
- Service B team deploys a breaking change
- Service A breaks in production
- Nobody caught this before deployment

**The Solution:**
- Create a "contract" (agreed API spec) between services
- Verify contracts automatically in CI/CD
- Catch breaking changes before deployment

### What is a Contract?

A contract defines:
- ✅ What requests should look like
- ✅ What responses will be returned
- ✅ Required fields
- ✅ Data types
- ✅ Error scenarios

### Why It Matters

**Without contracts:**
```
Service A                    Service B
(Consumer)                   (Provider)
  │                            │
  └──→ GET /users/123 ────────┐
       Expected: {id, name}    │
                               │ ← Developer adds "email" field
                               │
       Gets: {id, name, email} │
       ← Breaking change! A wasn't expecting "email"
```

**With contracts:**
```
Service A                    Service B
(Consumer)                   (Provider)
  │ Contract                   │
  │ {id, name}               │
  │ (agreed spec)             │
  │                           │
  └─ "I will send: GET /users/123"
  │  "I expect: {id, name}"
  │                           │
  │ Contract verified?        │
  │ └─ YES: Safe to deploy ✓  │
```

---

## How Contract Testing Works

### Three-Part Process

```
Part 1: CREATE
┌─────────────────────────────────────────┐
│ Consumer and Provider agree on contract │
│ Create: contract.json                   │
└─────────────────────────────────────────┘
        │
        ▼
Part 2: VERIFY (Provider Side)
┌──────────────────────────────────────────┐
│ Provider verifies they honor the contract│
│ pytest tests/contract_verification.py    │
│ Result: PASS / FAIL                      │
└──────────────────────────────────────────┘
        │
        ▼
Part 3: VALIDATE (Consumer Side)
┌─────────────────────────────────────────┐
│ Consumer validates provider still honors │
│ contract after deployment                │
│ pytest tests/contract_validation.py      │
│ Result: PASS / FAIL                      │
└─────────────────────────────────────────┘
```

### Contract File Structure

```json
{
  "name": "User API Contract",
  "version": "1.0.0",
  "provider": "user-service",
  "consumer": "web-app",
  "interactions": [
    {
      "description": "Get user by ID",
      "request": {
        "method": "GET",
        "path": "/api/users/{id}",
        "pathParameters": {
          "id": {
            "type": "integer",
            "example": 123
          }
        }
      },
      "response": {
        "status": 200,
        "headers": {
          "Content-Type": "application/json"
        },
        "body": {
          "id": {
            "type": "integer",
            "required": true
          },
          "name": {
            "type": "string",
            "required": true
          },
          "email": {
            "type": "string",
            "required": true
          }
        }
      }
    }
  ]
}
```

---

## Getting Started

### Step 1: Capture Traffic from Provider

Have the provider capture their API traffic:

```bash
# Provider team
python tracetap.py --listen 8080 --export provider-api.json

# Exercise the API
export HTTP_PROXY=http://localhost:8080
curl -k https://api.example.com/users
curl -k https://api.example.com/users/123
curl -k -X POST https://api.example.com/users -d '{"name":"Bob","email":"bob@example.com"}'
```

### Step 2: Create Contract from Captures

Generate a contract from the captured traffic:

```bash
# Create contract
python -c "
from src.tracetap.contract import ContractCreator
import json

with open('provider-api.json') as f:
    captures = json.load(f)

creator = ContractCreator(
    provider='user-service',
    consumer='web-app'
)

contract = creator.create_from_captures(captures['requests'])

with open('contract.json', 'w') as f:
    json.dump(contract, f, indent=2)

print('✓ Contract created: contract.json')
"
```

Result: `contract.json` contains the agreed spec.

### Step 3: Commit Contract to Shared Location

```bash
# Share contract between teams
git add contract.json
git commit -m "Add API contract for user-service"
git push

# Other team checks it out
git pull
```

### Step 4: Provider Verifies Contract

Provider team ensures they honor the contract:

```bash
python -c "
from src.tracetap.contract import ContractVerifier
import json

with open('contract.json') as f:
    contract = json.load(f)

verifier = ContractVerifier(contract)

# Verify against running provider
result = verifier.verify(
    base_url='http://localhost:3000'
)

if result.passed:
    print(f'✓ All {result.total} interactions verified')
else:
    print(f'✗ {result.failed} / {result.total} interactions failed')
    for failure in result.failures:
        print(f'  - {failure}')
"
```

---

## Creating Contracts

### Method 1: From Captured Traffic

Generate automatically from traffic:

```bash
python -c "
from src.tracetap.contract import ContractCreator
import json

with open('api.json') as f:
    captures = json.load(f)

creator = ContractCreator(
    provider='my-service',
    consumer='client-app',
    base_url='https://api.example.com'
)

contract = creator.create_from_captures(
    captures['requests'],
    extract_parameters=True  # Auto-detect {id} in paths
)

with open('contract.json', 'w') as f:
    json.dump(contract, f, indent=2)
"
```

### Method 2: Manual Creation

Write contracts explicitly:

```json
{
  "name": "User Service Contract",
  "version": "1.0.0",
  "provider": "user-service",
  "consumer": "web-app",
  "interactions": [
    {
      "id": "get-user",
      "description": "Retrieve a user by ID",
      "request": {
        "method": "GET",
        "path": "/api/users/{id}",
        "pathParameters": {
          "id": {
            "type": "integer",
            "example": 123
          }
        }
      },
      "response": {
        "status": 200,
        "headers": {
          "Content-Type": "application/json"
        },
        "body": {
          "type": "object",
          "required": ["id", "name", "email"],
          "properties": {
            "id": {
              "type": "integer",
              "description": "User ID"
            },
            "name": {
              "type": "string",
              "description": "User full name"
            },
            "email": {
              "type": "string",
              "format": "email",
              "description": "User email address"
            }
          }
        }
      }
    },
    {
      "id": "create-user",
      "description": "Create a new user",
      "request": {
        "method": "POST",
        "path": "/api/users",
        "headers": {
          "Content-Type": "application/json"
        },
        "body": {
          "type": "object",
          "required": ["name", "email"],
          "properties": {
            "name": {
              "type": "string"
            },
            "email": {
              "type": "string",
              "format": "email"
            }
          }
        }
      },
      "response": {
        "status": 201,
        "body": {
          "type": "object",
          "required": ["id", "name", "email"],
          "properties": {
            "id": {
              "type": "integer"
            },
            "name": {
              "type": "string"
            },
            "email": {
              "type": "string"
            }
          }
        }
      }
    }
  ]
}
```

---

## Verifying Contracts

### Provider Verification

Provider team ensures their API matches the contract:

```bash
# Create test file that verifies contract
python -c "
from src.tracetap.contract import ContractVerifier
import json

with open('contract.json') as f:
    contract = json.load(f)

verifier = ContractVerifier(contract)

# Test each interaction
for interaction in contract['interactions']:
    result = verifier.verify_interaction(
        interaction,
        base_url='http://localhost:3000'
    )

    if result.passed:
        print(f'✓ {interaction[\"description\"]}')
    else:
        print(f'✗ {interaction[\"description\"]}')
        print(f'  Error: {result.error}')
"
```

### Generated Verification Tests

Auto-generate test file from contract:

```bash
python -c "
from src.tracetap.contract import ContractVerifier
import json

with open('contract.json') as f:
    contract = json.load(f)

verifier = ContractVerifier(contract)

# Generate test file
test_code = verifier.generate_tests(
    language='python',
    framework='pytest',
    base_url='http://localhost:3000'
)

with open('tests/test_contract.py', 'w') as f:
    f.write(test_code)
"
```

Generated test file:

```python
import pytest
import requests

BASE_URL = 'http://localhost:3000'

class TestUserServiceContract:
    \"\"\"Contract verification tests for User Service\"\"\"

    def test_get_user_by_id(self):
        \"\"\"Verify: Get user by ID\"\"\"
        response = requests.get(f'{BASE_URL}/api/users/123')

        assert response.status_code == 200
        assert 'Content-Type' in response.headers

        data = response.json()
        assert 'id' in data
        assert 'name' in data
        assert 'email' in data
        assert isinstance(data['id'], int)
        assert isinstance(data['name'], str)
        assert isinstance(data['email'], str)

    def test_create_user(self):
        \"\"\"Verify: Create a new user\"\"\"
        response = requests.post(
            f'{BASE_URL}/api/users',
            json={
                'name': 'Test User',
                'email': 'test@example.com'
            }
        )

        assert response.status_code == 201

        data = response.json()
        assert 'id' in data
        assert 'name' in data
        assert 'email' in data
```

Run the tests:

```bash
pytest tests/test_contract.py -v
```

---

## CI/CD Integration

### GitHub Actions

Provider verifies contract with every deploy:

```yaml
# .github/workflows/contract-verification.yml
name: Contract Verification

on: [push, pull_request]

jobs:
  verify-contract:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Start service
        run: |
          python -m pytest --setup-only
          python service.py &

      - name: Verify contract
        run: |
          python -c "
          from src.tracetap.contract import ContractVerifier
          import json

          with open('contract.json') as f:
              contract = json.load(f)

          verifier = ContractVerifier(contract)
          result = verifier.verify(base_url='http://localhost:3000')

          if not result.passed:
              exit(1)
          "

      - name: Report results
        if: always()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '✓ Contract verification passed'
            })
```

### Consumer Validation

Consumer validates the contract after provider deploys:

```yaml
# .github/workflows/contract-validation.yml
name: Contract Validation

on:
  workflow_run:
    workflows: ["provider-deployment"]
    types: [completed]

jobs:
  validate-contract:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Validate contract
        env:
          PROVIDER_URL: https://api.example.com
        run: |
          python -c "
          from src.tracetap.contract import ContractValidator
          import json

          with open('contract.json') as f:
              contract = json.load(f)

          validator = ContractValidator(contract)
          result = validator.validate(
              base_url=os.getenv('PROVIDER_URL')
          )

          if not result.passed:
              print(f'✗ Contract validation failed:')
              for failure in result.failures:
                  print(f'  - {failure}')
              exit(1)

          print('✓ Contract validation passed')
          "

      - name: Run consumer tests
        if: success()
        run: pytest tests/
```

---

## Real-World Examples

### Example 1: Microservices Coordination

Three services need to coordinate:

```
Service A (Orders)  →  Service B (Payments)
Service A (Orders)  →  Service C (Inventory)
```

Create contracts:

```bash
# orders-to-payments-contract.json
{
  "provider": "payments-service",
  "consumer": "orders-service",
  "interactions": [
    {
      "description": "Process payment",
      "request": {
        "method": "POST",
        "path": "/api/payments",
        "body": {
          "required": ["order_id", "amount", "currency"]
        }
      },
      "response": {
        "status": 201,
        "body": {
          "required": ["payment_id", "status", "timestamp"]
        }
      }
    }
  ]
}

# orders-to-inventory-contract.json
{
  "provider": "inventory-service",
  "consumer": "orders-service",
  "interactions": [
    {
      "description": "Check stock",
      "request": {
        "method": "GET",
        "path": "/api/items/{id}/stock"
      },
      "response": {
        "status": 200,
        "body": {
          "required": ["item_id", "quantity"]
        }
      }
    }
  ]
}
```

Each service verifies their contracts:

```bash
# In payments-service repo
pytest tests/contract_verification.py

# In inventory-service repo
pytest tests/contract_verification.py
```

If any service breaks the contract, CI/CD fails before deployment.

### Example 2: Versioned APIs

Support multiple API versions with contracts:

```
contract-v1.json  (supports old clients)
contract-v2.json  (supports new clients)
contract-v3.json  (latest version)
```

Provider verifies all versions:

```bash
for version in 1 2 3; do
  python -c "
  from src.tracetap.contract import ContractVerifier
  import json

  with open(f'contract-v{version}.json') as f:
      contract = json.load(f)

  verifier = ContractVerifier(contract)
  result = verifier.verify(base_url='http://localhost:3000')

  if not result.passed:
      print(f'✗ Version {version} broken')
      exit(1)

  print(f'✓ Version {version} verified')
  "
done
```

---

## Best Practices

### 1. Keep Contracts Simple

Focus on what matters:

```json
{
  "request": {
    "method": "GET",
    "path": "/api/users/{id}"
  },
  "response": {
    "status": 200,
    "body": {
      "type": "object",
      "required": ["id", "name", "email"],
      "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "email": {"type": "string"}
      }
    }
  }
}
```

Don't over-specify:

```json
{
  "response": {
    "body": {
      "type": "object",
      "required": ["id", "name", "email", "created_at"],
      "properties": {
        "id": {
          "type": "integer",
          "minimum": 1,
          "maximum": 9223372036854775807,
          "multipleOf": 1
        },
        "name": {
          "type": "string",
          "minLength": 1,
          "maxLength": 255,
          "pattern": "^[a-zA-Z ]+$"  // ❌ Too specific!
        }
      }
    }
  }
}
```

### 2. Version Your Contracts

```bash
# Use semantic versioning
contract-1.0.0.json  # Initial version
contract-1.1.0.json  # Added optional field
contract-2.0.0.json  # Removed field (breaking change)
```

Document what changed:

```json
{
  "version": "2.0.0",
  "changelog": {
    "breaking_changes": [
      "Removed 'deprecated_field' - migrate to 'new_field'"
    ],
    "additions": [
      "Added optional 'metadata' object"
    ]
  }
}
```

### 3. Test Breaking Changes Early

When you want to break a contract:

```bash
# 1. Create new contract version
contract-2.0.0.json

# 2. Update your service to honor both versions
# (Gradual migration)

# 3. Update consumers (version contract)
# 4. Migrate all consumers to new version
# 5. Deprecate old version
# 6. Remove old version

# Only then deploy the breaking change
```

### 4. Document Why Contracts Exist

Include context:

```json
{
  "name": "User API Contract",
  "version": "1.0.0",
  "description": "Contract between orders-service and user-service",
  "context": "The orders service needs to fetch user data to validate addresses and payment methods",
  "interactions": [...]
}
```

---

## Troubleshooting

### Contract Verification Fails

**Problem**: Provider tests fail against contract

**Solution**:
```bash
# 1. Debug which interaction fails
python -c "
from src.tracetap.contract import ContractVerifier
import json

with open('contract.json') as f:
    contract = json.load(f)

verifier = ContractVerifier(contract)

for interaction in contract['interactions']:
    result = verifier.verify_interaction(
        interaction,
        base_url='http://localhost:3000',
        verbose=True
    )
    if not result.passed:
        print(f'Failed: {interaction[\"description\"]}')
        print(f'Expected: {result.expected}')
        print(f'Got: {result.actual}')
"

# 2. Fix your service to match the contract
# 3. Re-verify
```

### Consumers See Different Behavior

**Problem**: Contract says GET /users returns `{id, name, email}` but sometimes missing `email`

**Solution**:
- Make the field explicitly optional in contract
- Or ensure your service always returns it
- Update contract if behavior actually changed

### Contract Too Restrictive

**Problem**: Contract prevents needed API evolution

**Solution**:
- Create new contract version (v2.0.0)
- Document migration path for consumers
- Give consumers time to upgrade
- Deprecate old version after transition

---

## Next Steps

- **[CI/CD Integration](../guides/ci-cd-integration.md)** - Automate contract verification
- **[Regression Testing](regression-testing.md)** - Combine with regression tests
- **[Troubleshooting](../troubleshooting.md)** - Common contract issues
