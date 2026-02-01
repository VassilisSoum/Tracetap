# CI/CD Integration Guide

Automate traffic capture, test generation, and validation in your CI/CD pipeline.

## Table of Contents

- [Overview](#overview)
- [GitHub Actions](#github-actions)
- [GitLab CI](#gitlab-ci)
- [Generic CI/CD](#generic-cicd)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

---

## Overview

Integrate TraceTap into your CI/CD to:

- ✅ Run regression tests on every deployment
- ✅ Verify API contracts before releasing
- ✅ Capture traffic from staging environment
- ✅ Generate tests automatically
- ✅ Detect breaking changes before production

### Basic Pipeline

```
1. Code Push
   │
   ▼
2. Start Mock API / Real API
   │
   ▼
3. Run TraceTap Capture (if new baseline)
   │
   ▼
4. Generate Tests from Baseline
   │
   ▼
5. Run Tests
   │
   ▼
6. Run Contract Verification
   │
   ▼
7. Deploy (if all pass)
```

---

## GitHub Actions

### Regression Test Workflow

Create `.github/workflows/regression-tests.yml`:

```yaml
name: Regression Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    # Run daily at 2 AM UTC
    - cron: '0 2 * * *'

jobs:
  regression-tests:
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

      - name: Start API server
        run: |
          python -m pytest --setup-only
          python api_server.py &
          sleep 2  # Wait for server to start

      - name: Run regression tests
        run: |
          pytest tests/ --junitxml=results.xml

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: results.xml

      - name: Publish test results
        if: always()
        uses: dorny/test-reporter@v1
        with:
          name: Regression Tests
          path: 'results.xml'
          reporter: 'java-junit'
```

### Contract Verification Workflow

Create `.github/workflows/contract-verification.yml`:

```yaml
name: Contract Verification

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

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

      - name: Start API server
        run: |
          python api_server.py &
          sleep 2

      - name: Verify contract
        run: |
          python -c "
          from src.tracetap.contract import ContractVerifier
          import json
          import sys

          with open('contract.json') as f:
              contract = json.load(f)

          verifier = ContractVerifier(contract)
          result = verifier.verify(base_url='http://localhost:3000')

          if not result.passed:
              print(f'✗ {result.failed} failures')
              for failure in result.failures:
                  print(f'  - {failure}')
              sys.exit(1)

          print(f'✓ All {result.total} interactions verified')
          "

      - name: Report status
        if: always()
        uses: actions/github-script@v6
        with:
          script: |
            if ('${{ job.status }}' === 'success') {
              github.rest.issues.createComment({
                issue_number: context.issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                body: '✓ Contract verification passed'
              })
            } else {
              github.rest.issues.createComment({
                issue_number: context.issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                body: '✗ Contract verification failed'
              })
            }
```

### Test Generation on New API Changes

Create `.github/workflows/test-generation.yml`:

```yaml
name: Generate Tests from Changes

on:
  push:
    branches: [main]
    paths:
      - 'api/**'
      - 'src/**'

jobs:
  generate-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Start API server
        run: |
          python api_server.py &
          sleep 2

      - name: Capture baseline traffic
        run: |
          python tracetap.py --listen 8080 --export baseline.json &
          TRACETAP_PID=$!

          # Exercise API
          sleep 2
          curl -x http://localhost:8080 https://api.example.com/users
          curl -x http://localhost:8080 https://api.example.com/users/123

          # Stop capture
          kill $TRACETAP_PID
          wait $TRACETAP_PID 2>/dev/null || true

      - name: Generate tests
        run: |
          python tracetap-playwright.py baseline.json -o tests/generated/

      - name: Create pull request
        if: github.event_name == 'push'
        uses: peter-evans/create-pull-request@v4
        with:
          commit-message: 'chore: regenerate tests from API baseline'
          title: 'Update auto-generated tests'
          body: 'Tests regenerated from API baseline'
          branch: auto-update-tests
```

---

## GitLab CI

### Basic Regression Tests

Create `.gitlab-ci.yml`:

```yaml
stages:
  - test
  - verify
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip

regression-tests:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt -r requirements-dev.txt
    - python api_server.py &
    - sleep 2
    - pytest tests/ --junitxml=results.xml
  artifacts:
    reports:
      junit: results.xml
  only:
    - main
    - develop
    - merge_requests

contract-verification:
  stage: verify
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - python api_server.py &
    - sleep 2
    - python -c "
      from src.tracetap.contract import ContractVerifier
      import json
      import sys

      with open('contract.json') as f:
          contract = json.load(f)

      verifier = ContractVerifier(contract)
      result = verifier.verify(base_url='http://localhost:3000')

      if not result.passed:
          for failure in result.failures:
              print(f'✗ {failure}')
          sys.exit(1)

      print(f'✓ Contract verified')
      "
  only:
    - main
    - merge_requests

deploy:
  stage: deploy
  script:
    - ./deploy.sh
  only:
    - main
  dependencies:
    - regression-tests
    - contract-verification
```

### With Artifacts

Store test results and coverage:

```yaml
regression-tests:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt -r requirements-dev.txt
    - pytest tests/ \
        --junitxml=results.xml \
        --cov=src/tracetap \
        --cov-report=html \
        --cov-report=term
  artifacts:
    reports:
      junit: results.xml
    paths:
      - htmlcov/
    expire_in: 1 week
```

---

## Generic CI/CD

### Docker-based CI/CD

```bash
#!/bin/bash
# ci.sh - Generic CI script

set -e

echo "Installing dependencies..."
pip install -r requirements.txt -r requirements-dev.txt

echo "Starting API server..."
python api_server.py &
SERVER_PID=$!
sleep 2

echo "Running tests..."
if ! pytest tests/ --junitxml=results.xml; then
    kill $SERVER_PID || true
    exit 1
fi

echo "Verifying contract..."
if ! python -c "
from src.tracetap.contract import ContractVerifier
import json, sys

with open('contract.json') as f:
    contract = json.load(f)

verifier = ContractVerifier(contract)
result = verifier.verify(base_url='http://localhost:3000')

if not result.passed:
    for failure in result.failures:
        print(f'✗ {failure}')
    sys.exit(1)
"; then
    kill $SERVER_PID || true
    exit 1
fi

kill $SERVER_PID || true

echo "✓ All checks passed"
```

Run in Docker:

```dockerfile
FROM python:3.11

WORKDIR /app

# Install dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt -r requirements-dev.txt

# Copy code
COPY . .

# Run CI script
CMD bash ci.sh
```

---

## Common Patterns

### Pattern 1: Staging Environment Testing

Test against staging after deployment:

```yaml
# GitHub Actions
name: Staging Verification

on:
  deployment:
    environment: staging

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run regression tests
        env:
          API_URL: https://staging-api.example.com
        run: pytest tests/ -v
```

### Pattern 2: Capture on Staging, Test Locally

```bash
#!/bin/bash

# 1. Capture from staging
python tracetap.py --listen 8080 \
  --filter-host staging-api.example.com \
  --export staging-capture.json &

sleep 2

# Point your app to proxy
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# Run test suite against staging
pytest tests/staging/

# 2. Generate local tests from staging capture
python tracetap-playwright.py staging-capture.json \
  -o tests/staging-generated/

# 3. Run generated tests against local mock
python tracetap2wiremock.py staging-capture.json \
  -o wiremock/mappings/staging.json

pytest tests/staging-generated/
```

### Pattern 3: Continuous Baseline Updates

Update test baseline when API intentionally changes:

```yaml
# GitHub Actions
name: Update Baseline

on:
  push:
    paths:
      - 'api/**.py'
      - 'src/api/**.py'

jobs:
  update-baseline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Start API
        run: python api_server.py &
      - name: Capture new baseline
        run: |
          python tracetap.py --listen 8080 --export baseline.json &
          sleep 2
          # Exercise API
          curl http://localhost:3000/api/users
          kill %1
      - name: Generate tests
        run: python tracetap-playwright.py baseline.json -o tests/
      - name: Create PR
        uses: peter-evans/create-pull-request@v4
        with:
          commit-message: 'chore: update baseline and tests'
          title: 'Update API baseline'
```

### Pattern 4: Multi-Environment Testing

Test against multiple environments:

```bash
#!/bin/bash

for env in staging production; do
    echo "Testing $env..."

    export API_URL="https://${env}-api.example.com"

    pytest tests/ \
        --junitxml="results-${env}.xml" \
        || exit 1

    echo "✓ $env passed"
done
```

---

## Troubleshooting

### Tests Timeout in CI

**Problem**: Tests pass locally but timeout in CI

**Solution**:
```yaml
# Increase timeout
pytest tests/ --timeout=30

# Or set in pytest.ini
[pytest]
timeout = 30
```

### API Server Startup Fails in CI

**Problem**: API server doesn't start before tests run

**Solution**:
```yaml
# Add health check
- name: Start API server
  run: |
    python api_server.py &
    sleep 5

    # Wait for health check
    for i in {1..30}; do
      curl http://localhost:3000/health && break
      sleep 1
    done
```

### Contract Verification Failures Not Reported

**Problem**: Contract failures don't fail the CI build

**Solution**:
```bash
# Ensure proper exit code
python -c "
from src.tracetap.contract import ContractVerifier
import json, sys

with open('contract.json') as f:
    contract = json.load(f)

result = ContractVerifier(contract).verify(
    base_url='http://localhost:3000'
)

# Exit with non-zero if failed
sys.exit(0 if result.passed else 1)
"
```

### Artifacts Not Found

**Problem**: Test results not uploaded

**Solution**:
```yaml
# Ensure files exist
- name: Check test results
  if: always()
  run: |
    ls -la results.xml || echo "No results file"

- name: Upload
  if: always() && hashFiles('results.xml') != ''
  uses: actions/upload-artifact@v3
```

---

## Next Steps

- **[Regression Testing](../features/regression-testing.md)** - Learn test structure
- **[Contract Testing](../features/contract-testing.md)** - Understand contract verification
- **[Capturing Traffic](capturing-traffic.md)** - How to capture for CI/CD
