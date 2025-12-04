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

    def __init__(self, raw_log: List[Dict[str, Any]], flow_intent: str = "", api_key: Optional[str] = None):
        self.raw_log = raw_log
        self.flow_intent = flow_intent
        self.client = None
        self.ai_available = False

        # Check if anthropic library is available
        if not ANTHROPIC_AVAILABLE:
            self.ai_message = "⚠ Claude AI not available: anthropic library not installed\n  Install: pip install anthropic"
            return

        # Check for API key (parameter or environment)
        actual_api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not actual_api_key:
            self.ai_message = "⚠ Claude AI not available: ANTHROPIC_API_KEY not set\n  Set: export ANTHROPIC_API_KEY=your_key_here\n  Or: --api-key your_key\n  Get key: https://console.anthropic.com/"
            return

        # Initialize client
        try:
            self.client = anthropic.Anthropic(api_key=actual_api_key)
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

    def __init__(self, name: str, description: str = ""):
        self.collection = {
            "info": {
                "name": name,
                "description": description,
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": []
        }

    def add_request(self,
                    name: str,
                    method: str,
                    url: str,
                    headers: Optional[Dict[str, str]] = None,
                    body: Optional[Any] = None,
                    notes: Optional[List[str]] = None,
                    expected_status: Optional[int] = None) -> None:
        """Add a request to the collection"""

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

            # Generate flow with AI
            api_key = self.args.api_key if hasattr(self.args, 'api_key') else None
            flow_generator = AIFlowGenerator(self.raw_log, self.args.flow_intent or "", api_key=api_key)
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

        builder = PostmanCollectionBuilder(collection_name, description)

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

        builder = PostmanCollectionBuilder(collection_name, description)

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
                notes=notes
            )

        print(f"  ✓ Processed all entries")

        return builder

    def generate_from_flow_only(self) -> PostmanCollectionBuilder:
        """Generate Postman collection directly from flow YAML (no raw logs)"""
        collection_name = self.flow_processor.get_flow_name()
        description = self.flow_processor.get_flow_description()

        builder = PostmanCollectionBuilder(collection_name, description)

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

    parser.add_argument('--api-key',
                        type=str,
                        help='Anthropic API key for AI-powered flow generation (or set ANTHROPIC_API_KEY env var)')

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