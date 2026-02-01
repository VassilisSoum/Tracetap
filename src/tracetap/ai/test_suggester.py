"""
Test Suggestion Engine

Converts pattern analysis into actionable test recommendations.
Generates markdown-formatted suggestions with code snippets.
"""

import json
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .pattern_analyzer import Pattern, PatternAnalyzer


class TestSuggestion:
    """Represents a test suggestion with code snippet"""

    def __init__(
        self,
        priority: str,
        title: str,
        observed: str,
        missing: str,
        suggestions: List[str],
        code_snippet: Optional[str] = None,
        pattern_type: str = 'general'
    ):
        self.priority = priority
        self.title = title
        self.observed = observed
        self.missing = missing
        self.suggestions = suggestions
        self.code_snippet = code_snippet
        self.pattern_type = pattern_type

    def to_markdown(self, number: int) -> str:
        """Convert to markdown format"""
        lines = [
            f"## {number}. {self.title} (Priority: {self.priority})",
            "",
            f"**Observed:** {self.observed}",
            "",
            f"**Missing Test:** {self.missing}",
            "",
            "**Suggested:**"
        ]

        for suggestion in self.suggestions:
            lines.append(f"- {suggestion}")

        if self.code_snippet:
            lines.extend([
                "",
                "**Example Test:**",
                "```typescript",
                self.code_snippet.strip(),
                "```"
            ])

        lines.append("")  # Blank line separator

        return "\n".join(lines)


class TestSuggester:
    """
    Generates actionable test suggestions from pattern analysis

    Takes pattern analyzer output and produces:
    - Prioritized test recommendations
    - Code snippets for suggested tests
    - Markdown-formatted output
    """

    def __init__(self, base_url: str = 'https://api.example.com'):
        """
        Initialize test suggester

        Args:
            base_url: Base URL for API endpoints in code snippets
        """
        self.base_url = base_url

    def generate_suggestions(
        self,
        analysis_result: Dict[str, Any]
    ) -> List[TestSuggestion]:
        """
        Generate test suggestions from pattern analysis

        Args:
            analysis_result: Output from PatternAnalyzer.analyze_traffic()

        Returns:
            List of TestSuggestion objects, sorted by priority
        """
        patterns = analysis_result.get('patterns', [])
        suggestions = []

        for pattern in patterns:
            suggestion = self._pattern_to_suggestion(pattern)
            if suggestion:
                suggestions.append(suggestion)

        # Sort by priority (HIGH > MEDIUM > LOW)
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        suggestions.sort(key=lambda s: priority_order.get(s.priority, 3))

        return suggestions

    def format_markdown(self, suggestions: List[TestSuggestion]) -> str:
        """
        Format suggestions as markdown document

        Args:
            suggestions: List of TestSuggestion objects

        Returns:
            Markdown-formatted string
        """
        lines = [
            "# TEST SUGGESTIONS",
            "",
            f"Found {len(suggestions)} testing opportunities.",
            ""
        ]

        for i, suggestion in enumerate(suggestions, 1):
            lines.append(suggestion.to_markdown(i))

        return "\n".join(lines)

    def _pattern_to_suggestion(self, pattern: Dict) -> Optional[TestSuggestion]:
        """Convert a pattern to a test suggestion"""
        pattern_type = pattern.get('type', 'general')
        severity = pattern.get('severity', 'MEDIUM')

        # Dispatch to specific handler
        if pattern_type == 'empty-array':
            return self._suggest_empty_array_test(pattern, severity)
        elif pattern_type == 'error-path':
            return self._suggest_error_path_test(pattern, severity)
        elif pattern_type == 'concurrency':
            return self._suggest_concurrency_test(pattern, severity)
        elif pattern_type == 'boundary':
            return self._suggest_boundary_test(pattern, severity)
        elif pattern_type == 'success-bias':
            return self._suggest_success_bias_test(pattern, severity)
        elif pattern_type == 'ai-insight':
            return self._suggest_ai_insight(pattern, severity)
        else:
            return self._suggest_generic(pattern, severity)

    def _suggest_empty_array_test(
        self,
        pattern: Dict,
        severity: str
    ) -> TestSuggestion:
        """Generate suggestion for empty array pattern"""
        title = pattern.get('title', 'Empty Array Test')
        description = pattern.get('description', '')
        evidence = pattern.get('evidence', [])

        # Extract endpoint from title (format: "Empty array never tested: GET /endpoint")
        endpoint = self._extract_endpoint_from_title(title)
        method = self._extract_method_from_endpoint(endpoint)
        path = self._extract_path_from_endpoint(endpoint)

        # Generate code snippet
        code_snippet = f"""test('should handle empty {path.split('/')[-1] or 'results'}', async ({{ request }}) => {{
  // Setup: Ensure database/filter returns no results
  const response = await request.{method.lower()}('{self.base_url}{path}');
  const data = await response.json();

  // Verify
  expect(response.status()).toBe(200);
  expect(Array.isArray(data)).toBe(true);
  expect(data.length).toBe(0); // Should return empty array, not null
}});"""

        return TestSuggestion(
            priority=severity,
            title=f"EDGE CASE: Empty Array - {endpoint}",
            observed=f"{endpoint} always returns data in captured traffic ({evidence[0] if evidence else 'multiple samples'})",
            missing="Test case for empty result set (zero matching records)",
            suggestions=[
                "Test with empty database or no matching filters",
                "Verify response is [] (empty array) not null or undefined",
                "Check pagination metadata shows total: 0",
                "Ensure proper JSON structure even when empty"
            ],
            code_snippet=code_snippet,
            pattern_type='empty-array'
        )

    def _suggest_error_path_test(
        self,
        pattern: Dict,
        severity: str
    ) -> TestSuggestion:
        """Generate suggestion for error path pattern"""
        title = pattern.get('title', 'Error Path Test')
        description = pattern.get('description', '')
        evidence = pattern.get('evidence', [])

        endpoint = self._extract_endpoint_from_title(title)
        method = self._extract_method_from_endpoint(endpoint)
        path = self._extract_path_from_endpoint(endpoint)

        # Generate code snippet for common error cases
        code_snippet = f"""test('should handle error cases for {endpoint}', async ({{ request }}) => {{
  // Test 404 - Resource not found
  const notFoundResponse = await request.{method.lower()}('{self.base_url}{path.replace("{id}", "99999")}');
  expect(notFoundResponse.status()).toBe(404);

  // Test 400 - Bad request (malformed input)
  const badRequestResponse = await request.{method.lower()}('{self.base_url}{path.replace("{id}", "invalid")}');
  expect(badRequestResponse.status()).toBe(400);

  // Test 401 - Unauthorized (missing auth)
  const unauthorizedResponse = await request.{method.lower()}('{self.base_url}{path}', {{
    headers: {{}} // No authorization header
  }});
  expect(unauthorizedResponse.status()).toBe(401);
}});"""

        return TestSuggestion(
            priority=severity,
            title=f"ERROR HANDLING: Missing Error Cases - {endpoint}",
            observed=f"{endpoint} only shows success responses (2xx) in captured traffic",
            missing="Error scenario testing (4xx, 5xx status codes)",
            suggestions=[
                "Test 404: Invalid/non-existent resource IDs",
                "Test 400: Malformed input, invalid data types",
                "Test 401: Missing or invalid authentication",
                "Test 403: Insufficient permissions",
                "Test 422: Validation errors (required fields, constraints)",
                "Test 429: Rate limiting (too many requests)",
                "Test 500: Server errors (simulate backend failure)"
            ],
            code_snippet=code_snippet,
            pattern_type='error-path'
        )

    def _suggest_concurrency_test(
        self,
        pattern: Dict,
        severity: str
    ) -> TestSuggestion:
        """Generate suggestion for concurrency pattern"""
        title = pattern.get('title', 'Concurrency Test')
        description = pattern.get('description', '')
        evidence = pattern.get('evidence', [])

        endpoint = self._extract_endpoint_from_title(title)
        method = self._extract_method_from_endpoint(endpoint)
        path = self._extract_path_from_endpoint(endpoint)

        code_snippet = f"""test('should handle concurrent requests safely', async ({{ request }}) => {{
  // Send multiple requests simultaneously
  const promises = [];
  for (let i = 0; i < 5; i++) {{
    promises.push(request.{method.lower()}('{self.base_url}{path}', {{
      data: {{ value: i }}
    }}));
  }}

  const responses = await Promise.all(promises);

  // Verify all succeeded
  responses.forEach(response => {{
    expect(response.status()).toBe(201);
  }});

  // Verify no duplicate processing or data corruption
  const bodies = await Promise.all(responses.map(r => r.json()));
  const ids = bodies.map(b => b.id);
  const uniqueIds = new Set(ids);
  expect(uniqueIds.size).toBe(ids.length); // No duplicates
}});"""

        return TestSuggestion(
            priority=severity,
            title=f"RACE CONDITION: Concurrent Writes - {endpoint}",
            observed=f"Detected {evidence[0] if evidence else 'multiple'} simultaneous write operations to {endpoint}",
            missing="Test for race conditions and proper isolation",
            suggestions=[
                "Test multiple concurrent writes to same resource",
                "Verify no duplicate processing (check for unique IDs)",
                "Check for lost updates (last write wins vs merge)",
                "Test optimistic locking (version checks)",
                "Verify database isolation levels",
                "Check for deadlocks or timeouts"
            ],
            code_snippet=code_snippet,
            pattern_type='concurrency'
        )

    def _suggest_boundary_test(
        self,
        pattern: Dict,
        severity: str
    ) -> TestSuggestion:
        """Generate suggestion for boundary condition pattern"""
        title = pattern.get('title', 'Boundary Test')
        description = pattern.get('description', '')
        evidence = pattern.get('evidence', [])

        endpoint = self._extract_endpoint_from_title(title)
        method = self._extract_method_from_endpoint(endpoint)
        path = self._extract_path_from_endpoint(endpoint)

        code_snippet = f"""test('should handle boundary values', async ({{ request }}) => {{
  // Test zero
  const zeroResponse = await request.{method.lower()}('{self.base_url}{path.replace("{id}", "0")}');
  expect(zeroResponse.status()).toBeGreaterThanOrEqual(200);

  // Test negative values
  const negativeResponse = await request.{method.lower()}('{self.base_url}{path.replace("{id}", "-1")}');
  expect([400, 404]).toContain(negativeResponse.status()); // Should reject or not find

  // Test maximum integer
  const maxIntResponse = await request.{method.lower()}('{self.base_url}{path.replace("{id}", "2147483647")}');
  expect(maxIntResponse.status()).toBeGreaterThanOrEqual(200);

  // Test very large number
  const largeResponse = await request.{method.lower()}('{self.base_url}{path.replace("{id}", "999999999")}');
  expect(largeResponse.status()).toBeGreaterThanOrEqual(200);
}});"""

        return TestSuggestion(
            priority=severity,
            title=f"BOUNDARY CONDITIONS: Edge Values - {endpoint}",
            observed=f"{endpoint} uses numeric parameters: {evidence[0] if evidence else 'range observed'}",
            missing="Boundary value testing (zero, negative, max values)",
            suggestions=[
                "Test zero (0) - often special case",
                "Test negative values - should reject or handle gracefully",
                "Test maximum integer (2^31-1 or 2^63-1)",
                "Test minimum integer values",
                "Test very large numbers (beyond expected range)",
                "Test decimal/float boundaries if applicable"
            ],
            code_snippet=code_snippet,
            pattern_type='boundary'
        )

    def _suggest_success_bias_test(
        self,
        pattern: Dict,
        severity: str
    ) -> TestSuggestion:
        """Generate suggestion for success bias pattern"""
        title = pattern.get('title', 'Success Bias')
        description = pattern.get('description', '')
        evidence = pattern.get('evidence', [])

        code_snippet = """test('error scenario coverage', async ({ request }) => {
  // Test invalid input
  const invalidResponse = await request.post('https://api.example.com/resource', {
    data: { invalid: 'data' }
  });
  expect(invalidResponse.status()).toBeGreaterThanOrEqual(400);

  // Test missing required fields
  const missingFieldsResponse = await request.post('https://api.example.com/resource', {
    data: {}
  });
  expect(missingFieldsResponse.status()).toBe(422);

  // Test unauthorized access
  const unauthorizedResponse = await request.get('https://api.example.com/protected', {
    headers: {} // No auth
  });
  expect(unauthorizedResponse.status()).toBe(401);

  // Test rate limiting
  const rateLimitPromises = [];
  for (let i = 0; i < 100; i++) {
    rateLimitPromises.push(request.get('https://api.example.com/resource'));
  }
  const rateLimitResponses = await Promise.all(rateLimitPromises);
  const rateLimited = rateLimitResponses.some(r => r.status() === 429);
  expect(rateLimited).toBe(true); // Should hit rate limit
});"""

        return TestSuggestion(
            priority=severity,
            title="SUCCESS BIAS: Insufficient Error Scenario Testing",
            observed=evidence[0] if evidence else "Most requests are successful (2xx responses)",
            missing="Comprehensive error scenario coverage",
            suggestions=[
                "Add tests for invalid input (400 Bad Request)",
                "Add tests for missing resources (404 Not Found)",
                "Add tests for authentication failures (401, 403)",
                "Add tests for validation errors (422 Unprocessable)",
                "Add tests for rate limiting (429 Too Many Requests)",
                "Add tests for server errors (500, 503)",
                "Test error response format and messaging"
            ],
            code_snippet=code_snippet,
            pattern_type='success-bias'
        )

    def _suggest_ai_insight(
        self,
        pattern: Dict,
        severity: str
    ) -> TestSuggestion:
        """Generate suggestion from AI insight"""
        title = pattern.get('title', 'AI-Identified Opportunity')
        description = pattern.get('description', '')

        return TestSuggestion(
            priority=severity,
            title=title,
            observed="AI analysis of traffic patterns",
            missing="Additional testing opportunities identified by Claude AI",
            suggestions=[description],
            code_snippet=None,
            pattern_type='ai-insight'
        )

    def _suggest_generic(
        self,
        pattern: Dict,
        severity: str
    ) -> TestSuggestion:
        """Generate generic suggestion"""
        title = pattern.get('title', 'Test Opportunity')
        description = pattern.get('description', '')
        suggestion = pattern.get('suggestion', '')

        return TestSuggestion(
            priority=severity,
            title=title,
            observed=description,
            missing="Testing gap identified",
            suggestions=[suggestion] if suggestion else ["Review pattern and add appropriate tests"],
            code_snippet=None,
            pattern_type='general'
        )

    def _extract_endpoint_from_title(self, title: str) -> str:
        """Extract endpoint from pattern title"""
        # Pattern titles typically end with ": GET /endpoint" or "endpoint"
        parts = title.split(':')
        if len(parts) > 1:
            return parts[-1].strip()
        return title

    def _extract_method_from_endpoint(self, endpoint: str) -> str:
        """Extract HTTP method from endpoint string"""
        methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        for method in methods:
            if endpoint.startswith(method):
                return method
        return 'GET'

    def _extract_path_from_endpoint(self, endpoint: str) -> str:
        """Extract path from endpoint string"""
        # Remove method prefix if present
        for method in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
            if endpoint.startswith(method):
                return endpoint[len(method):].strip()
        return endpoint


def generate_test_suggestions(
    json_file: str,
    output_file: Optional[str] = None,
    use_ai: bool = True,
    verbose: bool = True
) -> str:
    """
    Convenience function to generate test suggestions from traffic file

    Args:
        json_file: Path to captured traffic JSON
        output_file: Optional path to save markdown output
        use_ai: Whether to use AI enhancement
        verbose: Print status messages

    Returns:
        Markdown-formatted suggestions string
    """
    # Load and analyze traffic
    with open(json_file, 'r') as f:
        data = json.load(f)

    requests = data.get('requests', [])

    # Analyze patterns
    analyzer = PatternAnalyzer(use_ai=use_ai, verbose=verbose)
    analysis = analyzer.analyze_traffic(requests)

    # Generate suggestions
    # Try to extract base_url from first request
    base_url = 'https://api.example.com'
    if requests:
        first_url = requests[0].get('url', '')
        if first_url:
            parsed = urlparse(first_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

    suggester = TestSuggester(base_url=base_url)
    suggestions = suggester.generate_suggestions(analysis)
    markdown = suggester.format_markdown(suggestions)

    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            f.write(markdown)
        if verbose:
            print(f"✓ Saved test suggestions to {output_file}")

    return markdown
