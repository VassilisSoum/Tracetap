"""
Filtering logic for TraceTap.

Provides functions to determine if HTTP requests should be captured
based on host matching (exact, wildcard) and regex patterns.
"""

import re
from typing import List, Optional


class RequestFilter:
    """
    Handles filtering logic to determine which requests should be captured.
    
    Supports:
    - Exact host matching (e.g., "api.example.com")
    - Wildcard matching (e.g., "*.example.com")
    - Regex pattern matching on URL and host
    """
    
    def __init__(self, host_filters: List[str], regex_pattern: Optional[str] = None):
        """
        Initialize the filter.
        
        Args:
            host_filters: List of hosts to match (supports wildcards)
            regex_pattern: Optional regex pattern to match against URLs
        """
        self.host_filters = host_filters
        self.regex_pattern = None
        
        if regex_pattern:
            try:
                self.regex_pattern = re.compile(regex_pattern)
            except re.error as e:
                print(f"Invalid regex pattern: {e}", flush=True)
    
    def should_capture(self, host: str, url: str, verbose: bool = False) -> bool:
        """
        Determine if a request should be captured based on filters.

        Filtering logic:
        - If no filters configured: capture everything
        - If any filter matches: capture (OR logic)
        - Supports exact host matching, wildcard matching, and regex

        Args:
            host: The request hostname (e.g., "api.example.com")
            url: The full URL (e.g., "https://api.example.com/users")
            verbose: If True, print filtering decisions

        Returns:
            True if request should be captured, False otherwise
        """
        # No filters = capture everything
        if not self.host_filters and not self.regex_pattern:
            return True

        captured = False
        match_reason = ""

        # Check host filters
        if self.host_filters:
            for filter_host in self.host_filters:
                # Exact match: filter_host == host
                if filter_host == host:
                    captured = True
                    match_reason = f"exact match: {filter_host}"
                    break

                # Wildcard match: *.example.com matches api.example.com, auth.example.com, etc.
                if filter_host.startswith('*.'):
                    domain = filter_host[2:]  # Remove "*."

                    # Match subdomains (api.example.com matches *.example.com)
                    if host.endswith('.' + domain):
                        captured = True
                        match_reason = f"wildcard match: {filter_host}"
                        break

                    # Also match the domain itself (example.com matches *.example.com)
                    if host == domain:
                        captured = True
                        match_reason = f"wildcard match: {filter_host}"
                        break

        # Check regex filter (only if not already captured)
        if not captured and self.regex_pattern:
            # Try matching against both URL and host
            if self.regex_pattern.search(url) or self.regex_pattern.search(host):
                captured = True
                match_reason = f"regex match: {self.regex_pattern.pattern}"

        # Log filtering decision in verbose mode
        if verbose:
            if captured:
                print(f"✅ [CAPTURE] {host} ({match_reason})", flush=True)
            else:
                print(f"❌ [SKIP] {host}", flush=True)

        return captured
