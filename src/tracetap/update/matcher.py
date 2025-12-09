"""
Request matching logic for collection updates.

Matches requests from existing Postman collection to new captures
using multi-stage matching strategies.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass


@dataclass
class MatchResult:
    """Result of matching a request."""
    matched: bool
    existing_request: Optional[Dict[str, Any]] = None
    capture: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    match_type: str = "none"  # exact, base_url, pattern, fuzzy
    reason: str = ""


class RequestMatcher:
    """Matches requests between existing collection and new captures."""

    def __init__(self, min_confidence: float = 0.75, collection_variables: Optional[Dict[str, str]] = None):
        """
        Initialize matcher.

        Args:
            min_confidence: Minimum confidence score for auto-matching
            collection_variables: Dictionary of collection variable key-value pairs
        """
        self.min_confidence = min_confidence
        self.collection_variables = collection_variables or {}

        # ID patterns for normalization
        self.uuid_pattern = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE)
        self.numeric_id_pattern = re.compile(r'/\d{3,}(?:/|$)')
        self.objectid_pattern = re.compile(r'[0-9a-f]{24}')

    def match_collections(
        self,
        existing_requests: List[Dict[str, Any]],
        captures: List[Dict[str, Any]]
    ) -> List[MatchResult]:
        """
        Match all requests from existing collection to captures.

        Returns list of MatchResults (one per existing request).
        """
        results = []
        used_captures = set()

        for existing in existing_requests:
            match = self.find_best_match(existing, captures, used_captures)
            results.append(match)

            if match.matched and match.capture:
                # Mark this capture as used
                capture_idx = captures.index(match.capture)
                used_captures.add(capture_idx)

        return results

    def find_best_match(
        self,
        existing_request: Dict[str, Any],
        captures: List[Dict[str, Any]],
        used_captures: set
    ) -> MatchResult:
        """
        Find best matching capture for an existing request.

        Uses multi-stage matching:
        1. Exact match (method + URL)
        2. Base URL match (method + URL without query params)
        3. Pattern match (method + normalized URL with ID patterns)
        4. Fuzzy match (similarity scoring)
        """
        request_data = existing_request.get('request', {})
        method = request_data.get('method', 'GET').upper()

        # Extract URL from various possible formats
        url = self._extract_url(request_data)

        if not url:
            return MatchResult(matched=False, reason="No URL in existing request")

        # Stage 1: Exact match
        for idx, capture in enumerate(captures):
            if idx in used_captures:
                continue

            if self._exact_match(method, url, capture):
                return MatchResult(
                    matched=True,
                    existing_request=existing_request,
                    capture=capture,
                    confidence=1.0,
                    match_type="exact",
                    reason="Exact method + URL match"
                )

        # Stage 2: Base URL match (ignore query params)
        for idx, capture in enumerate(captures):
            if idx in used_captures:
                continue

            confidence = self._base_url_match(method, url, capture)
            if confidence >= 0.9:
                return MatchResult(
                    matched=True,
                    existing_request=existing_request,
                    capture=capture,
                    confidence=confidence,
                    match_type="base_url",
                    reason="Method + base URL match (query params differ)"
                )

        # Stage 3: Pattern match (normalize IDs)
        best_pattern_match = None
        best_pattern_score = 0.0

        for idx, capture in enumerate(captures):
            if idx in used_captures:
                continue

            confidence = self._pattern_match(method, url, capture)
            if confidence > best_pattern_score:
                best_pattern_score = confidence
                best_pattern_match = capture

        if best_pattern_score >= 0.75:
            return MatchResult(
                matched=True,
                existing_request=existing_request,
                capture=best_pattern_match,
                confidence=best_pattern_score,
                match_type="pattern",
                reason="Method + normalized URL pattern match"
            )

        # Stage 4: Fuzzy match
        best_fuzzy_match = None
        best_fuzzy_score = 0.0

        for idx, capture in enumerate(captures):
            if idx in used_captures:
                continue

            confidence = self._fuzzy_match(method, url, request_data, capture)
            if confidence > best_fuzzy_score:
                best_fuzzy_score = confidence
                best_fuzzy_match = capture

        if best_fuzzy_score >= self.min_confidence:
            return MatchResult(
                matched=True,
                existing_request=existing_request,
                capture=best_fuzzy_match,
                confidence=best_fuzzy_score,
                match_type="fuzzy",
                reason=f"Fuzzy match (similarity: {best_fuzzy_score:.0%})"
            )

        # No match found
        return MatchResult(
            matched=False,
            existing_request=existing_request,
            reason=f"No match found (best score: {best_fuzzy_score:.0%})"
        )

    def _expand_variables(self, text: str) -> str:
        """
        Expand {{variable}} references in text using collection variables.

        Args:
            text: Text that may contain {{variable}} references

        Returns:
            Text with variables expanded
        """
        if not text or not self.collection_variables:
            return text

        # Replace all {{variable}} patterns
        def replace_var(match):
            var_name = match.group(1)
            return self.collection_variables.get(var_name, match.group(0))

        return re.sub(r'\{\{([^}]+)\}\}', replace_var, text)

    def _extract_url(self, request_data: Dict[str, Any]) -> Optional[str]:
        """Extract URL from various request formats and expand variables."""
        # Try raw URL first
        url_data = request_data.get('url', {})

        url = None

        if isinstance(url_data, str):
            url = url_data
        elif isinstance(url_data, dict):
            raw_url = url_data.get('raw')
            if raw_url:
                url = raw_url
            else:
                # Reconstruct from components
                protocol = url_data.get('protocol', 'https')
                host = url_data.get('host', [])
                path = url_data.get('path', [])

                if host and path:
                    host_str = '.'.join(host) if isinstance(host, list) else host
                    path_str = '/' + '/'.join(path) if isinstance(path, list) else path
                    url = f"{protocol}://{host_str}{path_str}"

        # Expand variables if URL was found
        if url:
            url = self._expand_variables(url)

        return url

    def _exact_match(self, method: str, url: str, capture: Dict[str, Any]) -> bool:
        """Check for exact method + URL match."""
        capture_method = capture.get('method', 'GET').upper()
        capture_url = capture.get('url', '')

        return method == capture_method and url == capture_url

    def _base_url_match(self, method: str, url: str, capture: Dict[str, Any]) -> float:
        """Check for method + base URL match (ignore query params)."""
        capture_method = capture.get('method', 'GET').upper()
        capture_url = capture.get('url', '')

        if method != capture_method:
            return 0.0

        # Strip query parameters
        base_url = url.split('?')[0]
        capture_base_url = capture_url.split('?')[0]

        if base_url == capture_base_url:
            return 0.9  # High confidence but not exact

        return 0.0

    def _pattern_match(self, method: str, url: str, capture: Dict[str, Any]) -> float:
        """Check for pattern match with ID normalization."""
        capture_method = capture.get('method', 'GET').upper()
        capture_url = capture.get('url', '')

        if method != capture_method:
            return 0.0

        # Normalize both URLs (replace IDs with {id})
        normalized_url = self._normalize_url(url)
        normalized_capture_url = self._normalize_url(capture_url)

        if normalized_url == normalized_capture_url:
            return 0.85  # Good confidence

        # Calculate path similarity
        url_parts = normalized_url.split('/')
        capture_parts = normalized_capture_url.split('/')

        if len(url_parts) == len(capture_parts):
            matches = sum(1 for a, b in zip(url_parts, capture_parts) if a == b)
            similarity = matches / len(url_parts)

            if similarity >= 0.8:
                return 0.75 + (similarity - 0.8) * 0.5  # 0.75-0.85 range

        return 0.0

    def _normalize_url(self, url: str) -> str:
        """Normalize URL by replacing IDs with {id} placeholder."""
        # Strip query parameters
        base_url = url.split('?')[0]

        # Replace UUIDs
        normalized = self.uuid_pattern.sub('{id}', base_url)

        # Replace numeric IDs (3+ digits)
        normalized = self.numeric_id_pattern.sub('/{id}/', normalized)

        # Replace MongoDB ObjectIds
        normalized = self.objectid_pattern.sub('{id}', normalized)

        # Clean up any double slashes
        normalized = re.sub(r'/+', '/', normalized)

        return normalized

    def _fuzzy_match(
        self,
        method: str,
        url: str,
        request_data: Dict[str, Any],
        capture: Dict[str, Any]
    ) -> float:
        """Calculate fuzzy similarity score."""
        capture_method = capture.get('method', 'GET').upper()
        capture_url = capture.get('url', '')

        # Method match (30% weight)
        method_score = 1.0 if method == capture_method else 0.0

        # URL similarity (50% weight)
        url_score = self._url_similarity(url, capture_url)

        # Path structure similarity (20% weight)
        path_score = self._path_structure_similarity(url, capture_url)

        # Weighted average
        total_score = (
            method_score * 0.3 +
            url_score * 0.5 +
            path_score * 0.2
        )

        return total_score

    def _url_similarity(self, url1: str, url2: str) -> float:
        """Calculate character-level similarity between URLs."""
        # Simple Levenshtein-like approach
        url1_clean = url1.split('?')[0].lower()
        url2_clean = url2.split('?')[0].lower()

        if url1_clean == url2_clean:
            return 1.0

        # Calculate common prefix length
        common_prefix = 0
        for c1, c2 in zip(url1_clean, url2_clean):
            if c1 == c2:
                common_prefix += 1
            else:
                break

        max_len = max(len(url1_clean), len(url2_clean))
        if max_len == 0:
            return 0.0

        return common_prefix / max_len

    def _path_structure_similarity(self, url1: str, url2: str) -> float:
        """Compare path segment structure."""
        path1 = urlparse(url1).path
        path2 = urlparse(url2).path

        parts1 = [p for p in path1.split('/') if p]
        parts2 = [p for p in path2.split('/') if p]

        if len(parts1) != len(parts2):
            return 0.0

        if not parts1:
            return 1.0

        # Count matching segments
        matches = sum(1 for a, b in zip(parts1, parts2) if a == b)
        return matches / len(parts1)

    def find_unmatched_captures(
        self,
        captures: List[Dict[str, Any]],
        match_results: List[MatchResult]
    ) -> List[Dict[str, Any]]:
        """Find captures that weren't matched to any existing request."""
        matched_captures = set()

        for result in match_results:
            if result.matched and result.capture:
                matched_captures.add(id(result.capture))

        unmatched = []
        for capture in captures:
            if id(capture) not in matched_captures:
                unmatched.append(capture)

        return unmatched
