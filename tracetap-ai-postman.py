#!/usr/bin/env python3
"""
TraceTap AI Postman Collection Generator

This script converts raw HTTP capture logs into Postman collections,
optionally guided by a flow YAML file that defines the expected sequence.
"""

import json
import yaml
import argparse
import sys
import os
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from datetime import datetime
from collections import defaultdict
from textwrap import dedent

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Import variable extraction functionality
try:
    from src.tracetap.replay.variables import VariableExtractor, Variable
    VARIABLE_EXTRACTOR_AVAILABLE = True
except ImportError:
    VARIABLE_EXTRACTOR_AVAILABLE = False
    print("Warning: VariableExtractor not available. Variable detection will be disabled.")

# Import common utilities for secure API key handling
try:
    from src.tracetap.common import get_api_key_from_env
except ImportError:
    # Fallback if common module not available
    def get_api_key_from_env():
        return os.environ.get('ANTHROPIC_API_KEY')


class URLMatcher:
    """Handles URL matching logic with various strategies"""

    @staticmethod
    def normalize_url(url: str, strip_query: bool = False) -> str:
        """Normalize URL for comparison"""
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
        Compare two URLs for matching

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
        """Extract base URL without query parameters"""
        return URLMatcher.normalize_url(url, strip_query=True)


class RawLogProcessor:
    """Processes raw HTTP capture logs"""

    def __init__(self, log_data: List[Dict[str, Any]]):
        self.log_entries = log_data
        self.url_index = self._build_url_index()

    def _build_url_index(self) -> Dict[str, List[Dict[str, Any]]]:
        """Build an index of log entries by base URL for faster lookup"""
        index = defaultdict(list)
        for entry in self.log_entries:
            base_url = URLMatcher.extract_base_url(entry.get('url', ''))
            index[base_url].append(entry)
        return index

    def find_matching_entry(self,
                            url: str,
                            method: Optional[str] = None,
                            strict: bool = False,
                            used_entries: Optional[set] = None) -> Optional[Dict[str, Any]]:
        """
        Find a log entry matching the given URL and method

        Args:
            url: URL to match
            method: HTTP method to match (optional)
            strict: Whether to use strict URL matching
            used_entries: Set of already used entry indices to avoid duplicates

        Returns:
            Matching log entry or None
        """
        if used_entries is None:
            used_entries = set()

        # First try exact match with method
        for idx, entry in enumerate(self.log_entries):
            if idx in used_entries:
                continue

            entry_url = entry.get('url', '')
            entry_method = entry.get('method', '')

            # Check URL match
            if URLMatcher.urls_match(url, entry_url, strict=strict):
                # If method specified, must match
                if method and entry_method.upper() != method.upper():
                    continue
                return entry

        # If strict and no match found, try without query parameters
        if strict:
            base_url = URLMatcher.extract_base_url(url)
            if base_url in self.url_index:
                for entry in self.url_index[base_url]:
                    idx = self.log_entries.index(entry)
                    if idx in used_entries:
                        continue

                    entry_method = entry.get('method', '')
                    if method and entry_method.upper() != method.upper():
                        continue
                    return entry

        return None


class AIFlowGenerator:
    """AI-powered flow generator using Claude to analyze raw logs"""

    def __init__(self, raw_log: List[Dict[str, Any]], flow_intent: str = ""):
        """
        Initialize AI flow generator.

        Args:
            raw_log: List of captured HTTP requests
            flow_intent: Description of the expected flow (SECURITY: API key from environment only)
        """
        self.raw_log = raw_log
        self.flow_intent = flow_intent
        self.client = None
        self.ai_available = False

        # Check if anthropic library is available
        if not ANTHROPIC_AVAILABLE:
            self.ai_message = "⚠ Claude AI not available: anthropic library not installed\n  Install: pip install anthropic"
            return

        # SECURITY: Get API key from environment only (never accept via CLI)
        api_key = get_api_key_from_env()
        if not api_key:
            self.ai_message = "⚠ Claude AI not available: ANTHROPIC_API_KEY not set\n  Set: export ANTHROPIC_API_KEY=your_key_here\n  Get key: https://console.anthropic.com/"
            return

        # Initialize client
        try:
            self.client = anthropic.Anthropic(api_key=api_key)
            self.ai_available = True
            self.ai_message = "✓ Claude AI enabled"
        except Exception as e:
            self.ai_message = f"⚠ Claude AI initialization failed: {e}"

    def save_flow(self, filepath: str) -> None:
        """Generate and save flow to YAML file"""
        # Show AI status
        if hasattr(self, 'ai_message'):
            print(self.ai_message)

        # Use AI if available, otherwise basic generation
        if self.ai_available and self.client:
            print("  Using AI-powered flow analysis...")

            # Show intent keywords for debugging
            if self.flow_intent:
                keywords = self._extract_intent_keywords(self.flow_intent)
                print(f"  Intent keywords: {', '.join(keywords[:15])}")

            flow = self.generate_flow_with_ai()
        else:
            print("  Using basic flow generation...")
            flow = self._generate_basic_flow()

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)

        with open(filepath, 'w') as f:
            yaml.dump(flow, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def generate_flow_with_ai(self) -> Dict[str, Any]:
        """Use Claude AI to generate an intelligent flow from raw logs"""

        if not self.ai_available:
            return self._generate_basic_flow()

        try:
            # Prepare the raw logs for Claude with full details
            logs_json = self._prepare_logs_for_ai()

            # Create the prompt for Claude
            prompt = self._create_ai_prompt(logs_json)

            # Call Claude API
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract YAML from response
            response_text = message.content[0].text
            flow_yaml = self._extract_yaml_from_response(response_text)

            if flow_yaml:
                return yaml.safe_load(flow_yaml)
            else:
                print("  ⚠ Could not extract YAML from AI response, using basic flow")
                return self._generate_basic_flow()

        except Exception as e:
            print(f"  ⚠ AI generation failed: {e}")
            print("  Falling back to basic flow generation")
            return self._generate_basic_flow()

    def _prepare_logs_for_ai(self) -> str:
        """Prepare raw logs as JSON for Claude - use smart sampling based on intent"""

        # Extract keywords from flow intent
        intent_keywords = self._extract_intent_keywords(self.flow_intent)

        # Step 1: Always include first 50 requests (start of flow)
        selected_indices = set(range(min(50, len(self.raw_log))))

        # Step 2: Search entire log for requests matching intent keywords
        keyword_matches = 0
        for idx, entry in enumerate(self.raw_log):
            url = entry.get('url', '').lower()
            body = str(entry.get('req_body', '')).lower()

            # Check if any intent keyword appears in URL or body
            for keyword in intent_keywords:
                if keyword in url or keyword in body:
                    selected_indices.add(idx)
                    keyword_matches += 1
                    # Also include surrounding requests for context
                    if idx > 0:
                        selected_indices.add(idx - 1)
                    if idx < len(self.raw_log) - 1:
                        selected_indices.add(idx + 1)
                    break

        # Step 3: Add some samples from middle and end for coverage
        total = len(self.raw_log)
        if total > 100:
            # Add samples from middle
            mid_start = total // 2 - 10
            mid_end = total // 2 + 10
            selected_indices.update(range(max(0, mid_start), min(total, mid_end)))

            # Add last 20 requests
            selected_indices.update(range(max(0, total - 20), total))

        # Step 4: Limit to 200 requests max to stay within token limits
        selected_indices = sorted(selected_indices)[:200]

        # Print sampling statistics
        match_percentage = (keyword_matches / total * 100) if total > 0 else 0
        print(f"  Smart sampling: {len(selected_indices)} requests selected from {total} total")
        print(f"  Keyword matches: {keyword_matches} requests ({match_percentage:.1f}%)")

        # Create simplified version for AI
        simplified = []
        for idx in selected_indices:
            entry = self.raw_log[idx]
            simplified.append({
                'index': idx + 1,  # 1-based for readability
                'method': entry.get('method', 'GET'),
                'url': entry.get('url', ''),
                'status': entry.get('status', ''),
                'req_body': entry.get('req_body', '')[:200] if entry.get('req_body') else ''
            })

        return json.dumps(simplified, indent=2)

    def _extract_intent_keywords(self, intent: str) -> List[str]:
        """Extract keywords from flow intent with minimal filtering"""
        if not intent:
            return []

        # Convert to lowercase and split
        words = intent.lower().split()

        # Only filter out the most basic articles and conjunctions
        basic_stopwords = {'a', 'an', 'the', 'and', 'or', 'to', 'of', 'in', 'on'}

        # Keep keywords that are at least 3 characters
        keywords = []
        for w in words:
            cleaned = w.strip(',.!?;:')
            if len(cleaned) >= 3 and cleaned not in basic_stopwords:
                keywords.append(cleaned)

        # Create compound keywords for consecutive meaningful words
        compound_keywords = []
        for i in range(len(words) - 1):
            word1 = words[i].strip(',.!?;:')
            word2 = words[i + 1].strip(',.!?;:')

            if (word1 not in basic_stopwords and word2 not in basic_stopwords and
                    len(word1) >= 3 and len(word2) >= 3):
                compound = word1 + word2
                compound_keywords.append(compound)

        return keywords + compound_keywords

    def _create_ai_prompt(self, logs_json: str) -> str:
        """Create the prompt for Claude AI"""
        intent_section = ""
        keywords_section = ""

        if self.flow_intent:
            intent_section = f"""
USER'S FLOW INTENT: {self.flow_intent}
"""
            # Extract keywords and show them in the prompt
            intent_keywords = self._extract_intent_keywords(self.flow_intent)
            if intent_keywords:
                keywords_section = f"""
Keywords extracted from intent: {', '.join(intent_keywords[:20])}

IMPORTANT: Before using any intent keyword, verify it actually appears in the log URLs or request bodies.
Ignore intent keywords that don't match anything in the actual logs (e.g., if intent says "destroys everything" 
but no URLs contain "destroy", ignore those keywords and focus only on what's actually present in the logs).
"""

        return dedent(f"""
        You are analyzing HTTP request logs to create a structured flow YAML file.

        {intent_section}{keywords_section}
        HTTP Request Logs (Smart Sampled from {len(self.raw_log)} total requests):
        ```json
        {logs_json}
        ```

        CRITICAL INSTRUCTIONS:

        1. **Validate Intent Against Logs**:
           - Review the URLs and request bodies in the logs
           - ONLY create flow steps for actions that are ACTUALLY PRESENT in the logs
           - If intent keywords don't appear in any URLs/paths/bodies, ignore those parts of the intent
           - Example: If intent says "destroys everything" but no URL contains "destroy", skip it
           - Example: If intent says "paysafe deposit" and URLs contain "/paysafe/" and "/deposit", use them

        2. **Match Real Actions**:
           - Identify requests where the URL path, domain, or body clearly relates to the intent
           - Look for domain-specific terms (payment provider names, action verbs in URLs, API endpoints)
           - Prefer explicit matches (e.g., URL contains "paysafe", "login", "cashier", "deposit")

        3. **Use Exact URLs**:
           - Use the EXACT URLs from the logs (including all query parameters)
           - Include the actual HTTP method from the logs
           - Use the actual status codes from the logs

        4. **Create Accurate Flow Steps**:
           - Name steps based on what the URL/endpoint actually does
           - Only include steps where you can find a clear corresponding request
           - Order steps by their index position in the logs

        5. **Be Honest**:
           - If the intent describes actions not present in the logs, only create steps for what IS present
           - Don't invent steps for intent keywords that have no corresponding requests
           - Focus on the actual technical flow captured in the logs

        Create a YAML flow file with this structure:
        ```yaml
        name: "Flow Name Based on Actual Log Content"
        description: "Description of what actually happened in the logs"
        steps:
          - id: step1
            name: "Step Name Based on Actual Request"
            request:
              method: POST  # Actual method from log
              url: "https://exact.url.from/log?with=params"  # EXACT URL from log
            expect:
              status: 200  # Actual status from log
            notes:
              - "What this request actually does"
        ```

        Generate the YAML flow now, including ONLY steps that have actual corresponding requests in the logs:
        """).strip()

    def _extract_yaml_from_response(self, response: str) -> Optional[str]:
        """Extract YAML content from Claude's response"""
        # Try to find YAML in code blocks
        yaml_pattern = r'```(?:yaml|yml)?\s*\n(.*?)\n```'
        matches = re.findall(yaml_pattern, response, re.DOTALL)

        if matches:
            return matches[0]

        # If no code blocks, try to parse the entire response
        try:
            yaml.safe_load(response)
            return response
        except (yaml.YAMLError, AttributeError, TypeError):
            return None

    def _generate_basic_flow(self) -> Dict[str, Any]:
        """Generate a basic flow without AI"""
        steps = []

        for idx, entry in enumerate(self.raw_log[:50], 1):  # Limit to first 50
            method = entry.get('method', 'GET')
            url = entry.get('url', '')
            status = entry.get('status')

            if not url:
                continue

            # Generate simple step name
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split('/') if p]
            step_name = path_parts[-1] if path_parts else parsed.netloc

            step = {
                'id': f'step{idx}',
                'name': f"{method} {step_name}",
                'request': {
                    'method': method,
                    'url': url
                }
            }

            if status:
                step['expect'] = {'status': status}

            steps.append(step)

        return {
            'name': "Generated Flow",
            'description': f"Auto-generated from {len(self.raw_log)} requests",
            'steps': steps
        }


class FlowProcessor:
    """Processes flow YAML file"""

    def __init__(self, flow: Dict[str, Any]):
        self.flow = flow
        self.flow_steps = flow.get('steps', [])

    def get_flow_name(self) -> str:
        return self.flow.get('name', 'API Flow')

    def get_flow_description(self) -> str:
        return self.flow.get('description', '')


class PostmanCollectionBuilder:
    """Builds Postman collection JSON"""

    def __init__(self, name: str, description: str = "",
                 enable_variables: bool = True,
                 enable_jwt_params: bool = True,
                 enable_path_params: bool = True,
                 enable_base_url_params: bool = True,
                 enable_response_extraction: bool = True):
        self.collection = {
            "info": {
                "name": name,
                "description": description,
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": [],
            "variable": []
        }
        self.variable_registry = {}  # Track variables: {key: {"value": val, "type": type}}
        self.response_variables = {}  # Track response→request variable flow: {var_name: {source_idx, usage_indices}}
        self.request_responses = []  # Store (request_data, response_data) pairs for analysis

        # Variable extraction settings
        self.enable_variables = enable_variables
        self.enable_jwt_params = enable_jwt_params and enable_variables
        self.enable_path_params = enable_path_params and enable_variables
        self.enable_base_url_params = enable_base_url_params and enable_variables
        self.enable_response_extraction = enable_response_extraction and enable_variables

    def add_collection_variable(self, key: str, value: str, var_type: str = "default", description: str = "") -> None:
        """
        Add a variable to the collection's variable list.

        Args:
            key: Variable name (will be referenced as {{key}} in requests)
            value: Default value for the variable
            var_type: Type of variable (default, string, number, boolean, etc.)
            description: Optional description of what the variable represents
        """
        # Skip if variable already exists
        if key in self.variable_registry:
            return

        # Register the variable
        self.variable_registry[key] = {
            "value": value,
            "type": var_type
        }

        # Add to collection
        variable_entry = {
            "key": key,
            "value": value,
            "type": var_type
        }

        if description:
            variable_entry["description"] = description

        self.collection["variable"].append(variable_entry)

    def _parameterize_jwt_token(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Detect JWT tokens in Authorization headers and replace with variables.

        Args:
            headers: Request headers dictionary

        Returns:
            Modified headers with JWT tokens replaced by {{variable_name}}
        """
        if not headers:
            return headers

        # JWT pattern: eyJ...eyJ... (Base64 encoded JSON with 3 parts)
        jwt_pattern = r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*'

        modified_headers = headers.copy()

        # Check Authorization header
        for header_name, header_value in headers.items():
            if header_name.lower() == 'authorization' and isinstance(header_value, str):
                # Check for Bearer token
                bearer_match = re.match(r'Bearer\s+(.+)', header_value, re.IGNORECASE)
                if bearer_match:
                    token = bearer_match.group(1).strip()

                    # Verify it's a JWT token
                    if re.fullmatch(jwt_pattern, token):
                        # Add variable if not already exists
                        self.add_collection_variable(
                            key="auth_token",
                            value=token,
                            var_type="string",
                            description="JWT authentication token (extracted from Authorization header)"
                        )

                        # Replace token with variable reference
                        modified_headers[header_name] = "Bearer {{auth_token}}"

        return modified_headers

    def _parameterize_path_ids(self, url: str) -> str:
        """
        Detect IDs in URL paths and replace with variables.

        Detects:
        - Numeric IDs (e.g., /users/123)
        - UUIDs (e.g., /orders/a1b2c3d4-e5f6-...)
        - MongoDB ObjectIds (24 hex characters)
        - Base64-like IDs

        Args:
            url: Original URL

        Returns:
            URL with IDs replaced by {{variable_name}}
        """
        parsed = urlparse(url)
        path_parts = parsed.path.split('/')

        # ID patterns
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        objectid_pattern = r'^[0-9a-f]{24}$'
        numeric_id_pattern = r'^\d{3,}$'  # 3+ digits to avoid version numbers like v1, v2
        base64_pattern = r'^[A-Za-z0-9_-]{20,}$'  # Long base64-like strings

        parameterized_parts = []
        prev_segment = None

        for i, part in enumerate(path_parts):
            if not part:
                parameterized_parts.append(part)
                continue

            # Check if this part looks like an ID
            is_uuid = re.match(uuid_pattern, part.lower())
            is_objectid = re.match(objectid_pattern, part.lower())
            is_numeric_id = re.match(numeric_id_pattern, part)
            is_base64_id = re.match(base64_pattern, part)

            if is_uuid or is_objectid or is_numeric_id or is_base64_id:
                # Infer variable name from previous path segment
                var_name = None
                if prev_segment:
                    # Use previous segment to name the variable (e.g., "users" -> "user_id")
                    base_name = prev_segment.rstrip('s')  # Simple singularization
                    var_name = f"{base_name}_id"
                else:
                    # Fallback naming
                    if is_uuid:
                        var_name = "resource_uuid"
                    elif is_objectid:
                        var_name = "resource_objectid"
                    elif is_numeric_id:
                        var_name = "resource_id"
                    else:
                        var_name = "resource_token"

                # Determine ID type
                if is_uuid:
                    id_type = "uuid"
                    description = f"UUID identifier (extracted from path /{prev_segment or 'resource'}/:id)"
                elif is_objectid:
                    id_type = "objectid"
                    description = f"MongoDB ObjectId (extracted from path /{prev_segment or 'resource'}/:id)"
                elif is_numeric_id:
                    id_type = "integer"
                    description = f"Numeric identifier (extracted from path /{prev_segment or 'resource'}/:id)"
                else:
                    id_type = "string"
                    description = f"Base64 identifier (extracted from path /{prev_segment or 'resource'}/:id)"

                # Add variable
                self.add_collection_variable(
                    key=var_name,
                    value=part,
                    var_type=id_type,
                    description=description
                )

                # Replace with variable reference
                parameterized_parts.append(f"{{{{{var_name}}}}}")
            else:
                parameterized_parts.append(part)
                prev_segment = part

        # Reconstruct URL
        parameterized_path = '/'.join(parameterized_parts)
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parameterized_path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

    def _parameterize_base_url(self, url: str) -> str:
        """
        Extract base URL and replace with variable.

        Args:
            url: Original URL

        Returns:
            URL with base URL replaced by {{base_url}} or {{base_url_N}}
        """
        parsed = urlparse(url)

        # Extract base URL (scheme + netloc)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Create variable name
        # If this is the first base URL, use "base_url", otherwise "base_url_2", etc.
        var_name = "base_url"

        # Check if we already have this base URL registered
        if var_name in self.variable_registry:
            # Check if it's the same base URL
            if self.variable_registry[var_name]["value"] != base_url:
                # Different base URL, need a new variable
                counter = 2
                while f"{var_name}_{counter}" in self.variable_registry:
                    if self.variable_registry[f"{var_name}_{counter}"]["value"] == base_url:
                        var_name = f"{var_name}_{counter}"
                        break
                    counter += 1
                else:
                    var_name = f"{var_name}_{counter}"

        # Add variable if not already exists
        if var_name not in self.variable_registry:
            # Extract a clean description from the hostname
            hostname = parsed.netloc.split(':')[0]
            self.add_collection_variable(
                key=var_name,
                value=base_url,
                var_type="string",
                description=f"Base URL for {hostname}"
            )

        # Build parameterized URL
        # Reconstruct with {{variable}} replacing base URL
        path_and_query = parsed.path
        if parsed.params:
            path_and_query += f";{parsed.params}"
        if parsed.query:
            path_and_query += f"?{parsed.query}"
        if parsed.fragment:
            path_and_query += f"#{parsed.fragment}"

        return f"{{{{{var_name}}}}}{path_and_query}"

    def _detect_response_variables(self, response_body: Any, subsequent_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze response body to detect fields that might be used in subsequent requests.

        Args:
            response_body: Parsed response body (dict, list, or string)
            subsequent_requests: List of subsequent request data to check for value reuse

        Returns:
            List of detected variables with extraction info:
            [{"field": "id", "path": "$.id", "value": "12345", "var_name": "user_id", "used_in": [...]}, ...]
        """
        if not self.enable_response_extraction:
            return []

        if not isinstance(response_body, dict):
            return []

        detected_vars = []

        def extract_fields(obj: Dict[str, Any], path_prefix: str = "$") -> None:
            """Recursively extract fields from JSON object."""
            for key, value in obj.items():
                current_path = f"{path_prefix}.{key}"

                # Only consider simple values (strings, numbers) that could be IDs or tokens
                if isinstance(value, (str, int, float)) and value:
                    # Convert to string for comparison
                    value_str = str(value)

                    # Check if this value appears in subsequent requests
                    used_in_requests = []
                    for idx, req_data in enumerate(subsequent_requests):
                        req_url = req_data.get('url', '')
                        req_headers = str(req_data.get('req_headers', {}))
                        req_body = str(req_data.get('req_body', ''))

                        # Check if value appears in URL, headers, or body
                        if value_str in req_url or value_str in req_headers or value_str in req_body:
                            used_in_requests.append(idx)

                    # If value is reused, it's a candidate for extraction
                    if used_in_requests:
                        # Infer variable name from field name
                        var_name = key
                        if key in ['id', 'ID', '_id']:
                            var_name = "resource_id"
                        elif 'token' in key.lower():
                            var_name = f"{key}_token" if not key.lower().endswith('token') else key
                        elif 'code' in key.lower():
                            var_name = f"{key}_code" if not key.lower().endswith('code') else key

                        detected_vars.append({
                            "field": key,
                            "path": current_path,
                            "value": value,
                            "var_name": var_name.lower(),
                            "used_in": used_in_requests
                        })

                # Recursively process nested objects (limit depth to avoid over-extraction)
                elif isinstance(value, dict) and path_prefix.count('.') < 3:
                    extract_fields(value, current_path)

        extract_fields(response_body)
        return detected_vars

    def _generate_test_script(self, variables_to_extract: List[Dict[str, Any]]) -> str:
        """
        Generate Postman test script code to extract variables from response.

        Args:
            variables_to_extract: List of variables with paths and names

        Returns:
            JavaScript code for Postman test script
        """
        if not variables_to_extract:
            return ""

        script_lines = [
            "// Extract variables from response",
            "try {",
            "    const response = pm.response.json();"
        ]

        for var_info in variables_to_extract:
            json_path = var_info['path']
            var_name = var_info['var_name']
            field = var_info['field']

            # Convert JSONPath to JavaScript accessor
            # $.id → response.id
            # $.user.id → response.user.id
            js_accessor = json_path.replace('$', 'response')

            script_lines.extend([
                f"    ",
                f"    // Extract {field} for use in subsequent requests",
                f"    if ({js_accessor} !== undefined) {{",
                f"        pm.collectionVariables.set('{var_name}', {js_accessor});",
                f"        console.log('✓ Extracted {var_name}:', {js_accessor});",
                f"    }}"
            ])

        script_lines.extend([
            "} catch (e) {",
            "    console.error('Failed to extract variables:', e);",
            "}"
        ])

        return "\n".join(script_lines)

    def analyze_captures_for_cross_request_vars(self, captures: List[Dict[str, Any]]) -> None:
        """
        Analyze all captures to detect cross-request variable dependencies.
        Must be called before adding requests to enable response variable extraction.

        Args:
            captures: List of all capture dictionaries with request and response data
        """
        if not self.enable_response_extraction or not captures:
            return

        print(f"\n🔍 Analyzing cross-request variable flow...")

        # For each capture, analyze its response against subsequent requests
        for idx, capture in enumerate(captures):
            response_body = capture.get('res_body', '')

            # Try to parse response as JSON
            parsed_response = None
            if response_body and isinstance(response_body, str):
                try:
                    parsed_response = json.loads(response_body)
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

            if parsed_response:
                # Get subsequent requests for analysis
                subsequent_requests = captures[idx + 1:]

                # Detect variables that should be extracted
                detected_vars = self._detect_response_variables(parsed_response, subsequent_requests)

                if detected_vars:
                    # Store the variables to extract for this request index
                    self.response_variables[idx] = detected_vars

                    # Print detected variables
                    for var in detected_vars:
                        used_count = len(var['used_in'])
                        print(f"  ✓ Request {idx + 1}: Extract '{var['var_name']}' (used in {used_count} subsequent request{'s' if used_count > 1 else ''})")

        if self.response_variables:
            print(f"\n✓ Found {len(self.response_variables)} requests with extractable variables")
        else:
            print(f"  No cross-request variable dependencies detected")

    def add_request(self,
                    name: str,
                    method: str,
                    url: str,
                    headers: Optional[Dict[str, str]] = None,
                    body: Optional[Any] = None,
                    notes: Optional[List[str]] = None,
                    expected_status: Optional[int] = None,
                    request_index: Optional[int] = None) -> None:
        """
        Add a request to the collection.

        Args:
            request_index: Index of this request in the captures list (for response variable extraction)
        """

        # Parameterize path IDs in URL (must be before base URL parameterization)
        if self.enable_path_params:
            url = self._parameterize_path_ids(url)

        # Parameterize base URL (extract scheme://host into variable)
        if self.enable_base_url_params:
            url = self._parameterize_base_url(url)

        # Parameterize JWT tokens in headers
        if self.enable_jwt_params and headers:
            headers = self._parameterize_jwt_token(headers)

        # Build header array, excluding content-length (Postman calculates it automatically)
        header_array = []
        if headers:
            for key, value in headers.items():
                # Skip content-length header - Postman calculates it automatically
                if key.lower() == 'content-length':
                    continue
                header_array.append({
                    "key": key,
                    "value": str(value),
                    "type": "text"
                })

        # Build request body
        request_body = None
        if body:
            if isinstance(body, dict) or isinstance(body, list):
                request_body = {
                    "mode": "raw",
                    "raw": json.dumps(body, indent=2),
                    "options": {
                        "raw": {
                            "language": "json"
                        }
                    }
                }
            elif isinstance(body, str):
                request_body = {
                    "mode": "raw",
                    "raw": body
                }

        # Build the request item
        item = {
            "name": name,
            "request": {
                "method": method.upper(),
                "header": header_array,
                "url": {
                    "raw": url,
                    "protocol": urlparse(url).scheme,
                    "host": urlparse(url).netloc.split(':')[0].split('.'),
                    "path": urlparse(url).path.split('/')[1:],
                }
            }
        }

        if request_body:
            item["request"]["body"] = request_body

        # Add notes and expected status as description
        description_parts = []
        if notes:
            description_parts.extend(notes)
        if expected_status:
            description_parts.append(f"Expected Status: {expected_status}")

        if description_parts:
            item["request"]["description"] = "\n".join(description_parts)

        # Add test script if this request has response variables to extract
        if request_index is not None and request_index in self.response_variables:
            variables_to_extract = self.response_variables[request_index]
            test_script = self._generate_test_script(variables_to_extract)

            if test_script:
                # Add event array with test script
                item["event"] = [
                    {
                        "listen": "test",
                        "script": {
                            "type": "text/javascript",
                            "exec": test_script.split('\n')
                        }
                    }
                ]

                # Add note about variable extraction
                if "request" in item and "description" in item["request"]:
                    item["request"]["description"] += f"\n\n🔄 Extracts variables: {', '.join([v['var_name'] for v in variables_to_extract])}"
                else:
                    item["request"]["description"] = f"🔄 Extracts variables: {', '.join([v['var_name'] for v in variables_to_extract])}"

        self.collection["item"].append(item)

    def save(self, filepath: str) -> None:
        """Save collection to file"""
        with open(filepath, 'w') as f:
            json.dump(self.collection, f, indent=2)


class TraceTapAI:
    """Main application class"""

    def __init__(self, args):
        self.args = args
        self.raw_log = None
        self.flow = None
        self.flow_processor = None
        self.log_processor = None

    def load_raw_log(self) -> None:
        """Load raw HTTP capture log"""
        try:
            with open(self.args.raw_log, 'r') as f:
                data = json.load(f)

            if not isinstance(data, list):
                print(f"Error: Raw log must be a JSON array", file=sys.stderr)
                sys.exit(1)

            # Handle both flat and nested formats
            # Nested format: [{ "session": "...", "requests": [...] }]
            # Flat format: [{ "method": "...", "url": "...", ... }]
            if len(data) > 0 and isinstance(data[0], dict) and 'requests' in data[0]:
                # Nested format - extract requests
                print(f"Detected nested format (session wrapper)")
                self.raw_log = data[0]['requests']
                session_name = data[0].get('session', 'Unknown Session')
                print(f"Session: {session_name}")
                print(f"Loaded {len(self.raw_log)} log entries from {self.args.raw_log}")
            else:
                # Flat format - use as-is
                print(f"Detected flat format")
                self.raw_log = data
                print(f"Loaded {len(self.raw_log)} log entries from {self.args.raw_log}")

            if len(self.raw_log) == 0:
                print(f"Warning: No log entries found in file", file=sys.stderr)

            self.log_processor = RawLogProcessor(self.raw_log)

        except FileNotFoundError:
            print(f"Error: Raw log file '{self.args.raw_log}' not found", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in raw log file: {e}", file=sys.stderr)
            sys.exit(1)

    def load_flow(self) -> None:
        """Load or generate flow YAML"""
        # Determine flow file path
        if self.args.from_flow:
            flow_file = self.args.from_flow
            must_exist = True
        elif self.args.emit_flow:
            flow_file = self.args.emit_flow
            must_exist = False
        else:
            return

        # Check if file exists
        file_exists = os.path.exists(flow_file)

        if not file_exists and must_exist:
            # For --from-flow mode, flow file is required
            print(f"Error: Flow file '{flow_file}' not found", file=sys.stderr)
            sys.exit(1)

        # Check if we should force regeneration
        should_regenerate = (
                not file_exists or
                (hasattr(self.args, 'force_regenerate') and self.args.force_regenerate)
        )

        if should_regenerate and self.args.infer_flow and self.args.emit_flow:
            # Generate flow from raw logs using AI
            if file_exists:
                print(f"Flow file '{flow_file}' exists, but --force-regenerate specified. Regenerating...")
            else:
                print(f"Flow file '{flow_file}' not found, generating from raw logs...")

            if not self.raw_log:
                print(f"Error: Cannot generate flow without raw log data", file=sys.stderr)
                sys.exit(1)

            # Generate flow with AI (SECURITY: API key from environment only)
            flow_generator = AIFlowGenerator(self.raw_log, self.args.flow_intent or "")
            flow_generator.save_flow(flow_file)
            print(f"✓ Generated flow file: {flow_file}")
            print(f"  Analyzed: {len(self.raw_log)} requests")

        # Now load the flow file (either existing or newly generated)
        try:
            with open(flow_file, 'r') as f:
                self.flow = yaml.safe_load(f)

            self.flow_processor = FlowProcessor(self.flow)
            print(f"Loaded flow with {len(self.flow_processor.flow_steps)} steps")

        except FileNotFoundError:
            if must_exist or self.args.infer_flow:
                print(f"Error: Flow file '{flow_file}' not found", file=sys.stderr)
                sys.exit(1)
            else:
                print(f"Warning: Flow file '{flow_file}' not found, will process raw log only",
                      file=sys.stderr)
                self.args.infer_flow = False
        except yaml.YAMLError as e:
            print(f"Error: Invalid YAML in flow file: {e}", file=sys.stderr)
            sys.exit(1)

    def generate_from_flow(self) -> PostmanCollectionBuilder:
        """Generate Postman collection from flow YAML"""
        collection_name = self.flow_processor.get_flow_name()
        description = self.flow_processor.get_flow_description()

        # Create builder with variable extraction settings
        builder = PostmanCollectionBuilder(
            collection_name,
            description,
            enable_variables=not getattr(self.args, 'no_variables', False),
            enable_jwt_params=not getattr(self.args, 'no_jwt_params', False),
            enable_path_params=not getattr(self.args, 'no_path_params', False),
            enable_base_url_params=not getattr(self.args, 'no_base_url_params', False),
            enable_response_extraction=not getattr(self.args, 'no_response_extraction', False)
        )

        # Analyze captures for cross-request variable flow (if raw log is available)
        if hasattr(self, 'log_processor') and self.log_processor:
            builder.analyze_captures_for_cross_request_vars(self.log_processor.log_entries)

        used_entries = set()
        matched_count = 0
        unmatched_steps = []

        print(f"\nMatching flow steps to log entries (strict={self.args.flow_strict})...")

        for step in self.flow_processor.flow_steps:
            step_id = step.get('id', 'unknown')
            step_name = step.get('name', step_id)
            request = step.get('request', {})
            expect = step.get('expect', {})
            notes = step.get('notes', [])

            method = request.get('method', 'GET')
            url = request.get('url', '')
            flow_headers = request.get('headers', {})
            flow_body = request.get('body')
            expected_status = expect.get('status')

            if not url:
                print(f"  ⚠ Skipping step '{step_name}': No URL specified")
                continue

            # Find matching log entry
            entry = self.log_processor.find_matching_entry(
                url=url,
                method=method,
                strict=self.args.flow_strict,
                used_entries=used_entries
            )

            if entry:
                # Use actual data from log entry
                actual_headers = entry.get('req_headers', {})
                actual_body = entry.get('req_body', '')

                # Try to parse body as JSON
                if actual_body and isinstance(actual_body, str):
                    try:
                        actual_body = json.loads(actual_body)
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass

                # Mark this entry as used
                entry_idx = self.log_processor.log_entries.index(entry)
                used_entries.add(entry_idx)

                print(f"  ✓ Matched: {step_name}")
                matched_count += 1

                builder.add_request(
                    name=step_name,
                    method=method,
                    url=url,
                    headers=actual_headers,
                    body=actual_body,
                    notes=notes,
                    expected_status=expected_status
                )
            else:
                # No match found - use flow definition
                print(f"  ✗ No match: {step_name} (using flow definition)")
                unmatched_steps.append(step_name)

                builder.add_request(
                    name=step_name,
                    method=method,
                    url=url,
                    headers=flow_headers,
                    body=flow_body,
                    notes=notes + ["⚠ No matching log entry found - using flow definition"],
                    expected_status=expected_status
                )

        print(f"\nMatching Summary:")
        print(f"  Total steps: {len(self.flow_processor.flow_steps)}")
        print(f"  Matched: {matched_count}")
        print(f"  Unmatched: {len(unmatched_steps)}")

        if unmatched_steps:
            print(f"\nUnmatched steps:")
            for step in unmatched_steps:
                print(f"    - {step}")

        return builder

    def generate_from_raw_log(self) -> PostmanCollectionBuilder:
        """Generate Postman collection directly from raw log"""
        collection_name = "Raw HTTP Capture"
        description = f"Captured on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # Create builder with variable extraction settings
        builder = PostmanCollectionBuilder(
            collection_name,
            description,
            enable_variables=not getattr(self.args, 'no_variables', False),
            enable_jwt_params=not getattr(self.args, 'no_jwt_params', False),
            enable_path_params=not getattr(self.args, 'no_path_params', False),
            enable_base_url_params=not getattr(self.args, 'no_base_url_params', False),
            enable_response_extraction=not getattr(self.args, 'no_response_extraction', False)
        )

        # Analyze captures for cross-request variable flow
        builder.analyze_captures_for_cross_request_vars(self.raw_log)

        print(f"\nProcessing {len(self.raw_log)} log entries...")

        for idx, entry in enumerate(self.raw_log):
            method = entry.get('method', 'GET')
            url = entry.get('url', '')
            headers = entry.get('req_headers', {})
            body = entry.get('req_body', '')
            status = entry.get('status')

            if not url:
                continue

            # Try to parse body as JSON
            if body and isinstance(body, str):
                try:
                    body = json.loads(body)
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

            # Generate name from URL
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split('/') if p]
            name = path_parts[-1] if path_parts else parsed.netloc
            name = f"{idx + 1}. {method} {name}"

            notes = []
            if status:
                notes.append(f"Status: {status}")

            builder.add_request(
                name=name,
                method=method,
                url=url,
                headers=headers,
                body=body,
                notes=notes,
                request_index=idx
            )

        print(f"  ✓ Processed all entries")

        return builder

    def generate_from_flow_only(self) -> PostmanCollectionBuilder:
        """Generate Postman collection directly from flow YAML (no raw logs)"""
        collection_name = self.flow_processor.get_flow_name()
        description = self.flow_processor.get_flow_description()

        # Create builder with variable extraction settings
        builder = PostmanCollectionBuilder(
            collection_name,
            description,
            enable_variables=not getattr(self.args, 'no_variables', False),
            enable_jwt_params=not getattr(self.args, 'no_jwt_params', False),
            enable_path_params=not getattr(self.args, 'no_path_params', False),
            enable_base_url_params=not getattr(self.args, 'no_base_url_params', False),
            enable_response_extraction=not getattr(self.args, 'no_response_extraction', False)
        )

        # Note: No cross-request analysis for flow-only mode (no raw logs available)

        print(f"\nGenerating Postman collection from flow YAML...")
        print(f"  Mode: Flow-only (no raw logs)")
        print(f"  Steps: {len(self.flow_processor.flow_steps)}")

        for step in self.flow_processor.flow_steps:
            step_id = step.get('id', 'unknown')
            step_name = step.get('name', step_id)
            request = step.get('request', {})
            expect = step.get('expect', {})
            notes = step.get('notes', [])

            method = request.get('method', 'GET')
            url = request.get('url', '')
            flow_headers = request.get('headers', {})
            flow_body = request.get('body')
            expected_status = expect.get('status')

            if not url:
                print(f"  ⚠ Skipping step '{step_name}': No URL specified")
                continue

            print(f"  ✓ Added: {step_name}")

            builder.add_request(
                name=step_name,
                method=method,
                url=url,
                headers=flow_headers,
                body=flow_body,
                notes=notes,
                expected_status=expected_status
            )

        print(f"\n✓ Generated {len(builder.collection['item'])} requests from flow definition")

        return builder

    def run(self) -> None:
        """Main execution flow"""
        print("TraceTap AI - Postman Collection Generator")
        print("=" * 50)

        # Determine mode
        if self.args.from_flow:
            print("Mode: Generate from Flow YAML only (no raw logs)")
        elif self.args.match_flow:
            print("Mode: Match Flow with Raw Logs (STRICT matching)")
        elif self.args.infer_flow:
            print(f"Mode: Match Flow with Raw Logs (strict={self.args.flow_strict})")
        else:
            print("Mode: Generate from Raw Logs only")

        if hasattr(self.args, 'force_regenerate') and self.args.force_regenerate:
            print("  ⚠ Force Regenerate: Will regenerate flow even if it exists")

        print()

        # Load raw log (if needed)
        if not self.args.from_flow:
            self.load_raw_log()

        # Load flow (if needed)
        if self.args.infer_flow or self.args.from_flow:
            self.load_flow()

        # Generate collection based on mode
        if self.args.from_flow:
            # Flow-only mode
            if not self.flow_processor:
                print("Error: Failed to load flow file", file=sys.stderr)
                sys.exit(1)
            builder = self.generate_from_flow_only()
        elif self.args.infer_flow and self.flow_processor:
            # Flow matching mode
            builder = self.generate_from_flow()
        else:
            # Raw log only mode
            builder = self.generate_from_raw_log()

        # Save output
        output_file = self.args.output
        builder.save(output_file)

        print(f"\n✓ Postman collection saved to: {output_file}")
        print(f"  Import this file into Postman to use the collection")


def main():
    parser = argparse.ArgumentParser(
        description='Convert raw HTTP captures to Postman collections',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from raw log only
  python tracetap-ai-postman.py raw_data.json -o output.postman.json

  # Generate with flow matching
  python tracetap-ai-postman.py raw_data.json \\
    --infer-flow \\
    --flow-intent "User login and payment flow" \\
    --emit-flow flows/payment.yaml \\
    -o enhanced.postman.json

  # Force regenerate flow even if it exists
  python tracetap-ai-postman.py raw_data.json \\
    --infer-flow \\
    --force-regenerate \\
    --flow-intent "User login and payment flow" \\
    --emit-flow flows/payment.yaml \\
    -o enhanced.postman.json

  # Generate with strict URL matching
  python tracetap-ai-postman.py raw_data.json \\
    --infer-flow \\
    --flow-strict \\
    --emit-flow flows/payment.yaml \\
    -o enhanced.postman.json

  # Generate DIRECTLY from flow YAML (no raw logs needed)
  python tracetap-ai-postman.py \\
    --from-flow flows/payment.yaml \\
    -o flow_based.postman.json

  # Match flow with raw logs (STRICT matching by default)
  python tracetap-ai-postman.py raw_data.json \\
    --match-flow flows/payment.yaml \\
    -o matched.postman.json
        """
    )

    parser.add_argument('raw_log',
                        nargs='?',
                        help='Path to raw HTTP capture log (JSON array)')

    parser.add_argument('--infer-flow',
                        action='store_true',
                        help='Use flow YAML to guide collection generation')

    parser.add_argument('--flow-intent',
                        type=str,
                        help='Description of the flow intent')

    parser.add_argument('--flow-strict',
                        action='store_true',
                        help='Use strict URL matching (include query parameters)')

    parser.add_argument('--emit-flow',
                        type=str,
                        help='Path to flow YAML file')

    parser.add_argument('--force-regenerate',
                        action='store_true',
                        help='Force regenerate flow file even if it already exists (uses Claude AI)')

    parser.add_argument('--from-flow',
                        type=str,
                        help='Generate Postman collection directly from flow YAML (no raw logs required)')

    parser.add_argument('--match-flow',
                        type=str,
                        help='Match flow YAML with raw logs and generate Postman collection (strict matching by default)')

    # Variable extraction flags
    parser.add_argument('--no-variables',
                        action='store_true',
                        help='Disable all variable extraction and parameterization')

    parser.add_argument('--no-jwt-params',
                        action='store_true',
                        help='Disable JWT token parameterization in Authorization headers')

    parser.add_argument('--no-path-params',
                        action='store_true',
                        help='Disable path ID parameterization (UUIDs, numeric IDs, ObjectIds)')

    parser.add_argument('--no-base-url-params',
                        action='store_true',
                        help='Disable base URL parameterization')

    parser.add_argument('--no-response-extraction',
                        action='store_true',
                        help='Disable response variable extraction and test script generation')

    parser.add_argument('-o', '--output',
                        type=str,
                        default='output.postman.json',
                        help='Output Postman collection file (default: output.postman.json)')

    args = parser.parse_args()

    # Validate arguments
    if args.from_flow:
        # Flow-only mode: no raw log needed
        if args.raw_log:
            parser.error("--from-flow mode does not use raw_log argument")
        if args.infer_flow:
            parser.error("--from-flow mode does not use --infer-flow (it's implied)")
        if args.match_flow:
            parser.error("Cannot use both --from-flow and --match-flow")
    elif args.match_flow:
        # Match flow mode: raw log required, strict by default
        if not args.raw_log:
            parser.error("--match-flow requires raw_log argument")
        if args.infer_flow:
            parser.error("--match-flow mode does not use --infer-flow (it's implied)")
        if args.emit_flow:
            parser.error("--match-flow mode uses --match-flow to specify the flow file, not --emit-flow")
        # Force strict mode for match-flow
        args.flow_strict = True
        args.infer_flow = True
        args.emit_flow = args.match_flow
    else:
        # Normal mode: raw log required
        if not args.raw_log:
            parser.error("raw_log is required unless using --from-flow mode")
        if args.infer_flow and not args.emit_flow:
            parser.error("--infer-flow requires --emit-flow to specify the flow file")

    # Force regenerate requires infer-flow
    if args.force_regenerate and not args.infer_flow and not args.match_flow:
        parser.error("--force-regenerate requires --infer-flow or --match-flow")

    try:
        app = TraceTapAI(args)
        app.run()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()