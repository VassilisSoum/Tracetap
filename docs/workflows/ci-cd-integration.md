# CI/CD Integration Workflow

Complete guide for integrating TraceTap into continuous integration and deployment pipelines to ensure API compatibility and prevent breaking changes.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [GitHub Actions Integration](#github-actions-integration)
4. [GitLab CI Integration](#gitlab-ci-integration)
5. [Jenkins Integration](#jenkins-integration)
6. [Contract Verification](#contract-verification)
7. [Breaking Change Detection](#breaking-change-detection)
8. [Advanced Patterns](#advanced-patterns)
9. [Troubleshooting](#troubleshooting)

---

## Overview

TraceTap enables CI/CD integration for:

- **API contract verification** - Detect breaking changes before deployment
- **Automated test generation** - Generate regression tests from captured traffic
- **Traffic replay** - Validate API changes against production traffic
- **Baseline management** - Version control API contracts

**CI/CD Workflow:**
```
Code Push → Capture Traffic → Generate Contract → Verify Changes → Block/Allow Deploy
```

---

## Prerequisites

### Required Tools

```bash
# TraceTap
pip install tracetap

# For AI features
export ANTHROPIC_API_KEY='your-api-key'
```

### Required Artifacts

1. **Baseline contract** - OpenAPI spec from production/main branch
2. **Test suite** - Existing tests or Playwright tests
3. **API endpoint** - Running test/staging API

---

## GitHub Actions Integration

### Basic Contract Verification

Create `.github/workflows/api-contract-check.yml`:

```yaml
name: API Contract Verification

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

jobs:
  verify-api-contract:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install TraceTap
        run: |
          pip install tracetap
          tracetap --version

      - name: Download baseline contract
        run: |
          # Download from artifact storage or S3
          curl -o baseline-contract.yaml \
            https://your-storage.com/contracts/baseline.yaml

      - name: Start test API
        run: |
          # Start your API in background
          npm install
          npm run start:test &
          sleep 10

      - name: Capture current API traffic
        run: |
          # Start capture in background
          tracetap capture \
            --port 8080 \
            --session-name "ci-verification" \
            --export current-traffic.json &
          CAPTURE_PID=$!

          # Wait for proxy
          sleep 2

          # Run test suite through proxy
          HTTP_PROXY=http://localhost:8080 \
          HTTPS_PROXY=http://localhost:8080 \
            npm test

          # Stop capture
          kill $CAPTURE_PID

      - name: Generate current contract
        run: |
          tracetap contract create current-traffic.json \
            --output current-contract.yaml

      - name: Verify contract compatibility
        id: verify
        run: |
          tracetap contract verify \
            --baseline baseline-contract.yaml \
            --current current-contract.yaml \
            --output contract-diff.json \
            --fail-on-breaking

      - name: Upload contract diff
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: contract-diff
          path: contract-diff.json

      - name: Comment PR with changes
        if: failure() && github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const diff = JSON.parse(fs.readFileSync('contract-diff.json', 'utf8'));

            const breaking = diff.changes.filter(c => c.severity === 'BREAKING');
            const warnings = diff.changes.filter(c => c.severity === 'WARNING');

            let comment = '## ⚠️ API Contract Changes Detected\n\n';

            if (breaking.length > 0) {
              comment += '### 🚨 Breaking Changes\n\n';
              breaking.forEach(change => {
                comment += `- **${change.path}**: ${change.message}\n`;
              });
            }

            if (warnings.length > 0) {
              comment += '\n### ⚡ Warnings\n\n';
              warnings.forEach(change => {
                comment += `- **${change.path}**: ${change.message}\n`;
              });
            }

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

### Regression Test Generation

Create `.github/workflows/generate-tests.yml`:

```yaml
name: Generate Regression Tests

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  generate-tests:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          pip install tracetap
          npm install -D @playwright/test

      - name: Capture production-like traffic
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          # Start capture
          tracetap capture \
            --port 8080 \
            --session-name "production-baseline" \
            --export baseline-traffic.json &
          CAPTURE_PID=$!

          sleep 2

          # Run comprehensive test suite
          HTTP_PROXY=http://localhost:8080 \
          HTTPS_PROXY=http://localhost:8080 \
            npm run test:e2e

          kill $CAPTURE_PID

      - name: Generate Playwright tests
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          tracetap-playwright baseline-traffic.json \
            --output tests/regression/ \
            --ai

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          commit-message: 'Update regression tests from baseline traffic'
          title: 'chore: Update API regression tests'
          body: |
            Automated PR to update regression tests based on current API behavior.

            Generated from production-like traffic capture.
          branch: update-regression-tests
          delete-branch: true
```

### Parallel Contract + Test Execution

```yaml
name: API Verification Pipeline

on: [pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [staging, production]

    steps:
      - uses: actions/checkout@v3

      - name: Setup
        run: |
          pip install tracetap
          npm install

      - name: Capture & Verify
        env:
          API_URL: ${{ matrix.environment == 'production' && secrets.PROD_API_URL || secrets.STAGING_API_URL }}
        run: |
          # Replay production traffic to staging
          tracetap-replay.py replay production-baseline.json \
            --target $API_URL \
            --output replay-results.json \
            --fail-on-errors

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: replay-results-${{ matrix.environment }}
          path: replay-results.json
```

---

## GitLab CI Integration

### Basic Pipeline

Create `.gitlab-ci.yml`:

```yaml
stages:
  - build
  - test
  - verify
  - deploy

variables:
  TRACETAP_VERSION: "latest"
  BASELINE_CONTRACT: "contracts/baseline.yaml"

before_script:
  - pip install tracetap

# Generate baseline on main branch
generate_baseline:
  stage: test
  only:
    - main
  script:
    - tracetap capture --port 8080 --export baseline-traffic.json &
    - sleep 2
    - npm run test:integration
    - pkill -f tracetap
    - tracetap contract create baseline-traffic.json --output $BASELINE_CONTRACT
  artifacts:
    paths:
      - $BASELINE_CONTRACT
    expire_in: 30 days

# Verify changes on merge requests
verify_contract:
  stage: verify
  only:
    - merge_requests
  script:
    # Start API
    - npm run start:test &
    - sleep 5

    # Capture current traffic
    - tracetap capture --port 8080 --export current-traffic.json &
    - CAPTURE_PID=$!
    - sleep 2

    # Run tests through proxy
    - HTTP_PROXY=http://localhost:8080 npm test
    - kill $CAPTURE_PID

    # Generate current contract
    - tracetap contract create current-traffic.json --output current-contract.yaml

    # Verify compatibility
    - |
      tracetap contract verify \
        --baseline $BASELINE_CONTRACT \
        --current current-contract.yaml \
        --output contract-diff.json \
        --fail-on-breaking || EXIT_CODE=$?

    # Generate report
    - cat contract-diff.json | jq -r '.summary'

    - exit ${EXIT_CODE:-0}

  artifacts:
    when: always
    paths:
      - contract-diff.json
      - current-contract.yaml
    reports:
      junit: contract-diff.json

# Allow override on explicit approval
deploy_staging:
  stage: deploy
  when: manual
  only:
    - merge_requests
  script:
    - echo "Deploying to staging despite contract changes"
    - ./deploy-staging.sh
```

### Multi-Environment Validation

```yaml
verify_multi_env:
  stage: verify
  parallel:
    matrix:
      - ENVIRONMENT: [staging, production]
  script:
    - |
      # Replay to environment
      tracetap-replay.py replay baseline-traffic.json \
        --target $ENVIRONMENT_URL \
        --output replay-$ENVIRONMENT.json \
        --workers 10

      # Check success rate
      SUCCESS_RATE=$(cat replay-$ENVIRONMENT.json | jq -r '.success_rate')
      if (( $(echo "$SUCCESS_RATE < 95.0" | bc -l) )); then
        echo "Error: Success rate $SUCCESS_RATE% is below 95%"
        exit 1
      fi
  artifacts:
    paths:
      - replay-*.json
```

---

## Jenkins Integration

### Jenkinsfile for Contract Verification

```groovy
pipeline {
    agent any

    environment {
        ANTHROPIC_API_KEY = credentials('anthropic-api-key')
        BASELINE_CONTRACT = 'contracts/baseline.yaml'
    }

    stages {
        stage('Setup') {
            steps {
                sh 'pip install tracetap'
                sh 'npm install'
            }
        }

        stage('Start Test Environment') {
            steps {
                sh 'docker-compose up -d api'
                sh 'sleep 10'  // Wait for API to be ready
            }
        }

        stage('Capture Traffic') {
            steps {
                script {
                    // Start capture in background
                    sh '''
                        tracetap capture \
                          --port 8080 \
                          --session-name "jenkins-${BUILD_NUMBER}" \
                          --export current-traffic.json &
                        echo $! > capture.pid
                        sleep 2
                    '''

                    try {
                        // Run tests through proxy
                        sh '''
                            export HTTP_PROXY=http://localhost:8080
                            export HTTPS_PROXY=http://localhost:8080
                            npm test
                        '''
                    } finally {
                        // Stop capture
                        sh 'kill $(cat capture.pid) || true'
                    }
                }
            }
        }

        stage('Generate Contract') {
            steps {
                sh '''
                    tracetap contract create current-traffic.json \
                      --output current-contract.yaml
                '''
            }
        }

        stage('Verify Contract') {
            steps {
                script {
                    def verifyResult = sh(
                        script: '''
                            tracetap contract verify \
                              --baseline ${BASELINE_CONTRACT} \
                              --current current-contract.yaml \
                              --output contract-diff.json \
                              --fail-on-breaking
                        ''',
                        returnStatus: true
                    )

                    // Parse results
                    def diff = readJSON file: 'contract-diff.json'
                    def breaking = diff.changes.findAll { it.severity == 'BREAKING' }

                    if (breaking.size() > 0) {
                        def message = "Breaking API changes detected:\n"
                        breaking.each { change ->
                            message += "- ${change.path}: ${change.message}\n"
                        }

                        // Post to Slack/Teams
                        slackSend(
                            color: 'danger',
                            message: message
                        )

                        error("Breaking changes detected - blocking deployment")
                    }
                }
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                sh './deploy.sh'
            }
        }
    }

    post {
        always {
            // Archive artifacts
            archiveArtifacts artifacts: 'contract-diff.json,current-contract.yaml', allowEmptyArchive: true

            // Cleanup
            sh 'docker-compose down'
        }

        failure {
            emailext(
                subject: "API Contract Verification Failed - Build #${BUILD_NUMBER}",
                body: "Contract verification failed. Check attached diff.",
                attachmentsPattern: 'contract-diff.json',
                to: '${DEFAULT_RECIPIENTS}'
            )
        }
    }
}
```

### Shared Library for TraceTap

Create `vars/tracetapVerify.groovy`:

```groovy
def call(Map config = [:]) {
    def baseline = config.baseline ?: 'contracts/baseline.yaml'
    def sessionName = config.sessionName ?: "jenkins-${env.BUILD_NUMBER}"
    def failOnBreaking = config.get('failOnBreaking', true)

    // Capture traffic
    sh """
        tracetap capture \
          --port 8080 \
          --session-name "${sessionName}" \
          --export current-traffic.json &
        echo \$! > capture.pid
        sleep 2
    """

    try {
        // Run tests
        sh """
            export HTTP_PROXY=http://localhost:8080
            export HTTPS_PROXY=http://localhost:8080
            ${config.testCommand ?: 'npm test'}
        """
    } finally {
        sh 'kill $(cat capture.pid) || true'
    }

    // Generate and verify
    sh """
        tracetap contract create current-traffic.json \
          --output current-contract.yaml

        tracetap contract verify \
          --baseline ${baseline} \
          --current current-contract.yaml \
          --output contract-diff.json \
          ${failOnBreaking ? '--fail-on-breaking' : ''}
    """

    return readJSON(file: 'contract-diff.json')
}
```

Usage in Jenkinsfile:

```groovy
@Library('shared-library') _

pipeline {
    agent any

    stages {
        stage('Verify API') {
            steps {
                script {
                    def result = tracetapVerify(
                        baseline: 'contracts/production.yaml',
                        testCommand: 'npm run test:integration'
                    )

                    echo "Changes detected: ${result.changes.size()}"
                }
            }
        }
    }
}
```

---

## Contract Verification

### Creating Baseline Contract

```bash
# Capture production traffic
tracetap capture \
  --port 8080 \
  --filter api.production.com \
  --export prod-baseline.json

# Generate OpenAPI contract
tracetap contract create prod-baseline.json \
  --output contracts/baseline.yaml \
  --title "Production API Baseline" \
  --version "1.0.0"

# Store in version control
git add contracts/baseline.yaml
git commit -m "Add production API baseline contract"
```

### Verification Strategy

```bash
# Strict mode - fail on any breaking change
tracetap contract verify \
  --baseline contracts/baseline.yaml \
  --current contracts/current.yaml \
  --fail-on-breaking

# Lenient mode - report but don't fail
tracetap contract verify \
  --baseline contracts/baseline.yaml \
  --current contracts/current.yaml \
  --output diff.json

# Custom severity threshold
tracetap contract verify \
  --baseline contracts/baseline.yaml \
  --current contracts/current.yaml \
  --max-breaking-changes 0 \
  --max-warnings 5
```

---

## Breaking Change Detection

### What Gets Detected

**Breaking Changes (Block Deployment):**
- ❌ Removed endpoints
- ❌ Removed required fields
- ❌ Changed response types
- ❌ Changed HTTP methods
- ❌ Removed path parameters

**Warnings (Alert but Allow):**
- ⚠️ New required fields
- ⚠️ Changed optional fields
- ⚠️ Deprecated endpoints

**Info (Track Only):**
- ℹ️ New endpoints
- ℹ️ New optional fields
- ℹ️ Documentation changes

### Example Diff Output

```json
{
  "summary": {
    "breaking_changes": 2,
    "warnings": 3,
    "info": 5,
    "compatible": false
  },
  "changes": [
    {
      "severity": "BREAKING",
      "category": "endpoint",
      "path": "/users/{id}",
      "message": "Endpoint removed",
      "old_value": "GET /users/{id}",
      "new_value": null
    },
    {
      "severity": "BREAKING",
      "category": "field",
      "path": "/users.email",
      "message": "Required field removed",
      "old_value": "string (required)",
      "new_value": null
    },
    {
      "severity": "WARNING",
      "category": "field",
      "path": "/users.phone",
      "message": "New required field added",
      "old_value": null,
      "new_value": "string (required)"
    }
  ]
}
```

---

## Advanced Patterns

### Semantic Versioning for Contracts

```bash
# contracts/
# ├── v1.0.0-baseline.yaml
# ├── v1.1.0-baseline.yaml
# └── v2.0.0-baseline.yaml

# Verify against specific version
tracetap contract verify \
  --baseline contracts/v1.0.0-baseline.yaml \
  --current current.yaml
```

### Multi-Branch Baseline

```yaml
# .github/workflows/contract-verify.yml
- name: Select baseline
  run: |
    if [[ "${{ github.base_ref }}" == "main" ]]; then
      BASELINE="contracts/production-baseline.yaml"
    elif [[ "${{ github.base_ref }}" == "develop" ]]; then
      BASELINE="contracts/staging-baseline.yaml"
    else
      BASELINE="contracts/feature-baseline.yaml"
    fi
    echo "BASELINE=$BASELINE" >> $GITHUB_ENV

- name: Verify
  run: |
    tracetap contract verify \
      --baseline ${{ env.BASELINE }} \
      --current current.yaml
```

### Progressive Contract Updates

```bash
#!/bin/bash
# scripts/update-contract.sh

# Generate new contract
tracetap contract create current-traffic.json \
  --output new-contract.yaml

# Verify compatibility
if tracetap contract verify \
     --baseline contracts/baseline.yaml \
     --current new-contract.yaml \
     --fail-on-breaking; then

  # Compatible - update baseline
  cp new-contract.yaml contracts/baseline.yaml
  git add contracts/baseline.yaml
  git commit -m "Update baseline contract (backward compatible)"
else
  echo "Breaking changes detected!"
  echo "Review changes and bump major version if intentional"
  exit 1
fi
```

---

## Troubleshooting

### Issue 1: False Positive Breaking Changes

**Problem:** CI reports breaking changes that aren't actually breaking

**Solution:** Use ignore patterns

```bash
tracetap contract verify \
  --baseline baseline.yaml \
  --current current.yaml \
  --ignore-paths "/internal/*" \
  --ignore-fields "metadata.timestamp,debug.*"
```

### Issue 2: Flaky Contract Tests

**Problem:** Intermittent failures due to dynamic responses

**Solution:** Normalize before comparison

```bash
# Generate contract with normalization
tracetap contract create traffic.json \
  --output contract.yaml \
  --normalize-ids \
  --normalize-timestamps \
  --exclude-headers "X-Request-ID,X-Trace-ID"
```

### Issue 3: Slow CI Builds

**Problem:** Contract verification adds too much time

**Solution:** Parallel execution and caching

```yaml
- name: Cache baseline
  uses: actions/cache@v3
  with:
    path: contracts/baseline.yaml
    key: contract-baseline-${{ hashFiles('package.json') }}

- name: Quick verify
  run: |
    # Use contract-only mode (no traffic capture)
    tracetap contract verify \
      --baseline contracts/baseline.yaml \
      --current <(curl -s https://api.staging.com/openapi.json) \
      --fast
```

### Issue 4: Certificate Issues in CI

**Problem:** HTTPS capture fails in containerized CI

**Solution:** Use environment-specific config

```yaml
- name: Setup certificates
  run: |
    tracetap cert install --ci-mode
    update-ca-certificates  # Linux
```

Or disable SSL verification for test environments:

```bash
tracetap capture \
  --port 8080 \
  --no-verify-ssl \
  --export traffic.json
```

---

## Best Practices

### 1. Version Baseline Contracts

```bash
contracts/
├── v1/
│   ├── baseline.yaml
│   └── metadata.json
├── v2/
│   ├── baseline.yaml
│   └── metadata.json
└── current/
    ├── baseline.yaml -> ../v2/baseline.yaml
    └── metadata.json
```

### 2. Separate Concerns

```yaml
# Different workflows for different checks
.github/workflows/
├── contract-verify.yml      # Breaking change detection
├── test-generation.yml      # Generate regression tests
└── traffic-replay.yml       # Replay validation
```

### 3. Use Branch Protection

```yaml
# .github/branch-protection.yml
branches:
  main:
    required_status_checks:
      - verify-api-contract
      - test-generation
```

### 4. Set Up Notifications

```yaml
- name: Notify on breaking changes
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: 'Breaking API changes detected in PR #${{ github.event.number }}'
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Related Documentation

- [Playwright Integration](./playwright-integration.md) - Integrate with Playwright tests
- [Local Development](./local-development.md) - Daily development workflows
- [Contract-First](./contract-first.md) - Contract-first development
- [TraceTap README](../../README.md) - Complete feature guide

---

## Quick Reference

```bash
# Create baseline
tracetap contract create prod-traffic.json -o baseline.yaml

# Verify changes
tracetap contract verify --baseline baseline.yaml --current current.yaml --fail-on-breaking

# Generate tests
tracetap-playwright traffic.json -o tests/

# Replay to staging
tracetap-replay.py replay prod-traffic.json --target https://staging-api.com
```
