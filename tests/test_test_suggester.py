"""
Tests for Test Suggestion Engine

Tests suggestion generation and markdown formatting.
"""

import json
import pytest
from pathlib import Path
import sys
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from tracetap.ai.test_suggester import (
    TestSuggestion,
    TestSuggester,
    generate_test_suggestions
)


class TestTestSuggestion:
    """Test TestSuggestion class"""

    def test_suggestion_creation(self):
        suggestion = TestSuggestion(
            priority='HIGH',
            title='Test Empty Arrays',
            observed='GET /users always returns data',
            missing='Empty array test case',
            suggestions=['Test with empty database', 'Verify response is []'],
            code_snippet='test code here',
            pattern_type='empty-array'
        )

        assert suggestion.priority == 'HIGH'
        assert suggestion.title == 'Test Empty Arrays'
        assert len(suggestion.suggestions) == 2

    def test_suggestion_to_markdown(self):
        suggestion = TestSuggestion(
            priority='HIGH',
            title='Error Handling',
            observed='Only 2xx responses seen',
            missing='Error scenario testing',
            suggestions=['Test 404', 'Test 401'],
            code_snippet='test("error", async () => {});'
        )

        markdown = suggestion.to_markdown(1)

        assert '## 1. Error Handling (Priority: HIGH)' in markdown
        assert '**Observed:** Only 2xx responses seen' in markdown
        assert '**Missing Test:** Error scenario testing' in markdown
        assert '- Test 404' in markdown
        assert '- Test 401' in markdown
        assert '```typescript' in markdown
        assert 'test("error"' in markdown

    def test_suggestion_without_code_snippet(self):
        suggestion = TestSuggestion(
            priority='MEDIUM',
            title='General Test',
            observed='Something observed',
            missing='Something missing',
            suggestions=['Do this'],
            code_snippet=None
        )

        markdown = suggestion.to_markdown(1)

        assert '**Observed:**' in markdown
        assert '**Missing Test:**' in markdown
        assert '- Do this' in markdown
        assert '```typescript' not in markdown


class TestTestSuggester:
    """Test TestSuggester core functionality"""

    def test_initialization(self):
        suggester = TestSuggester(base_url='https://api.example.com')
        assert suggester.base_url == 'https://api.example.com'

    def test_generate_suggestions_empty_analysis(self):
        suggester = TestSuggester()
        result = suggester.generate_suggestions({'patterns': []})

        assert len(result) == 0

    def test_extract_endpoint_from_title(self):
        suggester = TestSuggester()

        # Format: "Title: GET /endpoint"
        endpoint = suggester._extract_endpoint_from_title("Empty array never tested: GET /users")
        assert endpoint == "GET /users"

        # Format without method
        endpoint = suggester._extract_endpoint_from_title("Test endpoint")
        assert endpoint == "Test endpoint"

    def test_extract_method_from_endpoint(self):
        suggester = TestSuggester()

        assert suggester._extract_method_from_endpoint("GET /users") == "GET"
        assert suggester._extract_method_from_endpoint("POST /orders") == "POST"
        assert suggester._extract_method_from_endpoint("PUT /items/123") == "PUT"
        assert suggester._extract_method_from_endpoint("/users") == "GET"  # Default

    def test_extract_path_from_endpoint(self):
        suggester = TestSuggester()

        assert suggester._extract_path_from_endpoint("GET /users") == "/users"
        assert suggester._extract_path_from_endpoint("POST /orders/123") == "/orders/123"
        assert suggester._extract_path_from_endpoint("/items") == "/items"


class TestEmptyArraySuggestion:
    """Test empty array suggestion generation"""

    def test_generates_empty_array_suggestion(self):
        suggester = TestSuggester()

        pattern = {
            'type': 'empty-array',
            'severity': 'HIGH',
            'title': 'Empty array never tested: GET /users',
            'description': 'GET /users always returns data',
            'evidence': ['Observed 5 responses, all non-empty'],
            'suggestion': 'Test with empty conditions'
        }

        suggestion = suggester._suggest_empty_array_test(pattern, 'HIGH')

        assert suggestion.priority == 'HIGH'
        assert 'Empty Array' in suggestion.title
        assert 'GET /users' in suggestion.title
        assert suggestion.code_snippet is not None
        assert 'expect(Array.isArray(data)).toBe(true)' in suggestion.code_snippet
        assert 'expect(data.length).toBe(0)' in suggestion.code_snippet

    def test_empty_array_suggestion_includes_endpoint(self):
        suggester = TestSuggester(base_url='https://api.test.com')

        pattern = {
            'type': 'empty-array',
            'severity': 'MEDIUM',
            'title': 'Empty array never tested: GET /orders',
            'description': 'Orders always populated',
            'evidence': [],
            'suggestion': 'Test empty'
        }

        suggestion = suggester._suggest_empty_array_test(pattern, 'MEDIUM')

        assert 'https://api.test.com/orders' in suggestion.code_snippet
        assert 'request.get' in suggestion.code_snippet


class TestErrorPathSuggestion:
    """Test error path suggestion generation"""

    def test_generates_error_path_suggestion(self):
        suggester = TestSuggester()

        pattern = {
            'type': 'error-path',
            'severity': 'HIGH',
            'title': 'No error cases tested: GET /users/{id}',
            'description': 'Only 2xx seen',
            'evidence': ['Observed status codes: [200, 201]'],
            'suggestion': 'Test error paths'
        }

        suggestion = suggester._suggest_error_path_test(pattern, 'HIGH')

        assert suggestion.priority == 'HIGH'
        assert 'ERROR HANDLING' in suggestion.title
        assert suggestion.code_snippet is not None
        assert '404' in suggestion.code_snippet
        assert '400' in suggestion.code_snippet
        assert '401' in suggestion.code_snippet

    def test_error_path_includes_multiple_scenarios(self):
        suggester = TestSuggester()

        pattern = {
            'type': 'error-path',
            'severity': 'HIGH',
            'title': 'No error cases tested: POST /orders',
            'description': 'Missing error tests',
            'evidence': [],
            'suggestion': 'Add error tests'
        }

        suggestion = suggester._suggest_error_path_test(pattern, 'HIGH')

        # Should suggest multiple error types
        assert 'Test 404' in suggestion.suggestions or any('404' in s for s in suggestion.suggestions)
        assert 'Test 400' in suggestion.suggestions or any('400' in s for s in suggestion.suggestions)
        assert 'Test 401' in suggestion.suggestions or any('401' in s for s in suggestion.suggestions)


class TestConcurrencySuggestion:
    """Test concurrency suggestion generation"""

    def test_generates_concurrency_suggestion(self):
        suggester = TestSuggester()

        pattern = {
            'type': 'concurrency',
            'severity': 'HIGH',
            'title': 'Concurrent writes detected: POST /orders',
            'description': 'Multiple simultaneous writes',
            'evidence': ['2 concurrent writes'],
            'suggestion': 'Test race conditions'
        }

        suggestion = suggester._suggest_concurrency_test(pattern, 'HIGH')

        assert suggestion.priority == 'HIGH'
        assert 'RACE CONDITION' in suggestion.title or 'Concurrent' in suggestion.title
        assert suggestion.code_snippet is not None
        assert 'Promise.all' in suggestion.code_snippet
        assert 'for (let i = 0' in suggestion.code_snippet
        assert 'No duplicates' in suggestion.code_snippet


class TestBoundarySuggestion:
    """Test boundary condition suggestion generation"""

    def test_generates_boundary_suggestion(self):
        suggester = TestSuggester()

        pattern = {
            'type': 'boundary',
            'severity': 'MEDIUM',
            'title': 'Boundary conditions untested: GET /items/{id}',
            'description': 'Missing boundary tests',
            'evidence': ['Values seen: 1 to 100'],
            'suggestion': 'Test boundaries'
        }

        suggestion = suggester._suggest_boundary_test(pattern, 'MEDIUM')

        assert suggestion.priority == 'MEDIUM'
        assert 'BOUNDARY' in suggestion.title
        assert suggestion.code_snippet is not None
        assert '"0"' in suggestion.code_snippet or '0' in suggestion.code_snippet
        assert '"-1"' in suggestion.code_snippet or 'negative' in suggestion.code_snippet.lower()

    def test_boundary_includes_edge_values(self):
        suggester = TestSuggester()

        pattern = {
            'type': 'boundary',
            'severity': 'MEDIUM',
            'title': 'Boundary conditions untested: POST /items',
            'description': 'Edge values not tested',
            'evidence': [],
            'suggestion': 'Test boundaries'
        }

        suggestion = suggester._suggest_boundary_test(pattern, 'MEDIUM')

        # Should suggest multiple boundary values
        suggestions_text = ' '.join(suggestion.suggestions).lower()
        assert 'zero' in suggestions_text
        assert 'negative' in suggestions_text
        assert 'maximum' in suggestions_text or 'large' in suggestions_text


class TestSuccessBiasSuggestion:
    """Test success bias suggestion generation"""

    def test_generates_success_bias_suggestion(self):
        suggester = TestSuggester()

        pattern = {
            'type': 'success-bias',
            'severity': 'HIGH',
            'title': 'Success bias detected',
            'description': '95% requests are successful',
            'evidence': ['190 success / 200 total'],
            'suggestion': 'Add error tests'
        }

        suggestion = suggester._suggest_success_bias_test(pattern, 'HIGH')

        assert suggestion.priority == 'HIGH'
        assert 'SUCCESS BIAS' in suggestion.title
        assert suggestion.code_snippet is not None
        assert len(suggestion.suggestions) >= 5  # Multiple error scenarios

    def test_success_bias_includes_comprehensive_errors(self):
        suggester = TestSuggester()

        pattern = {
            'type': 'success-bias',
            'severity': 'HIGH',
            'title': 'Success bias',
            'description': 'Too many successes',
            'evidence': [],
            'suggestion': 'Test errors'
        }

        suggestion = suggester._suggest_success_bias_test(pattern, 'HIGH')

        suggestions_text = ' '.join(suggestion.suggestions).lower()
        assert 'invalid' in suggestions_text or '400' in suggestions_text
        assert '404' in suggestions_text or 'missing' in suggestions_text
        assert 'auth' in suggestions_text or '401' in suggestions_text


class TestAIInsightSuggestion:
    """Test AI insight suggestion generation"""

    def test_generates_ai_insight_suggestion(self):
        suggester = TestSuggester()

        pattern = {
            'type': 'ai-insight',
            'severity': 'MEDIUM',
            'title': 'AI-identified opportunity',
            'description': 'Additional testing needed for security',
            'evidence': ['Claude AI analysis'],
            'suggestion': 'Review AI suggestions'
        }

        suggestion = suggester._suggest_ai_insight(pattern, 'MEDIUM')

        assert suggestion.priority == 'MEDIUM'
        assert 'AI' in suggestion.title
        assert 'AI analysis' in suggestion.observed
        assert suggestion.code_snippet is None  # AI insights don't have code


class TestSuggestionPrioritization:
    """Test suggestion sorting and prioritization"""

    def test_sorts_by_priority(self):
        suggester = TestSuggester()

        analysis = {
            'patterns': [
                {'type': 'test', 'severity': 'LOW', 'title': 'Low', 'description': 'Low priority', 'evidence': [], 'suggestion': 'Fix'},
                {'type': 'test', 'severity': 'HIGH', 'title': 'High', 'description': 'High priority', 'evidence': [], 'suggestion': 'Fix'},
                {'type': 'test', 'severity': 'MEDIUM', 'title': 'Medium', 'description': 'Medium priority', 'evidence': [], 'suggestion': 'Fix'},
            ]
        }

        suggestions = suggester.generate_suggestions(analysis)

        # Should be sorted HIGH > MEDIUM > LOW
        assert suggestions[0].priority == 'HIGH'
        assert suggestions[1].priority == 'MEDIUM'
        assert suggestions[2].priority == 'LOW'


class TestMarkdownFormatting:
    """Test markdown output formatting"""

    def test_format_markdown_with_suggestions(self):
        suggester = TestSuggester()

        suggestions = [
            TestSuggestion(
                priority='HIGH',
                title='Test 1',
                observed='Obs 1',
                missing='Miss 1',
                suggestions=['Sug 1'],
                code_snippet='code 1'
            ),
            TestSuggestion(
                priority='MEDIUM',
                title='Test 2',
                observed='Obs 2',
                missing='Miss 2',
                suggestions=['Sug 2'],
                code_snippet=None
            )
        ]

        markdown = suggester.format_markdown(suggestions)

        assert '# TEST SUGGESTIONS' in markdown
        assert 'Found 2 testing opportunities' in markdown
        assert '## 1. Test 1 (Priority: HIGH)' in markdown
        assert '## 2. Test 2 (Priority: MEDIUM)' in markdown
        assert '```typescript' in markdown  # First has code

    def test_format_markdown_empty(self):
        suggester = TestSuggester()

        markdown = suggester.format_markdown([])

        assert '# TEST SUGGESTIONS' in markdown
        assert 'Found 0 testing opportunities' in markdown


class TestIntegration:
    """Integration tests with complete workflow"""

    def test_end_to_end_suggestion_generation(self):
        suggester = TestSuggester(base_url='https://api.test.com')

        # Simulate pattern analyzer output
        analysis = {
            'patterns': [
                {
                    'type': 'empty-array',
                    'severity': 'HIGH',
                    'title': 'Empty array never tested: GET /users',
                    'description': 'Always returns data',
                    'evidence': ['5 samples, all non-empty'],
                    'suggestion': 'Test empty'
                },
                {
                    'type': 'error-path',
                    'severity': 'HIGH',
                    'title': 'No error cases tested: POST /orders',
                    'description': 'Only 2xx seen',
                    'evidence': [],
                    'suggestion': 'Test errors'
                }
            ],
            'stats': {
                'total_requests': 10,
                'success_rate': 1.0
            }
        }

        suggestions = suggester.generate_suggestions(analysis)

        assert len(suggestions) == 2
        assert all(s.priority == 'HIGH' for s in suggestions)
        assert all(s.code_snippet is not None for s in suggestions)

        markdown = suggester.format_markdown(suggestions)

        assert '# TEST SUGGESTIONS' in markdown
        assert 'GET /users' in markdown
        assert 'POST /orders' in markdown
        assert '```typescript' in markdown

    def test_generate_test_suggestions_convenience_function(self, tmp_path):
        # Create temporary traffic file
        traffic_file = tmp_path / "test_traffic.json"
        output_file = tmp_path / "suggestions.md"

        data = {
            'requests': [
                {'method': 'GET', 'url': 'http://api.test/users', 'status_code': 200, 'response_body': json.dumps([1, 2])},
                {'method': 'GET', 'url': 'http://api.test/users', 'status_code': 200, 'response_body': json.dumps([3, 4])},
                {'method': 'GET', 'url': 'http://api.test/users', 'status_code': 200, 'response_body': json.dumps([5])},
            ]
        }
        traffic_file.write_text(json.dumps(data))

        # Generate suggestions
        markdown = generate_test_suggestions(
            json_file=str(traffic_file),
            output_file=str(output_file),
            use_ai=False,
            verbose=False
        )

        # Check output file was created
        assert output_file.exists()
        content = output_file.read_text()
        assert '# TEST SUGGESTIONS' in content

        # Check returned markdown
        assert '# TEST SUGGESTIONS' in markdown

    def test_handles_no_patterns(self, tmp_path):
        traffic_file = tmp_path / "balanced_traffic.json"

        # Well-balanced traffic with no issues
        data = {
            'requests': [
                {'method': 'GET', 'url': 'http://api.test/users', 'status_code': 200},
                {'method': 'GET', 'url': 'http://api.test/users', 'status_code': 404},
            ]
        }
        traffic_file.write_text(json.dumps(data))

        markdown = generate_test_suggestions(
            json_file=str(traffic_file),
            use_ai=False,
            verbose=False
        )

        assert '# TEST SUGGESTIONS' in markdown
        assert 'Found 0 testing opportunities' in markdown


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
