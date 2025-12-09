"""
TraceTap Request Matcher

Intelligent request matching engine for finding the best-matching captured
request for an incoming mock request.

Features:
- Multiple matching strategies (exact, fuzzy, semantic)
- Scoring system with configurable weights
- Path pattern matching with wildcards
- Query parameter matching
- Header matching
- Body matching (JSON-aware)
- AI-powered semantic matching using Claude
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from urllib.parse import urlparse, parse_qs
from difflib import SequenceMatcher

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class MatchScore:
    """Score for a request match with breakdown."""

    total_score: float
    path_score: float = 0.0
    query_score: float = 0.0
    header_score: float = 0.0
    body_score: float = 0.0
    method_match: bool = False

    @property
    def is_good_match(self) -> bool:
        """Determine if this is a good enough match (>= 0.7)."""
        return self.total_score >= 0.7


@dataclass
class MatchResult:
    """Result of matching a request."""

    matched: bool
    capture: Optional[Dict[str, Any]] = None
    score: Optional[MatchScore] = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'matched': self.matched,
            'score': self.score.total_score if self.score else 0.0,
            'reason': self.reason,
            'capture_url': self.capture.get('url') if self.capture else None
        }


class RequestMatcher:
    """
    Intelligent request matcher for finding best-matching captures.

    Supports multiple matching strategies:
    - exact: Exact URL and method match
    - fuzzy: Flexible matching with similarity scoring
    - pattern: Pattern-based matching with wildcards
    - semantic: AI-powered semantic matching using Claude

    Example:
        matcher = RequestMatcher(captures, strategy='fuzzy')
        result = matcher.find_match('GET', 'https://api.example.com/users/123')

        if result.matched:
            print(f"Match found! Score: {result.score.total_score}")
            response = create_response(result.capture)
    """

    def __init__(
        self,
        captures: List[Dict[str, Any]],
        strategy: str = "fuzzy",
        min_score: float = 0.7,
        weights: Optional[Dict[str, float]] = None,
        api_key: Optional[str] = None,
        cache_enabled: bool = False,
        cache_max_size: int = 1000
    ):
        """
        Initialize request matcher.

        Args:
            captures: List of captured requests/responses
            strategy: Matching strategy (exact, fuzzy, pattern, semantic)
            min_score: Minimum score threshold for fuzzy matching (0.0 to 1.0)
            weights: Custom weights for scoring components
            api_key: Anthropic API key for semantic matching
            cache_enabled: Enable match result caching
            cache_max_size: Maximum cache size (FIFO eviction)
        """
        self.captures = captures
        self.strategy = strategy
        self.min_score = min_score

        # Default weights for scoring
        self.weights = weights or {
            'path': 0.5,
            'query': 0.2,
            'headers': 0.15,
            'body': 0.15
        }

        # Match result cache
        self.cache_enabled = cache_enabled
        self.cache_max_size = cache_max_size
        self.cache: Dict[str, MatchResult] = {}
        self.cache_hits = 0
        self.cache_misses = 0

        # Initialize Claude client for semantic matching
        self.client = None
        if strategy == 'semantic' and ANTHROPIC_AVAILABLE:
            import os
            actual_api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
            if actual_api_key:
                self.client = anthropic.Anthropic(api_key=actual_api_key)

        # Build index for faster matching
        self._build_index()

    def _build_index(self):
        """Build index of captures for faster lookup."""
        # Index by method and path for quick filtering
        self.index = {}
        for capture in self.captures:
            method = capture.get('method', 'GET').upper()
            url = capture.get('url', '')
            parsed = urlparse(url)
            path = parsed.path

            key = f"{method}:{path}"
            if key not in self.index:
                self.index[key] = []
            self.index[key].append(capture)

    def _generate_cache_key(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None
    ) -> str:
        """
        Generate cache key for a request.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body

        Returns:
            Cache key string
        """
        import hashlib

        # Start with method and URL
        key_parts = [method.upper(), url]

        # Add relevant headers (only interesting ones to keep key manageable)
        if headers:
            interesting_headers = ['content-type', 'authorization', 'accept']
            header_str = '|'.join(f"{k}:{v}" for k, v in sorted(headers.items()) if k.lower() in interesting_headers)
            if header_str:
                key_parts.append(header_str)

        # Add body hash if present
        if body:
            body_hash = hashlib.md5(body).hexdigest()[:8]
            key_parts.append(body_hash)

        # Combine all parts
        cache_key = '::'.join(key_parts)
        return cache_key

    def find_match(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None
    ) -> MatchResult:
        """
        Find best matching capture for incoming request.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body

        Returns:
            MatchResult with best match or no match
        """
        # Check cache first
        if self.cache_enabled:
            cache_key = self._generate_cache_key(method, url, headers, body)
            if cache_key in self.cache:
                self.cache_hits += 1
                return self.cache[cache_key]
            self.cache_misses += 1

        # Perform matching based on strategy
        if self.strategy == 'exact':
            result = self._exact_match(method, url)
        elif self.strategy == 'fuzzy':
            result = self._fuzzy_match(method, url, headers, body)
        elif self.strategy == 'pattern':
            result = self._pattern_match(method, url, headers, body)
        elif self.strategy == 'semantic':
            result = self._semantic_match(method, url, headers, body)
        else:
            # Default to fuzzy
            result = self._fuzzy_match(method, url, headers, body)

        # Store in cache
        if self.cache_enabled:
            # Apply FIFO eviction if cache is full
            if len(self.cache) >= self.cache_max_size:
                # Remove oldest entry (first key)
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]

            self.cache[cache_key] = result

        return result

    def _exact_match(self, method: str, url: str) -> MatchResult:
        """
        Exact matching: method and full URL must match.

        Args:
            method: HTTP method
            url: Request URL

        Returns:
            MatchResult
        """
        method_upper = method.upper()

        for capture in self.captures:
            capture_method = capture.get('method', 'GET').upper()
            capture_url = capture.get('url', '')

            if capture_method == method_upper and capture_url == url:
                score = MatchScore(
                    total_score=1.0,
                    path_score=1.0,
                    query_score=1.0,
                    method_match=True
                )
                return MatchResult(
                    matched=True,
                    capture=capture,
                    score=score,
                    reason="Exact match"
                )

        return MatchResult(matched=False, reason="No exact match found")

    def _fuzzy_match(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None
    ) -> MatchResult:
        """
        Fuzzy matching with similarity scoring.

        Scores based on:
        - Path similarity (weighted)
        - Query parameter similarity (weighted)
        - Header similarity (weighted)
        - Body similarity (weighted)

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body

        Returns:
            MatchResult with best match or no match
        """
        method_upper = method.upper()
        parsed_url = urlparse(url)
        request_path = parsed_url.path
        request_query = parse_qs(parsed_url.query)

        best_match = None
        best_score = None
        highest_total_score = 0.0

        # Quick filter using index
        index_key = f"{method_upper}:{request_path}"
        candidates = self.index.get(index_key, [])

        # If no exact path match, search all captures
        if not candidates:
            candidates = [
                c for c in self.captures
                if c.get('method', 'GET').upper() == method_upper
            ]

        for capture in candidates:
            score = self._calculate_match_score(
                capture,
                request_path,
                request_query,
                headers,
                body
            )

            if score.method_match and score.total_score > highest_total_score:
                highest_total_score = score.total_score
                best_score = score
                best_match = capture

        # Check if best match meets minimum threshold
        if best_match and highest_total_score >= self.min_score:
            return MatchResult(
                matched=True,
                capture=best_match,
                score=best_score,
                reason=f"Fuzzy match (score: {highest_total_score:.2f})"
            )

        return MatchResult(
            matched=False,
            reason=f"No match above threshold {self.min_score} (best: {highest_total_score:.2f})"
        )

    def _calculate_match_score(
        self,
        capture: Dict[str, Any],
        request_path: str,
        request_query: Dict[str, List[str]],
        headers: Optional[Dict[str, str]],
        body: Optional[bytes]
    ) -> MatchScore:
        """
        Calculate match score for a capture.

        Args:
            capture: Captured request/response
            request_path: Request path
            request_query: Parsed query parameters
            headers: Request headers
            body: Request body

        Returns:
            MatchScore with breakdown
        """
        capture_url = capture.get('url', '')
        capture_parsed = urlparse(capture_url)
        capture_path = capture_parsed.path
        capture_query = parse_qs(capture_parsed.query)
        capture_method = capture.get('method', 'GET').upper()

        # Method must match
        method_match = True  # Already filtered by method

        # Path similarity
        path_score = self._path_similarity(request_path, capture_path)

        # Query parameter similarity
        query_score = self._query_similarity(request_query, capture_query)

        # Header similarity (if headers provided)
        header_score = 0.0
        if headers:
            capture_headers = capture.get('req_headers', {})
            header_score = self._header_similarity(headers, capture_headers)

        # Body similarity (if body provided)
        body_score = 0.0
        if body:
            capture_body = capture.get('req_body', '')
            body_score = self._body_similarity(body, capture_body)

        # Calculate weighted total score
        total_score = (
            path_score * self.weights['path'] +
            query_score * self.weights['query'] +
            header_score * self.weights['headers'] +
            body_score * self.weights['body']
        )

        return MatchScore(
            total_score=total_score,
            path_score=path_score,
            query_score=query_score,
            header_score=header_score,
            body_score=body_score,
            method_match=method_match
        )

    def _path_similarity(self, path1: str, path2: str) -> float:
        """
        Calculate path similarity score.

        Supports:
        - Exact match: 1.0
        - Path parameter variations: partial score
        - Sequence similarity: difflib ratio

        Args:
            path1: First path
            path2: Second path

        Returns:
            Similarity score 0.0 to 1.0
        """
        if path1 == path2:
            return 1.0

        # Normalize paths (remove trailing slashes)
        p1 = path1.rstrip('/')
        p2 = path2.rstrip('/')

        if p1 == p2:
            return 1.0

        # Split into segments
        segments1 = [s for s in p1.split('/') if s]
        segments2 = [s for s in p2.split('/') if s]

        # Must have same number of segments for good match
        if len(segments1) != len(segments2):
            # Use sequence matcher for different lengths
            return SequenceMatcher(None, p1, p2).ratio() * 0.5

        # Compare segments
        matches = 0
        for seg1, seg2 in zip(segments1, segments2):
            if seg1 == seg2:
                matches += 1
            elif self._is_likely_id(seg1) and self._is_likely_id(seg2):
                # Both are IDs (different values), give partial credit
                matches += 0.8

        return matches / len(segments1) if segments1 else 0.0

    def _is_likely_id(self, segment: str) -> bool:
        """
        Check if path segment is likely an ID.

        Recognizes: UUIDs, numeric IDs, MongoDB ObjectIds,
        short alphanumeric IDs, and Base64-style IDs.
        """
        # UUID pattern (e.g., 550e8400-e29b-41d4-a716-446655440000)
        if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', segment, re.I):
            return True

        # Numeric ID (e.g., 123, 456789)
        if re.match(r'^\d+$', segment):
            return True

        # MongoDB ObjectId (24 hex characters, e.g., 507f1f77bcf86cd799439011)
        if re.match(r'^[0-9a-f]{24}$', segment, re.I):
            return True

        # Short alphanumeric ID (6-32 chars, e.g., abc123, user456)
        if re.match(r'^[a-zA-Z0-9]{6,32}$', segment):
            return True

        # Base64-style ID (URL-safe, e.g., dXNlcl8xMjM, a1b2-c3d4_e5f6)
        if re.match(r'^[A-Za-z0-9+/=_-]{16,}$', segment):
            return True

        # ULID or similar (alphanumeric, typically 26 chars)
        if re.match(r'^[0-9A-HJKMNP-TV-Z]{26}$', segment, re.I):
            return True

        return False

    def _query_similarity(
        self,
        query1: Dict[str, List[str]],
        query2: Dict[str, List[str]]
    ) -> float:
        """
        Calculate query parameter similarity.

        Args:
            query1: First query params
            query2: Second query params

        Returns:
            Similarity score 0.0 to 1.0
        """
        if not query1 and not query2:
            return 1.0

        if not query1 or not query2:
            return 0.0

        # Count matching keys
        keys1 = set(query1.keys())
        keys2 = set(query2.keys())

        common_keys = keys1 & keys2
        all_keys = keys1 | keys2

        if not all_keys:
            return 1.0

        # Key overlap score
        key_score = len(common_keys) / len(all_keys)

        # Value matching for common keys
        value_matches = 0
        for key in common_keys:
            if query1[key] == query2[key]:
                value_matches += 1

        value_score = value_matches / len(common_keys) if common_keys else 0.0

        # Weighted average
        return key_score * 0.5 + value_score * 0.5

    def _header_similarity(
        self,
        headers1: Dict[str, str],
        headers2: Dict[str, str]
    ) -> float:
        """
        Calculate header similarity (focusing on important headers).

        Args:
            headers1: First headers
            headers2: Second headers

        Returns:
            Similarity score 0.0 to 1.0
        """
        # Important headers for matching
        important_headers = [
            'content-type', 'accept', 'authorization',
            'x-api-key', 'user-agent'
        ]

        # Normalize header keys to lowercase
        h1 = {k.lower(): v for k, v in headers1.items()}
        h2 = {k.lower(): v for k, v in headers2.items()}

        matches = 0
        total = 0

        for header in important_headers:
            if header in h1 or header in h2:
                total += 1
                if header in h1 and header in h2:
                    if h1[header] == h2[header]:
                        matches += 1
                    else:
                        # Partial credit for similar values
                        similarity = SequenceMatcher(None, h1[header], h2[header]).ratio()
                        matches += similarity * 0.5

        return matches / total if total > 0 else 1.0

    def _body_similarity(self, body1: bytes, body2: str) -> float:
        """
        Calculate body similarity (JSON-aware).

        Args:
            body1: First body (bytes)
            body2: Second body (string)

        Returns:
            Similarity score 0.0 to 1.0
        """
        if not body1 and not body2:
            return 1.0

        if not body1 or not body2:
            return 0.0

        try:
            # Try JSON comparison
            body1_str = body1.decode('utf-8') if isinstance(body1, bytes) else body1
            json1 = json.loads(body1_str)
            json2 = json.loads(body2) if isinstance(body2, str) else body2

            # Compare JSON structures
            return self._json_similarity(json1, json2)

        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fallback to string comparison
            body1_str = body1.decode('utf-8', errors='ignore') if isinstance(body1, bytes) else str(body1)
            body2_str = str(body2)

            return SequenceMatcher(None, body1_str, body2_str).ratio()

    def _json_similarity(self, json1: Any, json2: Any) -> float:
        """Calculate similarity between JSON structures."""
        if json1 == json2:
            return 1.0

        if type(json1) != type(json2):
            return 0.0

        if isinstance(json1, dict):
            keys1 = set(json1.keys())
            keys2 = set(json2.keys())

            key_overlap = len(keys1 & keys2) / len(keys1 | keys2) if (keys1 | keys2) else 1.0

            # Check value similarity for common keys
            common_keys = keys1 & keys2
            if common_keys:
                value_similarity = sum(
                    self._json_similarity(json1[k], json2[k])
                    for k in common_keys
                ) / len(common_keys)
            else:
                value_similarity = 0.0

            return key_overlap * 0.5 + value_similarity * 0.5

        elif isinstance(json1, list):
            if len(json1) != len(json2):
                return 0.5  # Different lengths, partial credit

            if not json1:
                return 1.0

            # Compare elements
            similarity_sum = sum(
                self._json_similarity(j1, j2)
                for j1, j2 in zip(json1, json2)
            )
            return similarity_sum / len(json1)

        else:
            # Primitive types
            return 1.0 if json1 == json2 else 0.0

    def _pattern_match(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None
    ) -> MatchResult:
        """
        Pattern-based matching with wildcard support.

        Supports patterns like:
        - /users/* (any single segment)
        - /users/** (any number of segments)
        - /users/{id} (named parameter)

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body

        Returns:
            MatchResult
        """
        method_upper = method.upper()
        parsed_url = urlparse(url)
        request_path = parsed_url.path

        for capture in self.captures:
            capture_method = capture.get('method', 'GET').upper()
            if capture_method != method_upper:
                continue

            capture_url = capture.get('url', '')
            capture_parsed = urlparse(capture_url)
            capture_path = capture_parsed.path

            if self._path_matches_pattern(request_path, capture_path):
                score = MatchScore(
                    total_score=0.9,
                    path_score=0.9,
                    method_match=True
                )
                return MatchResult(
                    matched=True,
                    capture=capture,
                    score=score,
                    reason="Pattern match"
                )

        return MatchResult(matched=False, reason="No pattern match found")

    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern with wildcards."""
        # Convert pattern to regex
        # Replace {param} with regex group
        pattern_regex = re.sub(r'\{[^}]+\}', r'[^/]+', pattern)
        # Replace ** with .*
        pattern_regex = pattern_regex.replace('**', '.*')
        # Replace * with [^/]+
        pattern_regex = pattern_regex.replace('*', r'[^/]+')
        # Anchor pattern
        pattern_regex = f'^{pattern_regex}$'

        return bool(re.match(pattern_regex, path))

    def _semantic_match(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None
    ) -> MatchResult:
        """
        AI-powered semantic matching using Claude.

        Uses Claude to understand the intent of the request and find
        the most semantically similar captured request.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body

        Returns:
            MatchResult
        """
        if not self.client:
            # Fallback to fuzzy matching if no AI client
            return self._fuzzy_match(method, url, headers, body)

        try:
            # Format incoming request for AI analysis
            request_desc = self._format_request_for_ai(method, url, headers, body)

            # Format captures (limit to relevant ones for context)
            captures_desc = self._format_captures_for_ai(method, url, limit=10)

            if not captures_desc:
                # No relevant captures found
                return MatchResult(matched=False, reason="No captures available for semantic matching")

            # Create prompt for Claude
            prompt = f"""Analyze this incoming HTTP request and find the most semantically similar captured request.

INCOMING REQUEST:
{request_desc}

CAPTURED REQUESTS (with indices):
{captures_desc}

Task: Identify which captured request is most semantically similar to the incoming request.
Consider:
- Endpoint purpose (what it does, not just the URL)
- Data being sent/requested
- Workflow context
- API patterns

Respond with ONLY the index number (0-{len(self.captures)-1}) of the best matching capture.
If no good semantic match exists, respond with "NONE".
"""

            # Call Claude
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=100,
                temperature=0.0,  # Deterministic for consistency
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            response_text = response.content[0].text.strip()

            # Extract index
            if response_text.upper() == "NONE":
                return MatchResult(matched=False, reason="No semantic match found by AI")

            try:
                match_index = int(response_text)
                if 0 <= match_index < len(self.captures):
                    matched_capture = self.captures[match_index]
                    # Calculate a high score for AI matches
                    score = MatchScore(
                        total_score=0.95,  # High confidence for AI semantic match
                        path_score=1.0,
                        query_score=1.0,
                        header_score=1.0,
                        body_score=1.0,
                        method_match=(method == matched_capture.get('method'))
                    )
                    return MatchResult(
                        matched=True,
                        capture=matched_capture,
                        score=score,
                        reason=f"AI semantic match (index {match_index})"
                    )
                else:
                    # Invalid index, fallback
                    return self._fuzzy_match(method, url, headers, body)
            except ValueError:
                # Could not parse index, fallback
                return self._fuzzy_match(method, url, headers, body)

        except Exception as e:
            # AI error, fallback to fuzzy matching
            print(f"Warning: Semantic matching failed ({e}), falling back to fuzzy matching")
            return self._fuzzy_match(method, url, headers, body)

    def _format_request_for_ai(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Any
    ) -> str:
        """
        Format a request for AI analysis.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body

        Returns:
            Formatted string description of the request
        """
        # Parse URL
        parsed = urlparse(url)
        path = parsed.path or '/'
        query = parsed.query

        # Extract key headers
        relevant_headers = self._filter_interesting_headers(headers)

        # Format body
        body_str = ""
        if body:
            try:
                if isinstance(body, bytes):
                    body_str = body.decode('utf-8')
                else:
                    body_str = str(body)
                # Truncate if too long
                if len(body_str) > 500:
                    body_str = body_str[:500] + "... [truncated]"
            except:
                body_str = "[binary data]"

        # Format description
        desc = f"""Method: {method}
Path: {path}
Query: {query if query else "(none)"}
Headers: {relevant_headers if relevant_headers else "(none)"}
Body: {body_str if body_str else "(empty)"}"""

        return desc

    def _format_captures_for_ai(
        self,
        method: str,
        url: str,
        limit: int = 10
    ) -> str:
        """
        Format captured requests for AI analysis.

        Args:
            method: HTTP method to filter by
            url: Request URL for filtering
            limit: Maximum number of captures to include

        Returns:
            Formatted string with indexed captures
        """
        # Filter captures by method first for efficiency
        relevant_captures = [
            (i, c) for i, c in enumerate(self.captures)
            if c.get('method') == method
        ]

        # If too many, use fuzzy matching to pre-filter to most relevant
        if len(relevant_captures) > limit:
            # Quick scoring to filter
            scored = []
            parsed_url = urlparse(url)
            for idx, capture in relevant_captures:
                cap_parsed = urlparse(capture.get('url', ''))
                # Simple path similarity
                path_sim = self._path_similarity(parsed_url.path, cap_parsed.path)
                scored.append((path_sim, idx, capture))
            # Sort by score and take top N
            scored.sort(reverse=True)
            relevant_captures = [(idx, cap) for _, idx, cap in scored[:limit]]

        if not relevant_captures:
            # No method match, take any captures (limited)
            relevant_captures = list(enumerate(self.captures[:limit]))

        # Format captures
        formatted_captures = []
        for idx, capture in relevant_captures:
            cap_url = capture.get('url', '')
            cap_parsed = urlparse(cap_url)
            cap_path = cap_parsed.path or '/'
            cap_query = cap_parsed.query

            # Get body preview
            cap_body = capture.get('req_body', '')
            if cap_body and len(cap_body) > 200:
                cap_body = cap_body[:200] + "..."

            formatted = f"""[{idx}] {capture.get('method', 'GET')} {cap_path}
    Query: {cap_query if cap_query else "(none)"}
    Body: {cap_body if cap_body else "(empty)"}
    Response Status: {capture.get('status', 'unknown')}"""

            formatted_captures.append(formatted)

        return "\n\n".join(formatted_captures)

    def _filter_interesting_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Filter headers to only include interesting ones for matching."""
        interesting = [
            'content-type', 'authorization', 'accept',
            'x-api-key', 'x-auth-token', 'x-requested-with'
        ]
        return {
            k: v for k, v in headers.items()
            if k.lower() in interesting
        }
