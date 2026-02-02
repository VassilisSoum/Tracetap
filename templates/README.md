# Test Generation Templates

## Overview

Templates guide Claude AI in generating Playwright tests from correlated recording data. Each template provides specific instructions, examples, and best practices for different testing scenarios.

## Available Templates

### basic.txt

**Use when:** Quick test generation, simple flows, smoke tests

**Output:** Minimal assertions, focus on happy path

**Best for:**
- Smoke tests and sanity checks
- Initial test coverage
- Simple user flows (login, form submission)
- Proof of concept tests

**Characteristics:**
- Focuses on UI replay and basic API validation
- Validates HTTP status codes and response structure
- Minimal edge case handling
- Quick to generate and easy to understand

**Example use case:** "Generate a test that verifies login works"

---

### comprehensive.txt

**Use when:** Production test suites, critical flows, regression testing

**Output:** Full validation, edge cases, performance checks

**Best for:**
- CI/CD pipelines
- Regression test suites
- Critical business flows
- Production-ready test coverage

**Characteristics:**
- Extensive schema validation for API requests/responses
- UI state change verification
- Performance assertions based on correlation timing
- Error handling and edge cases
- Confidence-based assertion strictness
- Request/response header validation

**Example use case:** "Generate a comprehensive test for the checkout flow with full validation"

---

### regression.txt

**Use when:** API contract testing, breaking change detection, version tracking

**Output:** Schema validation, version tracking, migration guides

**Best for:**
- API versioning workflows
- Backward compatibility verification
- Contract-first development
- Detecting breaking changes in CI

**Characteristics:**
- Focuses on API contracts, not UI specifics
- Generates reusable contract schemas
- Detects missing/new/changed fields
- Documents expected behavior and versions
- Provides migration guides when changes detected

**Example use case:** "Generate contract tests to catch API breaking changes"

---

## Template Variables

Templates support variable substitution for dynamic content:

| Variable | Description | Example |
|----------|-------------|---------|
| `{events_json}` | Correlated events in JSON format | `[{"type":"click","selector":"button",...}]` |
| `{output_format}` | Target language | `typescript` or `python` |
| `{confidence_threshold}` | Minimum correlation confidence | `0.8` (range: 0.0-1.0) |
| `{base_url}` | Application base URL | `https://app.example.com` |
| `{test_name}` | Generated test name | `user_login_flow` |

Variables are replaced by the test generator before sending the prompt to Claude AI.

---

## Prompt Engineering Best Practices

### 1. Clear Instructions

Be explicit about what to generate:
- Specify test framework and syntax
- Define required assertions
- List validation criteria
- State output format expectations

### 2. Concrete Examples

Show input → output transformations:
- Include example correlated events
- Provide complete test code examples
- Show both TypeScript and Python variants
- Demonstrate edge cases and error handling

### 3. Constraints and Guardrails

Define what NOT to do:
- Avoid hardcoded IDs (use fixtures or variables)
- Don't use hardcoded waits (prefer waitForSelector)
- No credentials in test code
- Avoid brittle selectors (prefer data-testid)

### 4. Format Specifications

Specify exact output format:
- Import statements
- Test structure (describe/test blocks)
- Comment style and documentation
- Variable naming conventions

### 5. Contextual Information

Explain correlation confidence and its meaning:
- High confidence (>0.8): Strict assertions
- Medium confidence (0.5-0.8): Flexible validation
- Low confidence (<0.5): Soft assertions

Provide timing information:
- Use correlation time deltas for performance assertions
- Set reasonable timeout expectations

---

## Customization

### Creating Custom Templates

1. **Copy an existing template** as a starting point:
   ```bash
   cp templates/basic.txt templates/my-custom.txt
   ```

2. **Modify prompt instructions** to fit your needs:
   - Add domain-specific requirements
   - Include organization-specific best practices
   - Add custom validation rules
   - Define project-specific patterns

3. **Add examples** relevant to your use case:
   - Use actual selectors from your app
   - Show your API response formats
   - Include your error handling patterns

4. **Test the template** with sample data:
   ```bash
   tracetap generate --template my-custom --input recordings/sample.json
   ```

5. **Iterate and refine** based on output quality

### Template Best Practices

**Do:**
- Include clear examples for both TypeScript and Python
- Explain *why* certain patterns are used
- Provide decision criteria (when to use this vs that)
- Document expected input format
- Show handling of edge cases

**Don't:**
- Make assumptions about project structure
- Hardcode specific values without explaining flexibility
- Use complex jargon without explanation
- Provide examples without context

---

## Usage Examples

### Basic test generation
```bash
tracetap generate \
  --template basic \
  --input recordings/login-flow.json \
  --output tests/login.spec.ts
```

### Comprehensive with confidence threshold
```bash
tracetap generate \
  --template comprehensive \
  --confidence 0.8 \
  --input recordings/checkout.json \
  --output tests/checkout.spec.ts
```

### Regression tests with version tracking
```bash
tracetap generate \
  --template regression \
  --input recordings/api-flows.json \
  --output tests/contracts/ \
  --version 1.0.0
```

### Python output
```bash
tracetap generate \
  --template basic \
  --format python \
  --input recordings/signup.json \
  --output tests/test_signup.py
```

---

## Integration with AI

### How Templates Work

1. **User records** a flow using Tracetap
2. **Tracetap correlates** UI events with network calls
3. **Template is loaded** and variables are substituted
4. **Prompt is sent** to Claude AI with correlated data
5. **AI generates** test code following template instructions
6. **Output is saved** to specified file

### Template Selection Logic

The CLI can auto-select templates based on context:

```javascript
// Auto-select based on flags
if (flags.comprehensive) {
  template = 'comprehensive.txt';
} else if (flags.contract) {
  template = 'regression.txt';
} else {
  template = 'basic.txt';  // Default
}
```

### Quality Assurance

Generated tests are validated for:
- Syntax correctness (TypeScript/Python parsing)
- Import statement completeness
- Required assertion presence
- Selector validity (when possible)

---

## Template Development Tips

### Testing Your Templates

Create a test harness:

```bash
# templates/test-harness.sh
#!/bin/bash

TEMPLATE=$1
SAMPLE_DATA="fixtures/sample-events.json"

echo "Testing template: $TEMPLATE"
tracetap generate \
  --template "$TEMPLATE" \
  --input "$SAMPLE_DATA" \
  --output "/tmp/test-output.ts" \
  --dry-run

# Validate output
npx tsc --noEmit "/tmp/test-output.ts" && echo "✓ Valid TypeScript"
```

### Iterative Improvement

1. Generate tests from template
2. Run the generated tests
3. Note failures and issues
4. Update template instructions
5. Regenerate and verify improvements

### Version Control

Track template changes:
```bash
git log templates/comprehensive.txt
```

Document template changes in commits:
```
feat(templates): Add performance assertions to comprehensive template

- Include timing-based assertions using correlation deltas
- Add response time validation
- Document performance expectations in comments
```

---

## Troubleshooting

### Common Issues

**Issue:** Generated tests have syntax errors
**Solution:** Check template examples match target language syntax

**Issue:** Tests are too brittle (fail on minor changes)
**Solution:** Use flexible selectors and schema validation instead of exact matches

**Issue:** AI ignores template instructions
**Solution:** Make instructions more explicit, add examples, use stronger language ("MUST", "NEVER")

**Issue:** Generated assertions are too weak
**Solution:** Provide specific assertion examples in template

**Issue:** Output format inconsistent
**Solution:** Specify exact format with examples (imports, structure, naming)

---

## Contributing

To contribute new templates or improvements:

1. Create a new template in `templates/`
2. Add documentation to this README
3. Include test examples in `examples/`
4. Submit a pull request with use case description

---

## Future Enhancements

Planned template features:
- Visual regression testing templates
- Accessibility testing focus
- Load testing scenario generation
- Mobile app testing templates
- API-only contract testing (no UI)
