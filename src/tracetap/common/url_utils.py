"""
TraceTap URL Utilities

Shared URL parsing, normalization, and matching utilities.
"""

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Dict, Any


class URLMatcher:
    """Handles URL matching logic with various strategies."""

    @staticmethod
    def normalize_url(url: str, strip_query: bool = False) -> str:
        """
        Normalize URL for comparison.

        Args:
            url: URL to normalize
            strip_query: If True, remove query parameters

        Returns:
            Normalized URL string
        """
        parsed = urlparse(url)

        if strip_query:
            # Remove query parameters
            return urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                '',
                '',
                ''
            ))

        # Sort query parameters for consistent comparison
        query_dict = parse_qs(parsed.query)
        sorted_query = urlencode(sorted(query_dict.items()), doseq=True)

        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            sorted_query,
            ''  # Remove fragment
        ))

    @staticmethod
    def urls_match(url1: str, url2: str, strict: bool = False) -> bool:
        """
        Compare two URLs for matching.

        Args:
            url1: First URL
            url2: Second URL
            strict: If True, requires exact match including query params

        Returns:
            True if URLs match according to criteria
        """
        # Exact match first
        if url1 == url2:
            return True

        # Normalize and compare
        norm1 = URLMatcher.normalize_url(url1, strip_query=not strict)
        norm2 = URLMatcher.normalize_url(url2, strip_query=not strict)

        if norm1 == norm2:
            return True

        # If not strict, try without query parameters
        if not strict:
            norm1_no_query = URLMatcher.normalize_url(url1, strip_query=True)
            norm2_no_query = URLMatcher.normalize_url(url2, strip_query=True)
            return norm1_no_query == norm2_no_query

        return False

    @staticmethod
    def extract_base_url(url: str) -> str:
        """
        Extract base URL without query parameters.

        Args:
            url: Full URL

        Returns:
            Base URL without query params
        """
        return URLMatcher.normalize_url(url, strip_query=True)

    @staticmethod
    def parse_url_components(url: str) -> Dict[str, Any]:
        """
        Parse URL into components for easy access.

        Args:
            url: URL to parse

        Returns:
            Dict with scheme, netloc, path, query, params, etc.
        """
        parsed = urlparse(url)
        return {
            'scheme': parsed.scheme,
            'netloc': parsed.netloc,
            'hostname': parsed.hostname,
            'port': parsed.port,
            'path': parsed.path,
            'params': parsed.params,
            'query': parsed.query,
            'query_dict': parse_qs(parsed.query),
            'fragment': parsed.fragment
        }
