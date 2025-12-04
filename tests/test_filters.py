"""
Tests for request filtering module.

Tests RequestFilter class logic for exact matching, wildcard matching,
regex patterns, and combined filters.
"""

import sys
from pathlib import Path
from unittest.mock import patch
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "tracetap" / "capture"))

from filters import RequestFilter


class TestRequestFilterInitialization:
    """Test suite for RequestFilter initialization."""

    def test_init_with_host_filters_only(self):
        """Test initialization with only host filters."""
        filters = RequestFilter(["api.example.com", "auth.example.com"])

        assert filters.host_filters == ["api.example.com", "auth.example.com"]
        assert filters.regex_pattern is None

    def test_init_with_empty_host_filters(self):
        """Test initialization with empty host filters list."""
        filters = RequestFilter([])

        assert filters.host_filters == []
        assert filters.regex_pattern is None

    def test_init_with_regex_pattern(self):
        """Test initialization with valid regex pattern."""
        filters = RequestFilter([], regex_pattern=".*\\.example\\.com")

        assert filters.host_filters == []
        assert filters.regex_pattern is not None
        assert filters.regex_pattern.pattern == ".*\\.example\\.com"

    def test_init_with_invalid_regex_pattern(self, capsys):
        """Test initialization with invalid regex pattern."""
        filters = RequestFilter([], regex_pattern="[invalid(")

        captured = capsys.readouterr()
        assert "Invalid regex pattern" in captured.out
        assert filters.regex_pattern is None

    def test_init_with_both_filters_and_regex(self):
        """Test initialization with both host filters and regex."""
        filters = RequestFilter(["api.example.com"], regex_pattern=".*\\.test\\.com")

        assert filters.host_filters == ["api.example.com"]
        assert filters.regex_pattern is not None


class TestShouldCaptureNoFilters:
    """Test suite for should_capture() with no filters configured."""

    def test_capture_all_when_no_filters(self):
        """Test that all requests are captured when no filters configured."""
        filters = RequestFilter([])

        result = filters.should_capture("example.com", "https://example.com/test")

        assert result is True

    def test_capture_any_host_without_filters(self):
        """Test capturing various hosts when no filters configured."""
        filters = RequestFilter([])

        assert filters.should_capture("api.test.com", "https://api.test.com") is True
        assert filters.should_capture("google.com", "https://google.com") is True
        assert filters.should_capture("localhost", "http://localhost:8080") is True


class TestShouldCaptureExactHostMatch:
    """Test suite for exact host matching."""

    def test_exact_match_single_host(self):
        """Test exact match with single host filter."""
        filters = RequestFilter(["api.example.com"])

        result = filters.should_capture("api.example.com", "https://api.example.com/users")

        assert result is True

    def test_exact_match_multiple_hosts(self):
        """Test exact match with multiple host filters."""
        filters = RequestFilter(["api.example.com", "auth.example.com", "data.example.com"])

        assert filters.should_capture("api.example.com", "https://api.example.com") is True
        assert filters.should_capture("auth.example.com", "https://auth.example.com") is True
        assert filters.should_capture("data.example.com", "https://data.example.com") is True

    def test_exact_match_no_match(self):
        """Test that non-matching hosts are not captured."""
        filters = RequestFilter(["api.example.com"])

        result = filters.should_capture("other.example.com", "https://other.example.com")

        assert result is False

    def test_exact_match_case_sensitive(self):
        """Test that exact matching is case-sensitive."""
        filters = RequestFilter(["api.example.com"])

        result = filters.should_capture("API.EXAMPLE.COM", "https://API.EXAMPLE.COM")

        assert result is False

    def test_exact_match_with_port(self):
        """Test exact matching doesn't match host with port."""
        filters = RequestFilter(["api.example.com"])

        # Host should not include port number for matching
        result = filters.should_capture("api.example.com:8080", "https://api.example.com:8080")

        assert result is False


class TestShouldCaptureWildcardMatch:
    """Test suite for wildcard matching."""

    def test_wildcard_matches_subdomain(self):
        """Test wildcard matches subdomains."""
        filters = RequestFilter(["*.example.com"])

        assert filters.should_capture("api.example.com", "https://api.example.com") is True
        assert filters.should_capture("auth.example.com", "https://auth.example.com") is True
        assert filters.should_capture("data.example.com", "https://data.example.com") is True

    def test_wildcard_matches_base_domain(self):
        """Test wildcard matches the base domain itself."""
        filters = RequestFilter(["*.example.com"])

        result = filters.should_capture("example.com", "https://example.com")

        assert result is True

    def test_wildcard_matches_nested_subdomain(self):
        """Test wildcard matches nested subdomains."""
        filters = RequestFilter(["*.example.com"])

        result = filters.should_capture("api.prod.example.com", "https://api.prod.example.com")

        assert result is True

    def test_wildcard_no_match_different_domain(self):
        """Test wildcard doesn't match different domain."""
        filters = RequestFilter(["*.example.com"])

        result = filters.should_capture("api.test.com", "https://api.test.com")

        assert result is False

    def test_wildcard_no_match_partial_domain(self):
        """Test wildcard doesn't match partial domain names."""
        filters = RequestFilter(["*.example.com"])

        result = filters.should_capture("notexample.com", "https://notexample.com")

        assert result is False

    def test_multiple_wildcards(self):
        """Test multiple wildcard filters."""
        filters = RequestFilter(["*.example.com", "*.test.com"])

        assert filters.should_capture("api.example.com", "https://api.example.com") is True
        assert filters.should_capture("auth.test.com", "https://auth.test.com") is True
        assert filters.should_capture("other.org", "https://other.org") is False

    def test_wildcard_tld_only(self):
        """Test wildcard with TLD only."""
        filters = RequestFilter(["*.com"])

        assert filters.should_capture("example.com", "https://example.com") is True
        assert filters.should_capture("api.example.com", "https://api.example.com") is True


class TestShouldCaptureRegexMatch:
    """Test suite for regex pattern matching."""

    def test_regex_matches_url(self):
        """Test regex pattern matches against URL."""
        filters = RequestFilter([], regex_pattern=".*\\/api\\/.*")

        result = filters.should_capture("example.com", "https://example.com/api/users")

        assert result is True

    def test_regex_matches_host(self):
        """Test regex pattern matches against host."""
        filters = RequestFilter([], regex_pattern=".*\\.example\\.com")

        result = filters.should_capture("api.example.com", "https://api.example.com")

        assert result is True

    def test_regex_no_match(self):
        """Test regex pattern doesn't match."""
        filters = RequestFilter([], regex_pattern=".*\\/admin\\/.*")

        result = filters.should_capture("example.com", "https://example.com/users")

        assert result is False

    def test_regex_complex_pattern(self):
        """Test complex regex pattern."""
        filters = RequestFilter([], regex_pattern="^https://api\\.(dev|staging|prod)\\.example\\.com")

        assert filters.should_capture("api.dev.example.com", "https://api.dev.example.com/test") is True
        assert filters.should_capture("api.staging.example.com", "https://api.staging.example.com") is True
        assert filters.should_capture("api.local.example.com", "https://api.local.example.com") is False

    def test_regex_case_insensitive(self):
        """Test regex pattern with case-insensitive flag."""
        filters = RequestFilter([], regex_pattern="(?i).*\\.EXAMPLE\\.com")

        result = filters.should_capture("api.example.com", "https://api.example.com")

        assert result is True


class TestShouldCaptureCombinedFilters:
    """Test suite for combined host filters and regex."""

    def test_combined_host_matches(self):
        """Test host filter matches when both filters present."""
        filters = RequestFilter(["api.example.com"], regex_pattern=".*\\.test\\.com")

        result = filters.should_capture("api.example.com", "https://api.example.com")

        assert result is True

    def test_combined_regex_matches(self):
        """Test regex matches when both filters present."""
        filters = RequestFilter(["api.example.com"], regex_pattern=".*\\.test\\.com")

        result = filters.should_capture("auth.test.com", "https://auth.test.com")

        assert result is True

    def test_combined_neither_matches(self):
        """Test neither filter matches."""
        filters = RequestFilter(["api.example.com"], regex_pattern=".*\\.test\\.com")

        result = filters.should_capture("other.org", "https://other.org")

        assert result is False

    def test_combined_or_logic(self):
        """Test that filters use OR logic (any match succeeds)."""
        filters = RequestFilter(["exact.com"], regex_pattern=".*regex.*")

        # Exact match
        assert filters.should_capture("exact.com", "https://exact.com") is True
        # Regex match
        assert filters.should_capture("test.com", "https://test.com/regex/path") is True
        # No match
        assert filters.should_capture("other.com", "https://other.com/other") is False


class TestShouldCaptureVerboseMode:
    """Test suite for verbose output."""

    def test_verbose_capture_logged(self, capsys):
        """Test verbose output when request is captured."""
        filters = RequestFilter(["api.example.com"])

        filters.should_capture("api.example.com", "https://api.example.com", verbose=True)

        captured = capsys.readouterr()
        assert "✅ [CAPTURE]" in captured.out
        assert "api.example.com" in captured.out
        assert "exact match" in captured.out

    def test_verbose_skip_logged(self, capsys):
        """Test verbose output when request is skipped."""
        filters = RequestFilter(["api.example.com"])

        filters.should_capture("other.com", "https://other.com", verbose=True)

        captured = capsys.readouterr()
        assert "❌ [SKIP]" in captured.out
        assert "other.com" in captured.out

    def test_verbose_wildcard_match(self, capsys):
        """Test verbose output for wildcard match."""
        filters = RequestFilter(["*.example.com"])

        filters.should_capture("api.example.com", "https://api.example.com", verbose=True)

        captured = capsys.readouterr()
        assert "✅ [CAPTURE]" in captured.out
        assert "wildcard match" in captured.out

    def test_verbose_regex_match(self, capsys):
        """Test verbose output for regex match."""
        filters = RequestFilter([], regex_pattern=".*\\.example\\.com")

        filters.should_capture("api.example.com", "https://api.example.com", verbose=True)

        captured = capsys.readouterr()
        assert "✅ [CAPTURE]" in captured.out
        assert "regex match" in captured.out

    def test_verbose_disabled_no_output(self, capsys):
        """Test no output when verbose is disabled."""
        filters = RequestFilter(["api.example.com"])

        filters.should_capture("api.example.com", "https://api.example.com", verbose=False)

        captured = capsys.readouterr()
        assert captured.out == ""


class TestEdgeCases:
    """Test suite for edge cases and special scenarios."""

    def test_empty_host_string(self):
        """Test handling of empty host string."""
        filters = RequestFilter(["example.com"])

        result = filters.should_capture("", "https://example.com")

        assert result is False

    def test_empty_url_string(self):
        """Test handling of empty URL string."""
        filters = RequestFilter([], regex_pattern=".*test.*")

        result = filters.should_capture("example.com", "")

        assert result is False

    def test_special_characters_in_host(self):
        """Test handling of special characters in host."""
        filters = RequestFilter(["api-test.example.com"])

        result = filters.should_capture("api-test.example.com", "https://api-test.example.com")

        assert result is True

    def test_ipv4_address_host(self):
        """Test handling of IPv4 address as host."""
        filters = RequestFilter(["192.168.1.1"])

        result = filters.should_capture("192.168.1.1", "http://192.168.1.1")

        assert result is True

    def test_localhost(self):
        """Test handling of localhost."""
        filters = RequestFilter(["localhost"])

        result = filters.should_capture("localhost", "http://localhost:8080")

        assert result is True

    def test_very_long_host_list(self):
        """Test handling of many host filters."""
        hosts = [f"host{i}.example.com" for i in range(100)]
        filters = RequestFilter(hosts)

        result = filters.should_capture("host50.example.com", "https://host50.example.com")

        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
