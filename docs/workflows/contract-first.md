# Contract-First Development Workflow

Guide for contract-first development using TraceTap to establish API contracts, verify compatibility, and prevent breaking changes.

## Table of Contents

1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [Workflow: Generate Baseline from Production](#workflow-generate-baseline-from-production)
4. [Workflow: Verify Changes Before Deploy](#workflow-verify-changes-before-deploy)
5. [Workflow: Version Control for Contracts](#workflow-version-control-for-contracts)
6. [Advanced Patterns](#advanced-patterns)
7. [Contract Management](#contract-management)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

**Contract-First Development** means treating your API contract as the source of truth. Changes are validated against the contract before deployment, preventing breaking changes from reaching production.

### Why Contract-First?

**Traditional approach:**
```
Code → Deploy → Break Production → Fix → Redeploy
```

**Contract-first approach:**
```
Code → Generate Contract → Verify → Block Breaking Changes → Deploy Safely
```

### TraceTap Contract Workflow

```
Production Traffic → Baseline Contract → Feature Development →
New Contract → Verify Compatibility → Deploy or Block
```

---

## Core Concepts

### What is a Contract?

An **API contract** is an OpenAPI specification that defines:
- Available endpoints
- Request/response schemas
- Required vs optional fields
- Data types
- HTTP methods

### Contract Changes

| Type | Severity | Example | Action |
|------|----------|---------|--------|
| **Breaking** | 🚨 High | Remove endpoint, change type | Block deployment |
| **Warning** | ⚠️ Medium | Add required field | Review required |
| **Info** | ℹ️ Low | Add optional field | Allow deployment |

### Contract Sources

TraceTap can generate contracts from:
1. **Live traffic** - Capture real API usage
2. **Test runs** - Generated from automated tests
3. **Manual exploration** - Interactive API usage
4. **Production** - Real user behavior

---

## Workflow: Generate Baseline from Production

### Step 1: Capture Production Traffic

**Option A: Production Proxy (Passive)**

```bash
# Set up production proxy (read-only monitoring)
tracetap capture \
  --port 8080 \
  --filter api.production.com \
  --session-name "production-baseline-$(date +%Y%m%d)" \
  --export captures/prod-baseline.json

# Let it run for 24-48 hours to capture representative traffic
# Ctrl+C when sufficient
```

**Option B: Replay from Production Logs**

```bash
# If you have access logs, convert them
# (Requires custom script or log parser)

# Or capture during smoke tests in production
tracetap capture \
  --port 8080 \
  --filter api.production.com \
  --export prod-smoke-test.json &

PID=$!
# Run production smoke tests
./smoke-tests.sh
kill $PID
```

**Option C: Use Staging as Production Proxy**

```bash
# Capture from staging (if representative)
tracetap capture \
  --port 8080 \
  --filter api.staging.com \
  --session-name "staging-baseline" \
  --export captures/staging-baseline.json

# Run comprehensive test suite
npm run test:integration
```

### Step 2: Generate OpenAPI Contract

```bash
# Generate baseline contract
tracetap contract create captures/prod-baseline.json \
  --output contracts/baseline-v1.0.0.yaml \
  --title "Production API Baseline" \
  --version "1.0.0" \
  --description "Generated from production traffic on $(date)"

# Review the contract
cat contracts/baseline-v1.0.0.yaml
```

**Example output:**

```yaml
openapi: 3.0.0
info:
  title: Production API Baseline
  version: 1.0.0
  description: Generated from production traffic on 2024-01-15

servers:
  - url: https://api.production.com

paths:
  /api/users:
    get:
      summary: List users
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/User'

  /api/users/{id}:
    get:
      summary: Get user by ID
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'

components:
  schemas:
    User:
      type: object
      required:
        - id
        - email
        - name
      properties:
        id:
          type: string
        email:
          type: string
          format: email
        name:
          type: string
        phone:
          type: string
```

### Step 3: Store Baseline in Version Control

```bash
# Create contracts directory structure
mkdir -p contracts/{baselines,snapshots}

# Store baseline
cp contracts/baseline-v1.0.0.yaml contracts/baselines/

# Create symbolic link to current baseline
ln -sf baselines/baseline-v1.0.0.yaml contracts/baseline-current.yaml

# Commit to git
git add contracts/
git commit -m "Add API baseline contract v1.0.0

Generated from production traffic captured on 2024-01-15.
Represents current production API state."

# Tag the commit
git tag api-baseline-v1.0.0
git push origin api-baseline-v1.0.0
```

### Step 4: Document the Baseline

Create `contracts/baselines/baseline-v1.0.0.md`:

```markdown
# API Baseline v1.0.0

**Generated:** 2024-01-15
**Source:** Production traffic (24-hour capture)
**Endpoints:** 47
**Schemas:** 12

## Capture Details

- **Session Name:** production-baseline-20240115
- **Duration:** 24 hours
- **Total Requests:** 15,432
- **Unique Endpoints:** 47
- **API Version:** v1

## Coverage

- Authentication: ✓
- User Management: ✓
- Product Catalog: ✓
- Orders: ✓
- Payments: Partial (test mode only)

## Known Limitations

- Admin endpoints not fully captured
- Webhook endpoints excluded
- Internal-only APIs excluded

## Next Review

Schedule: 2024-04-15 (quarterly)
```

---

## Workflow: Verify Changes Before Deploy

### Step 1: Develop Feature with Contract Awareness

```bash
# Create feature branch
git checkout -b feature/user-preferences

# Develop your feature...

# Capture current behavior
tracetap capture \
  --port 8080 \
  --session-name "feature-user-preferences" \
  --export captures/feature-current.json

# Run your tests
npm test
```

### Step 2: Generate Current Contract

```bash
# Generate contract from current code
tracetap contract create captures/feature-current.json \
  --output contracts/snapshots/feature-user-preferences.yaml \
  --title "User Preferences Feature" \
  --version "1.1.0-dev"
```

### Step 3: Verify Against Baseline

```bash
# Compare contracts
tracetap contract verify \
  --baseline contracts/baseline-current.yaml \
  --current contracts/snapshots/feature-user-preferences.yaml \
  --output contract-diff.json \
  --verbose

# Review output
cat contract-diff.json | jq
```

**Example output:**

```json
{
  "summary": {
    "breaking_changes": 0,
    "warnings": 1,
    "info": 3,
    "compatible": true
  },
  "changes": [
    {
      "severity": "INFO",
      "category": "endpoint",
      "path": "/api/users/{id}/preferences",
      "message": "New endpoint added",
      "new_value": "GET /api/users/{id}/preferences"
    },
    {
      "severity": "INFO",
      "category": "endpoint",
      "path": "/api/users/{id}/preferences",
      "message": "New endpoint added",
      "new_value": "PUT /api/users/{id}/preferences"
    },
    {
      "severity": "WARNING",
      "category": "schema",
      "path": "User.preferences",
      "message": "New optional field added to existing schema",
      "new_value": "object (optional)"
    },
    {
      "severity": "INFO",
      "category": "schema",
      "path": "UserPreferences",
      "message": "New schema added"
    }
  ]
}
```

### Step 4: Handle Verification Results

**Scenario A: No Breaking Changes (Good!)**

```bash
# Contract is compatible
if cat contract-diff.json | jq -e '.summary.breaking_changes == 0' > /dev/null; then
  echo "✓ Contract compatible - safe to deploy"

  # Update baseline (optional for minor versions)
  cp contracts/snapshots/feature-user-preferences.yaml \
     contracts/baselines/baseline-v1.1.0.yaml

  ln -sf baselines/baseline-v1.1.0.yaml contracts/baseline-current.yaml

  git add contracts/
  git commit -m "Update API contract to v1.1.0 (backward compatible)"
fi
```

**Scenario B: Breaking Changes Detected (Block!)**

```bash
# Breaking changes found
if cat contract-diff.json | jq -e '.summary.breaking_changes > 0' > /dev/null; then
  echo "⚠️ Breaking changes detected!"

  # Show breaking changes
  cat contract-diff.json | jq '.changes[] | select(.severity == "BREAKING")'

  # Options:
  # 1. Fix the code to be backward compatible
  # 2. Plan a major version bump (v2.0.0)
  # 3. Add deprecation warnings first

  exit 1
fi
```

**Scenario C: Intentional Breaking Changes**

```bash
# Plan major version
# Update to v2.0.0

# Document breaking changes
cat > contracts/CHANGELOG.md <<EOF
# API Contract Changelog

## v2.0.0 (Unreleased)

### Breaking Changes

- Removed deprecated /api/legacy endpoint
- Changed User.email from optional to required
- Modified /api/users response format

### Migration Guide

1. Update client to use /api/v2/users endpoint
2. Ensure email is provided in user creation
3. Update response parsing for new format

See: docs/migration-v1-to-v2.md
EOF

# Commit with clear communication
git add contracts/
git commit -m "BREAKING: API contract v2.0.0

See CHANGELOG.md for migration guide."
```

### Step 5: Integrate into CI/CD

See [CI/CD Integration](./ci-cd-integration.md) for complete pipeline setup.

**Quick GitHub Actions example:**

```yaml
# .github/workflows/contract-verify.yml
name: Contract Verification

on: [pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup
        run: pip install tracetap

      - name: Capture current
        run: |
          tracetap capture --port 8080 --export current.json &
          sleep 2
          npm test
          pkill tracetap

      - name: Generate contract
        run: |
          tracetap contract create current.json -o current-contract.yaml

      - name: Verify
        run: |
          tracetap contract verify \
            --baseline contracts/baseline-current.yaml \
            --current current-contract.yaml \
            --fail-on-breaking
```

---

## Workflow: Version Control for Contracts

### Semantic Versioning for API Contracts

Follow semantic versioning:

- **Major (v2.0.0)**: Breaking changes
- **Minor (v1.1.0)**: New features (backward compatible)
- **Patch (v1.0.1)**: Bug fixes

### Directory Structure

```bash
contracts/
├── baselines/               # Official baseline contracts
│   ├── baseline-v1.0.0.yaml
│   ├── baseline-v1.1.0.yaml
│   ├── baseline-v1.2.0.yaml
│   └── baseline-v2.0.0.yaml
├── snapshots/              # Development snapshots
│   ├── feature-123.yaml
│   └── bugfix-456.yaml
├── deprecated/             # Old contracts
│   └── baseline-v0.9.0.yaml
├── baseline-current.yaml   # Symlink to latest
├── CHANGELOG.md            # Contract change history
└── README.md              # Documentation
```

### Tagging Strategy

```bash
# Tag each baseline contract
git tag -a api-v1.0.0 -m "API Contract v1.0.0 - Initial baseline"
git tag -a api-v1.1.0 -m "API Contract v1.1.0 - Add user preferences"
git tag -a api-v2.0.0 -m "API Contract v2.0.0 - Major revision"

# Push tags
git push origin --tags

# List all contract versions
git tag -l "api-v*"
```

### Branch Strategy

```bash
# Main branch: stable contracts
git checkout main
# contracts/baseline-current.yaml -> baselines/baseline-v1.2.0.yaml

# Feature branches: development contracts
git checkout -b feature/new-endpoint
# contracts/snapshots/feature-new-endpoint.yaml

# Release branches: candidate contracts
git checkout -b release/v1.3.0
# contracts/baselines/baseline-v1.3.0.yaml (candidate)
```

### Contract Changelog

Maintain `contracts/CHANGELOG.md`:

```markdown
# API Contract Changelog

All notable changes to the API contract are documented here.

## [2.0.0] - 2024-03-01

### Breaking Changes
- Removed `/api/legacy/users` endpoint
- Changed `User.email` from optional to required
- Modified `/api/auth/login` response structure

### Added
- New `/api/v2/users` endpoint with pagination
- Added `User.metadata` optional field
- Added `/api/users/{id}/avatar` endpoint

### Migration
See [Migration Guide v1 to v2](../docs/migration-v1-to-v2.md)

## [1.2.0] - 2024-02-01

### Added
- New `/api/users/{id}/preferences` endpoint
- Added `UserPreferences` schema
- Added optional `User.preferences` field

### Changed
- None

### Deprecated
- None

## [1.1.0] - 2024-01-15

### Added
- New `/api/users/{id}/settings` endpoint
- Added `privacy` query parameter to `/api/users`

## [1.0.0] - 2024-01-01

Initial baseline from production traffic.
```

---

## Advanced Patterns

### Pattern 1: Multi-Environment Baselines

```bash
contracts/
├── environments/
│   ├── production/
│   │   └── baseline-v1.2.0.yaml
│   ├── staging/
│   │   └── baseline-v1.3.0-rc1.yaml
│   └── development/
│       └── baseline-v1.3.0-dev.yaml
└── baseline-current.yaml -> environments/production/baseline-v1.2.0.yaml
```

Verify against appropriate baseline:

```bash
# Staging deployment
tracetap contract verify \
  --baseline contracts/environments/staging/baseline-v1.3.0-rc1.yaml \
  --current current-contract.yaml

# Production deployment
tracetap contract verify \
  --baseline contracts/environments/production/baseline-v1.2.0.yaml \
  --current current-contract.yaml
```

### Pattern 2: Contract Deprecation Workflow

```bash
# Step 1: Mark as deprecated in contract
# baseline-v1.3.0.yaml
paths:
  /api/legacy/users:
    get:
      deprecated: true
      summary: "[DEPRECATED] Use /api/v2/users instead"

# Step 2: Update changelog
echo "## [1.3.0] - $(date +%Y-%m-%d)
### Deprecated
- \`/api/legacy/users\` - Use \`/api/v2/users\` instead
" >> contracts/CHANGELOG.md

# Step 3: Deploy with warnings
# (Endpoint still works, but clients warned)

# Step 4: After grace period (e.g., 3 months), remove in v2.0.0
```

### Pattern 3: Contract-Driven Development

```bash
# 1. Design contract FIRST (before coding)
cat > contracts/design/feature-search.yaml <<EOF
openapi: 3.0.0
paths:
  /api/search:
    get:
      parameters:
        - name: q
          in: query
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Search results
          content:
            application/json:
              schema:
                type: object
                properties:
                  results:
                    type: array
                    items:
                      type: object
EOF

# 2. Review contract with team
# (Iterate on design)

# 3. Implement feature to match contract

# 4. Verify implementation matches design
tracetap capture --port 8080 --export impl.json
tracetap contract create impl.json --output impl-contract.yaml
tracetap contract verify \
  --baseline contracts/design/feature-search.yaml \
  --current impl-contract.yaml

# 5. If matches, promote to baseline
```

### Pattern 4: Consumer-Driven Contracts

```bash
# Consumer team defines needs
cat > contracts/consumer-needs/mobile-app-v2.yaml <<EOF
# Mobile app v2 requirements
openapi: 3.0.0
paths:
  /api/users/{id}:
    get:
      # Mobile app needs these fields
      responses:
        '200':
          content:
            application/json:
              schema:
                required:
                  - id
                  - email
                  - profile_image_url
EOF

# API team verifies they provide these
tracetap contract verify \
  --baseline contracts/consumer-needs/mobile-app-v2.yaml \
  --current contracts/baseline-current.yaml \
  --mode consumer-driven
```

### Pattern 5: Incremental Baseline Updates

```bash
#!/bin/bash
# scripts/update-baseline.sh

# Capture current state
tracetap capture --port 8080 --export current.json &
PID=$!
npm test
kill $PID

# Generate contract
tracetap contract create current.json --output new-contract.yaml

# Verify compatibility
if tracetap contract verify \
     --baseline contracts/baseline-current.yaml \
     --current new-contract.yaml \
     --fail-on-breaking; then

  # Compatible - auto-update
  CURRENT_VERSION=$(cat contracts/baseline-current.yaml | grep "version:" | awk '{print $2}')
  NEXT_VERSION=$(echo $CURRENT_VERSION | awk -F. '{$NF = $NF + 1;} 1' | sed 's/ /./g')

  cp new-contract.yaml "contracts/baselines/baseline-v${NEXT_VERSION}.yaml"
  ln -sf "baselines/baseline-v${NEXT_VERSION}.yaml" contracts/baseline-current.yaml

  git add contracts/
  git commit -m "Auto-update baseline to v${NEXT_VERSION} (backward compatible)"

  echo "✓ Baseline updated to v${NEXT_VERSION}"
else
  echo "⚠️ Breaking changes detected - manual review required"
  exit 1
fi
```

---

## Contract Management

### Best Practices for Baselines

1. **Regular Updates**: Review quarterly or after major releases
2. **Representative Traffic**: Capture during peak usage
3. **Comprehensive Coverage**: Include all endpoints
4. **Clean Data**: Exclude test/debug endpoints
5. **Documentation**: Explain what's captured and limitations

### Contract Review Checklist

Before promoting a contract to baseline:

- [ ] Captured sufficient traffic (>1000 requests)
- [ ] All critical endpoints included
- [ ] Schemas reflect actual data types
- [ ] Required vs optional fields accurate
- [ ] Edge cases covered
- [ ] Documentation updated
- [ ] Changelog entry added
- [ ] Git tag created
- [ ] Team notified

### Baseline Storage Options

**Option 1: Git Repository (Recommended)**

```bash
# Store with code
contracts/baselines/baseline-v1.0.0.yaml

# Pros: Version controlled, easy to review
# Cons: Increases repo size
```

**Option 2: Artifact Storage**

```bash
# Upload to S3/Azure/GCS
aws s3 cp contracts/baseline-v1.0.0.yaml \
  s3://my-api-contracts/baselines/

# Reference in code
BASELINE_URL="https://s3.amazonaws.com/my-api-contracts/baselines/baseline-v1.0.0.yaml"

# Pros: Keeps repo clean
# Cons: External dependency
```

**Option 3: Hybrid**

```bash
# Small contracts in git
git add contracts/baseline-current.yaml

# Large contracts in artifact storage
contracts/README.md:
  "Full baseline: https://s3.../baseline-v1.0.0.yaml"

# Pros: Best of both worlds
```

---

## Best Practices

### 1. Start Simple

```bash
# Don't try to capture everything at once
# Start with critical endpoints

# Capture core API only
tracetap capture \
  --filter-regex "^/api/(auth|users)" \
  --export core-baseline.json

# Generate baseline
tracetap contract create core-baseline.json \
  --output contracts/baseline-core-v1.0.0.yaml

# Expand over time
```

### 2. Automate Verification

```bash
# Add to pre-commit hook
# .git/hooks/pre-commit
#!/bin/bash

if git diff --cached --name-only | grep -q "^src/.*\.(js|ts)$"; then
  echo "Running contract verification..."

  npm run capture:current
  tracetap contract create current.json -o current-contract.yaml

  if ! tracetap contract verify \
         --baseline contracts/baseline-current.yaml \
         --current current-contract.yaml; then
    echo "⚠️ Contract changes detected. Review before committing."
    exit 1
  fi
fi
```

### 3. Communicate Changes

```bash
# When breaking changes needed, create RFC

# contracts/rfcs/rfc-001-remove-legacy-api.md
---
# RFC 001: Remove Legacy API Endpoints

**Status:** Proposed
**Author:** jane@example.com
**Date:** 2024-01-15

## Summary
Remove deprecated /api/v1/legacy endpoints

## Motivation
Endpoints unused for 6 months, blocking v2 architecture

## Breaking Changes
- DELETE /api/v1/legacy/users
- DELETE /api/v1/legacy/auth

## Migration Path
Use /api/v2/users and /api/v2/auth instead

## Timeline
- 2024-02-01: Announce deprecation
- 2024-03-01: Add warnings
- 2024-04-01: Remove endpoints

## Approval
- [ ] Engineering lead
- [ ] Product manager
- [ ] Customer success
---
```

### 4. Version APIs Explicitly

```bash
# Include version in URL
/api/v1/users
/api/v2/users

# Or in headers
X-API-Version: 2

# Maintain separate baselines per version
contracts/
├── v1/
│   └── baseline-v1.2.0.yaml
└── v2/
    └── baseline-v2.0.0.yaml
```

### 5. Monitor Contract Drift

```bash
# Weekly job to detect drift
# cron: 0 9 * * 1  (Every Monday 9am)

# Capture current production
tracetap capture --port 8080 --export prod-current.json
tracetap contract create prod-current.json --output prod-current.yaml

# Compare to baseline
tracetap contract verify \
  --baseline contracts/baseline-current.yaml \
  --current prod-current.yaml \
  --output drift-report.json

# Alert if significant drift
CHANGES=$(cat drift-report.json | jq '.summary.breaking_changes + .summary.warnings')
if [ $CHANGES -gt 5 ]; then
  echo "⚠️ Contract drift detected: $CHANGES changes"
  # Send alert
fi
```

---

## Troubleshooting

### Issue 1: Too Many False Positives

**Problem:** Contract verification reports breaking changes that aren't actually breaking

**Solution:** Tune contract generation

```bash
# Normalize dynamic values
tracetap contract create traffic.json \
  --output contract.yaml \
  --normalize-ids \
  --normalize-timestamps \
  --exclude-headers "X-Request-ID,X-Correlation-ID"

# Ignore volatile fields
tracetap contract verify \
  --baseline baseline.yaml \
  --current current.yaml \
  --ignore-fields "metadata.generated_at,debug.*"
```

### Issue 2: Contract Doesn't Reflect Reality

**Problem:** Generated contract missing endpoints or has wrong types

**Solution:** Improve traffic capture

```bash
# Capture more representative traffic
# - Run comprehensive test suite
# - Capture over longer period
# - Include edge cases

# Use multiple captures
tracetap contract create capture1.json capture2.json capture3.json \
  --output combined-contract.yaml \
  --merge-strategy union
```

### Issue 3: Baseline Out of Sync

**Problem:** Baseline contract doesn't match production anymore

**Solution:** Regenerate baseline

```bash
# Capture fresh production traffic
tracetap capture --port 8080 --export prod-fresh.json

# Generate new baseline
tracetap contract create prod-fresh.json \
  --output contracts/baselines/baseline-v1.3.0.yaml

# Compare old vs new baseline
tracetap contract verify \
  --baseline contracts/baseline-current.yaml \
  --current contracts/baselines/baseline-v1.3.0.yaml

# If acceptable, update
ln -sf baselines/baseline-v1.3.0.yaml contracts/baseline-current.yaml
git add contracts/
git commit -m "Update baseline to v1.3.0 (production sync)"
```

---

## Quick Reference

### Essential Commands

```bash
# Create baseline from production
tracetap capture --filter api.production.com --export prod.json
tracetap contract create prod.json --output baseline.yaml

# Verify changes
tracetap contract create current.json --output current.yaml
tracetap contract verify --baseline baseline.yaml --current current.yaml

# Version control
git add contracts/baseline.yaml
git commit -m "Add API baseline v1.0.0"
git tag api-v1.0.0
```

### Contract Lifecycle

```
1. Generate → 2. Review → 3. Baseline → 4. Verify → 5. Update
     ↑                                                      ↓
     └──────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [CI/CD Integration](./ci-cd-integration.md) - Automate contract verification
- [Playwright Integration](./playwright-integration.md) - Test generation from contracts
- [Local Development](./local-development.md) - Daily workflow tips
- [TraceTap README](../../README.md) - Full feature reference

---

**Next Steps:**
1. [Generate your first baseline](#workflow-generate-baseline-from-production)
2. Set up [contract verification](#workflow-verify-changes-before-deploy)
3. Implement [version control](#workflow-version-control-for-contracts)
