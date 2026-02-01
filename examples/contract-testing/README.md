# Contract Testing in CI/CD with TraceTap

This example demonstrates how to implement API contract testing in your CI/CD pipeline using TraceTap's contract verification capabilities.

## Overview

Contract testing ensures your API maintains backward compatibility by:
1. Establishing a baseline contract (OpenAPI specification)
2. Detecting breaking changes before deployment
3. Blocking PRs that introduce incompatible changes
4. Generating detailed diff reports

## What is Contract Testing?

**Contract testing** verifies that an API adheres to a defined specification (contract). When the API changes, the contract verifier detects:

- **Breaking changes**: Removed endpoints, changed types, removed required fields
- **Warnings**: Changed optional fields, new required fields
- **Info**: New endpoints, new optional fields

## Directory Structure

```
contract-testing/
├── README.md                    # This file
├── contracts/
│   ├── baseline.yaml           # Baseline OpenAPI contract
│   └── current.yaml            # Current contract (for comparison)
├── captured-traffic/
│   └── api-traffic.json        # Captured API traffic
├── ci-cd/
│   ├── github-actions.yml      # GitHub Actions workflow
│   ├── gitlab-ci.yml           # GitLab CI pipeline
│   └── jenkins.groovy          # Jenkins pipeline
├── scripts/
│   ├── capture-contract.sh     # Capture and create contract
│   └── verify-contract.sh      # Verify contract compatibility
└── reports/
    └── (generated diff reports)
```

## Quick Start

### Step 1: Establish Baseline Contract

First, capture your API traffic and generate a baseline contract:

```bash
# Start TraceTap proxy
python tracetap.py --listen 8080 \
    --raw-log api-traffic.json \
    --filter-host "api.example.com"

# Run your test suite through the proxy
export HTTP_PROXY=http://localhost:8080
./run-integration-tests.sh

# Stop proxy (Ctrl+C)
```

Generate the baseline contract:

```bash
python tracetap-replay.py create-contract \
    api-traffic.json \
    -o contracts/baseline.yaml \
    --title "My API" \
    --version "1.0.0"
```

### Step 2: Verify Changes

After API modifications, verify compatibility:

```bash
# Capture new traffic
python tracetap.py --listen 8080 --raw-log new-traffic.json

# Generate current contract
python tracetap-replay.py create-contract \
    new-traffic.json \
    -o contracts/current.yaml

# Verify compatibility
python tracetap-replay.py verify-contract \
    contracts/baseline.yaml \
    contracts/current.yaml \
    --fail-on-breaking
```

### Step 3: Integrate with CI/CD

Copy the appropriate workflow file to your repository:

**GitHub Actions:**
```bash
cp examples/contract-testing/ci-cd/github-actions.yml .github/workflows/contract-test.yml
```

**GitLab CI:**
```bash
cp examples/contract-testing/ci-cd/gitlab-ci.yml .gitlab-ci.yml
```

## Breaking Change Detection

TraceTap detects these types of breaking changes:

| Change Type | Severity | Example |
|-------------|----------|---------|
| Removed endpoint | BREAKING | `DELETE /api/v1/users` removed |
| Removed operation | BREAKING | `PUT /users/{id}` removed |
| Changed type | BREAKING | `id: string` changed to `id: number` |
| Removed required field | BREAKING | `email` field removed from response |
| New required field | BREAKING | New required `api_key` in request |
| Removed optional field | WARNING | `nickname` field removed |
| Changed optional field | WARNING | `age: string` changed to `age: number` |
| New endpoint | INFO | `POST /api/v2/users` added |
| New optional field | INFO | New `avatar` field in response |

## Contract Verification Output

### Text Format

```
Contract Changes:
==================================================

BREAKING CHANGES (2):
--------------------------------------------------
  - DELETE /users/{id}
    Operation removed: DELETE /users/{id}
  - GET /users / response 200 / email
    Property made required: email

WARNINGS (1):
--------------------------------------------------
  - GET /users / response 200 / nickname
    Property removed: nickname (optional)

INFO (3):
--------------------------------------------------
  - POST /users/v2
    New endpoint added: POST /users/v2

Summary: 2 breaking, 1 warnings, 3 info
```

### JSON Format

```json
[
  {
    "severity": "BREAKING",
    "category": "operation",
    "path": "DELETE /users/{id}",
    "message": "Operation removed: DELETE /users/{id}",
    "old_value": "delete"
  }
]
```

### Markdown Format

```markdown
# Contract Changes

**Summary:** 2 breaking, 1 warnings, 3 info

## BREAKING Changes

- **DELETE /users/{id}**
  - Operation removed: DELETE /users/{id}
```

## CI/CD Workflows

### GitHub Actions

```yaml
name: Contract Testing

on:
  pull_request:
    branches: [main]

jobs:
  contract-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install TraceTap
        run: pip install tracetap

      - name: Start API Server
        run: |
          ./start-api.sh &
          sleep 5

      - name: Capture Traffic
        run: |
          python tracetap.py --listen 8080 \
            --raw-log traffic.json &
          sleep 2

          # Run test suite through proxy
          HTTP_PROXY=http://localhost:8080 ./test-suite.sh

          pkill -f tracetap

      - name: Generate Contract
        run: |
          python tracetap-replay.py create-contract \
            traffic.json -o current.yaml

      - name: Verify Contract
        run: |
          python tracetap-replay.py verify-contract \
            contracts/baseline.yaml current.yaml \
            --fail-on-breaking

      - name: Comment on PR
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: 'Breaking API changes detected! Please review contract verification report.'
            })
```

### GitLab CI

```yaml
stages:
  - test
  - contract

contract-verification:
  stage: contract
  image: python:3.11
  script:
    - pip install tracetap
    - ./start-api.sh &
    - sleep 5
    - |
      python tracetap.py --listen 8080 --raw-log traffic.json &
      sleep 2
      HTTP_PROXY=http://localhost:8080 ./test-suite.sh
      pkill -f tracetap
    - python tracetap-replay.py create-contract traffic.json -o current.yaml
    - python tracetap-replay.py verify-contract contracts/baseline.yaml current.yaml --fail-on-breaking
  artifacts:
    when: always
    paths:
      - current.yaml
      - contract-diff.md
  only:
    - merge_requests
```

## Best Practices

### 1. Version Your Contracts

Store contracts with version information:

```
contracts/
├── v1.0.0/
│   └── api.yaml
├── v1.1.0/
│   └── api.yaml
└── baseline.yaml -> v1.1.0/api.yaml
```

### 2. Allow Intentional Breaking Changes

For major version bumps, update the baseline:

```bash
# For major version bump (intentional breaking changes)
python tracetap-replay.py create-contract \
    traffic.json \
    -o contracts/v2.0.0/api.yaml \
    --title "My API" \
    --version "2.0.0"

# Update baseline symlink
ln -sf v2.0.0/api.yaml contracts/baseline.yaml
```

### 3. Generate Reports for PRs

```bash
python tracetap-replay.py verify-contract \
    baseline.yaml current.yaml \
    --output contract-diff.md \
    --format markdown
```

### 4. Test Multiple Environments

```yaml
strategy:
  matrix:
    environment: [staging, production]

steps:
  - name: Verify Contract
    run: |
      python tracetap-replay.py verify-contract \
        contracts/baseline.yaml \
        contracts/${{ matrix.environment }}.yaml \
        --fail-on-breaking
```

## Troubleshooting

### Contract verification fails unexpectedly

1. Check if changes are intentional
2. Review the diff report
3. Update baseline if changes are approved

```bash
# View detailed diff
python tracetap-replay.py verify-contract \
    baseline.yaml current.yaml \
    --format text
```

### Missing endpoints in contract

Ensure test coverage includes all endpoints:

```bash
# Check coverage
cat current.yaml | grep "  /.*:" | sort
```

### Type inference issues

TraceTap infers types from traffic. Ensure diverse test data:

```bash
# Multiple values for each field type
curl http://api/users/1  # numeric ID
curl http://api/users/abc  # string ID (if supported)
```

## Next Steps

- See the [E-commerce Example](../ecommerce-api/) for full workflow testing
- Explore the [Regression Suite Example](../regression-suite/) for automated testing
- Read the main [TraceTap documentation](../../README.md)
