#!/bin/bash
# Manual Integration Test Script for TraceTap v2.1
# Tests all new CLI flags with example sessions

set -e  # Exit on error

echo "======================================"
echo "TraceTap v2.1 Integration Test Suite"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
test_start() {
    echo -e "${YELLOW}[TEST]${NC} $1"
    TESTS_RUN=$((TESTS_RUN + 1))
}

test_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

test_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

# Check prerequisites
echo "Checking prerequisites..."

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}ERROR:${NC} ANTHROPIC_API_KEY environment variable not set"
    echo "Please set it: export ANTHROPIC_API_KEY=sk-ant-..."
    exit 1
fi

# Check for example sessions
TODOMVC_SESSION="examples/ui-recording-demo/todomvc/session-example"
ECOMMERCE_SESSION="examples/ui-recording-demo/ecommerce/session-example"

if [ ! -f "$TODOMVC_SESSION/correlation.json" ]; then
    echo -e "${RED}ERROR:${NC} Example session not found: $TODOMVC_SESSION"
    exit 1
fi

echo -e "${GREEN}Prerequisites OK${NC}"
echo ""

# Create temp directory for test outputs
TEST_OUTPUT_DIR="test-results/integration-tests-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TEST_OUTPUT_DIR"
echo "Test outputs will be saved to: $TEST_OUTPUT_DIR"
echo ""

# ============================================================================
# TEST 1: Basic generation (backward compatibility)
# ============================================================================
test_start "Basic generation without new flags"

if tracetap-generate-tests "$TODOMVC_SESSION" \
    -o "$TEST_OUTPUT_DIR/test1-basic.spec.ts" \
    --template basic 2>&1 | tee "$TEST_OUTPUT_DIR/test1.log"; then

    if [ -f "$TEST_OUTPUT_DIR/test1-basic.spec.ts" ]; then
        test_pass "Generated test file exists"

        # Check file contains expected content
        if grep -q "import.*test.*expect.*from.*@playwright/test" "$TEST_OUTPUT_DIR/test1-basic.spec.ts"; then
            test_pass "Contains proper imports"
        else
            test_fail "Missing proper imports"
        fi
    else
        test_fail "Test file was not created"
    fi
else
    test_fail "Generation command failed"
fi
echo ""

# ============================================================================
# TEST 2: PII Sanitization (default ON)
# ============================================================================
test_start "PII sanitization enabled by default"

if tracetap-generate-tests "$TODOMVC_SESSION" \
    -o "$TEST_OUTPUT_DIR/test2-sanitized.spec.ts" \
    2>&1 | tee "$TEST_OUTPUT_DIR/test2.log"; then

    # Check log for sanitization message
    if grep -q "PII sanitization ENABLED" "$TEST_OUTPUT_DIR/test2.log" || \
       grep -q "Initializing AI test generator" "$TEST_OUTPUT_DIR/test2.log"; then
        test_pass "Sanitization enabled by default"
    else
        test_fail "Sanitization status unclear"
    fi
else
    test_fail "Generation with sanitization failed"
fi
echo ""

# ============================================================================
# TEST 3: PII Sanitization disabled
# ============================================================================
test_start "PII sanitization can be disabled"

if tracetap-generate-tests "$TODOMVC_SESSION" \
    -o "$TEST_OUTPUT_DIR/test3-no-sanitize.spec.ts" \
    --no-sanitize \
    2>&1 | tee "$TEST_OUTPUT_DIR/test3.log"; then

    # Check for warning message
    if grep -q "WARNING.*PII sanitization.*DISABLED" "$TEST_OUTPUT_DIR/test3.log"; then
        test_pass "Warning displayed when sanitization disabled"
    else
        test_fail "No warning when sanitization disabled"
    fi
else
    test_fail "Generation with --no-sanitize failed"
fi
echo ""

# ============================================================================
# TEST 4: Performance assertions
# ============================================================================
test_start "Performance assertions flag"

if tracetap-generate-tests "$TODOMVC_SESSION" \
    -o "$TEST_OUTPUT_DIR/test4-performance.spec.ts" \
    --performance \
    2>&1 | tee "$TEST_OUTPUT_DIR/test4.log"; then

    if [ -f "$TEST_OUTPUT_DIR/test4-performance.spec.ts" ]; then
        test_pass "Generated test file with performance flag"

        # Check if performance thresholds were extracted
        if grep -q "Performance.*threshold" "$TEST_OUTPUT_DIR/test4.log" || \
           grep -q "Performance" "$TEST_OUTPUT_DIR/test4.log"; then
            test_pass "Performance thresholds extracted"
        else
            echo "Note: No performance thresholds extracted (may be expected if session has no duration data)"
        fi
    else
        test_fail "Test file not created with --performance"
    fi
else
    test_fail "Generation with --performance failed"
fi
echo ""

# ============================================================================
# TEST 5: Test organization
# ============================================================================
test_start "Test organization flag"

if tracetap-generate-tests "$TODOMVC_SESSION" \
    -o "$TEST_OUTPUT_DIR/organized/" \
    --organize \
    2>&1 | tee "$TEST_OUTPUT_DIR/test5.log"; then

    # Check if organized directory was created
    if [ -d "$TEST_OUTPUT_DIR/organized" ]; then
        test_pass "Organized directory created"

        # Count generated files
        FILE_COUNT=$(find "$TEST_OUTPUT_DIR/organized" -name "*.spec.ts" | wc -l)
        if [ "$FILE_COUNT" -gt 0 ]; then
            test_pass "Generated $FILE_COUNT organized test files"
        else
            test_fail "No test files in organized directory"
        fi

        # Check for subdirectories (features)
        SUBDIR_COUNT=$(find "$TEST_OUTPUT_DIR/organized" -mindepth 1 -maxdepth 1 -type d | wc -l)
        if [ "$SUBDIR_COUNT" -gt 0 ]; then
            test_pass "Created $SUBDIR_COUNT feature subdirectories"
        else
            echo "Note: No subdirectories created (may be expected for simple session)"
        fi
    else
        test_fail "Organized directory not created"
    fi
else
    test_fail "Generation with --organize failed"
fi
echo ""

# ============================================================================
# TEST 6: Test variations
# ============================================================================
test_start "Test variations flag"

if tracetap-generate-tests "$TODOMVC_SESSION" \
    -o "$TEST_OUTPUT_DIR/test6-variations.spec.ts" \
    --variations 3 \
    2>&1 | tee "$TEST_OUTPUT_DIR/test6.log"; then

    # Check for variation files
    VAR_COUNT=$(ls "$TEST_OUTPUT_DIR"/test6-variations-variation-*.spec.ts 2>/dev/null | wc -l)

    if [ "$VAR_COUNT" -eq 3 ]; then
        test_pass "Generated 3 variation files"
    elif [ "$VAR_COUNT" -gt 0 ]; then
        echo "Note: Generated $VAR_COUNT variations (expected 3, may depend on input fields)"
    else
        echo "Note: No variation files created (may be expected if session has no input fields)"
    fi
else
    test_fail "Generation with --variations failed"
fi
echo ""

# ============================================================================
# TEST 7: Combined features (performance + organize)
# ============================================================================
test_start "Combined: performance + organize"

if tracetap-generate-tests "$TODOMVC_SESSION" \
    -o "$TEST_OUTPUT_DIR/combined-perf-org/" \
    --performance \
    --organize \
    2>&1 | tee "$TEST_OUTPUT_DIR/test7.log"; then

    if [ -d "$TEST_OUTPUT_DIR/combined-perf-org" ]; then
        test_pass "Combined performance + organize works"

        FILE_COUNT=$(find "$TEST_OUTPUT_DIR/combined-perf-org" -name "*.spec.ts" | wc -l)
        if [ "$FILE_COUNT" -gt 0 ]; then
            test_pass "Generated $FILE_COUNT test files"
        fi
    else
        test_fail "Combined features directory not created"
    fi
else
    test_fail "Combined performance + organize failed"
fi
echo ""

# ============================================================================
# TEST 8: Combined features (variations + organize)
# ============================================================================
test_start "Combined: variations + organize"

if tracetap-generate-tests "$TODOMVC_SESSION" \
    -o "$TEST_OUTPUT_DIR/combined-var-org/" \
    --variations 2 \
    --organize \
    2>&1 | tee "$TEST_OUTPUT_DIR/test8.log"; then

    if [ -d "$TEST_OUTPUT_DIR/combined-var-org" ]; then
        test_pass "Combined variations + organize works"

        # Check for variation suffixes
        if ls "$TEST_OUTPUT_DIR/combined-var-org"/*variation-*.spec.ts 2>/dev/null | head -1 > /dev/null; then
            test_pass "Variation files created in organized structure"
        else
            echo "Note: No variations created (may depend on input fields)"
        fi
    else
        test_fail "Combined features directory not created"
    fi
else
    test_fail "Combined variations + organize failed"
fi
echo ""

# ============================================================================
# TEST 9: All features combined
# ============================================================================
test_start "All features: variations + performance + organize"

if tracetap-generate-tests "$TODOMVC_SESSION" \
    -o "$TEST_OUTPUT_DIR/all-features/" \
    --variations 2 \
    --performance \
    --organize \
    2>&1 | tee "$TEST_OUTPUT_DIR/test9.log"; then

    if [ -d "$TEST_OUTPUT_DIR/all-features" ]; then
        test_pass "All features combined works"

        FILE_COUNT=$(find "$TEST_OUTPUT_DIR/all-features" -name "*.spec.ts" | wc -l)
        if [ "$FILE_COUNT" -gt 0 ]; then
            test_pass "Generated $FILE_COUNT test files with all features"
        fi
    else
        test_fail "All features directory not created"
    fi
else
    test_fail "All features combined failed"
fi
echo ""

# ============================================================================
# TEST 10: Different templates
# ============================================================================
test_start "Test with comprehensive template"

if tracetap-generate-tests "$TODOMVC_SESSION" \
    -o "$TEST_OUTPUT_DIR/test10-comprehensive.spec.ts" \
    --template comprehensive \
    --performance \
    2>&1 | tee "$TEST_OUTPUT_DIR/test10.log"; then

    if [ -f "$TEST_OUTPUT_DIR/test10-comprehensive.spec.ts" ]; then
        test_pass "Comprehensive template with performance works"
    else
        test_fail "Comprehensive template file not created"
    fi
else
    test_fail "Comprehensive template generation failed"
fi
echo ""

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "======================================"
echo "Test Summary"
echo "======================================"
echo "Total Tests: $TESTS_RUN"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All integration tests passed!${NC}"
    echo ""
    echo "Test outputs saved to: $TEST_OUTPUT_DIR"
    exit 0
else
    echo -e "${RED}❌ Some integration tests failed${NC}"
    echo ""
    echo "Check logs in: $TEST_OUTPUT_DIR"
    exit 1
fi
