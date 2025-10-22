#!/usr/bin/env python3
"""
TraceTap AI-Powered Postman Collection Enhancer

Enhances raw TraceTap captures with Claude AI to create clean, organized Postman collections.

Usage:
    python tracetap-ai-postman.py capture.json --output enhanced.json
    python tracetap-ai-postman.py capture.json --merge-with existing.json --output existing.json
"""

import json
import anthropic
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode
from textwrap import dedent

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None


def extract_json_from_response(text: str) -> Optional[Dict]:
    """
    Extract JSON from Claude's response, handling markdown code blocks
    """
    # Try to find JSON in code blocks first
    json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    matches = re.findall(json_pattern, text, re.DOTALL)

    if matches:
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

    # Try to parse the entire response as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Last resort: try to find JSON object in the text
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            try:
                return json.loads(text[json_start:json_end])
            except json.JSONDecodeError:
                pass

    return None


def get_path_pattern(url: str) -> str:
    """
    Get path pattern for matching, replacing variable placeholders and long IDs with wildcards

    Examples:
        /session/ABC123... -> /session/*
        /session/{{token}} -> /session/*
    """
    parsed = urlparse(url)
    path = parsed.path

    # Remove Postman variable placeholders {{variable}}
    path = re.sub(r'\{\{[^}]+\}\}', '*', path)

    # Replace long alphanumeric strings (session tokens, UUIDs, IDs) with wildcards
    # Matches sequences of 30+ alphanumeric characters, underscores, or hyphens
    path = re.sub(r'/[A-Za-z0-9_-]{30,}(?=/|$)', '/*', path)

    # Also replace UUIDs
    path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=/|$)', '/*', path,
                  flags=re.IGNORECASE)

    return path


def normalize_url_for_matching(url: str) -> str:
    """
    Normalize URL for matching (removes tokens, IDs, query params)
    Returns: scheme://host/path_pattern
    """
    parsed = urlparse(url)
    path_pattern = get_path_pattern(url)
    return f"{parsed.scheme}://{parsed.netloc}{path_pattern}"


DEFAULT_FLOW_TEMPLATE = dedent("""\
# FlowSpec version 1 canonical structure
version: 1
metadata:
  title: "<short descriptive title>"
  intent: "<plain-language summary of the user journey>"
  tags: []
flow:
  - id: step_identifier
    name: "Readable step name"
    request:
      method: GET
      url: "https://api.example.com/path"
      headers: {}
      body: null
    expect:
      status: 200
      assertions: []
    notes: []
""").strip()

FLOW_PLACEHOLDER_HOST = "flow.local"


def find_base_url(variables: Optional[List[Dict]]) -> Optional[str]:
    """Extract a usable base URL from Claude's variable recommendations."""
    if not variables:
        return None

    candidate_names = {"base_url", "baseurl", "base-url", "origin", "host", "basehost"}

    for var in variables:
        name = str(var.get('name', '')).lower()
        if name not in candidate_names:
            continue

        raw_value = str(var.get('value', '')).strip()
        if not raw_value:
            continue

        parsed = urlparse(raw_value if '://' in raw_value else f"https://{raw_value.lstrip('/')}")
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}".rstrip('/')

    return None


def ensure_absolute_url(url: str, variables: Optional[List[Dict]] = None) -> str:
    """Ensure a URL has scheme and host information for matching purposes."""
    if not url:
        return ''

    candidate = url.strip()
    if variables:
        candidate = replace_variables_in_url(candidate, variables)
    candidate = candidate.strip()
    if not candidate:
        return ''

    parsed = urlparse(candidate)
    base_url = find_base_url(variables)

    if parsed.scheme and parsed.netloc:
        return candidate

    if parsed.netloc and not parsed.scheme:
        scheme = urlparse(base_url or '').scheme or 'https'
        query = f"?{parsed.query}" if parsed.query else ''
        return f"{scheme}://{parsed.netloc}{parsed.path}{query}"

    if parsed.scheme and not parsed.netloc:
        host = urlparse(base_url or '').netloc or FLOW_PLACEHOLDER_HOST
        query = f"?{parsed.query}" if parsed.query else ''
        return f"{parsed.scheme}://{host}{parsed.path}{query}"

    if candidate.startswith('//'):
        return 'https:' + candidate

    if candidate.startswith('/'):
        target_base = base_url or f"https://{FLOW_PLACEHOLDER_HOST}"
        return f"{target_base.rstrip('/')}{candidate}"

    target_base = base_url or f"https://{FLOW_PLACEHOLDER_HOST}"
    return f"{target_base.rstrip('/')}/{candidate.lstrip('/')}"


def compute_flow_signature(method: str, url: str, variables: Optional[List[Dict]] = None) -> Tuple[str, str, str]:
    """Create a normalized signature (method, host, path pattern) for flow matching."""
    absolute_url = ensure_absolute_url(url, variables)
    method_upper = (method or '').upper()

    if not absolute_url:
        return method_upper, '', ''

    parsed = urlparse(absolute_url)
    host = parsed.netloc.lower()
    path_pattern = get_path_pattern(absolute_url)
    return method_upper, host, path_pattern


def build_flow_map(flow_spec: Dict[str, Any], variables: List[Dict]) -> Tuple[Dict[Tuple[str, str, str], Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Create lookup tables for flow step ordering."""
    flow_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    usage: Dict[str, Dict[str, Any]] = {}

    for order, step in enumerate(flow_spec.get('flow', []) or []):
        if not isinstance(step, dict):
            continue

        request = step.get('request', {})
        method = request.get('method')
        url = request.get('url')
        step_id = step.get('id')

        if not method or not url or not step_id:
            continue

        signature = compute_flow_signature(method, url, variables)
        entry = {'order': order, 'step': step, 'id': step_id}

        if signature not in flow_map:
            flow_map[signature] = entry

        hostless_signature = (signature[0], '', signature[2])
        if hostless_signature not in flow_map:
            flow_map[hostless_signature] = entry

        usage[step_id] = {'used': False, 'step': step, 'order': order}

    return flow_map, usage


def summarize_unique_endpoints(captured_data: Dict, limit: int) -> List[Dict[str, Any]]:
    """Summarize up to `limit` unique endpoints from the capture."""
    seen: Set[Tuple[str, str, str]] = set()
    summary: List[Dict[str, Any]] = []

    requests = captured_data.get('requests', []) or []
    for req in requests:
        url = req.get('url')
        if not url:
            continue

        parsed = urlparse(url)
        host = parsed.netloc or ''
        path = parsed.path or '/'
        method = (req.get('method') or 'GET').upper()
        key = (method, host.lower(), path)

        if key in seen:
            continue

        seen.add(key)
        summary.append({
            'method': method,
            'host': host,
            'path': path or '/',
            'status': req.get('status')
        })

        if limit and len(summary) >= limit:
            break

    return summary


def format_endpoints_summary(endpoints: List[Dict[str, Any]]) -> str:
    """Format the endpoint summary for Claude prompting."""
    lines = []
    for idx, endpoint in enumerate(endpoints, 1):
        status = endpoint.get('status')
        status_text = f"status≈{status}" if status not in (None, '') else "status≈unknown"
        host = endpoint.get('host') or ''
        path = endpoint.get('path') or '/'
        host_path = f"{host}{path}" if host else path
        lines.append(f"{idx}. {endpoint.get('method', 'GET')} {host_path} ({status_text})")
    return '\n'.join(lines)


def strip_code_fences(text: str) -> str:
    """Remove Markdown-style code fences from Claude output."""
    fenced_match = re.match(r"```(?:yaml|yml)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        return fenced_match.group(1)
    return text


def build_flow_prompt(flow_template: str, flow_intent: str, endpoints_summary: str) -> str:
    """Construct the Claude prompt for flow inference."""
    return dedent(f"""
You are TraceTap's FlowSpec author. Given captured HTTP endpoints and a human intent, produce a valid FlowSpec YAML.

FlowSpec canonical template:
---
{flow_template}
---

User intent:
{flow_intent.strip()}

Captured endpoints (deduplicated, up to the requested limit):
{endpoints_summary}

Guidelines:
- Follow FlowSpec version 1 exactly.
- Cover the key steps that fulfil the user's intent using the available endpoints.
- Prefer sequential ordering that mirrors the user flow.
- Include helpful names and keep IDs unique.
- Output ONLY raw YAML without Markdown fences or commentary.
""").strip()


def infer_flow_yaml(captured_data: Dict, api_key: str, flow_intent: str, flow_template: str, max_endpoints: int) -> Optional[str]:
    """Use Claude to infer a FlowSpec YAML description from captured endpoints."""
    endpoints = summarize_unique_endpoints(captured_data, max(1, max_endpoints))

    if not endpoints:
        print("⚠️  No captured endpoints available for flow inference.")
        return None

    summary_text = format_endpoints_summary(endpoints)
    prompt = build_flow_prompt(flow_template, flow_intent, summary_text)

    client = anthropic.Anthropic(api_key=api_key)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            temperature=0.2,
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}]
        )
    except Exception as exc:  # pragma: no cover - network / API failure
        print(f"❌ Flow inference request failed: {exc}")
        return None

    text_blocks: List[str] = []
    for block in message.content:
        if hasattr(block, 'text'):
            text_blocks.append(block.text)
        elif isinstance(block, dict) and 'text' in block:
            text_blocks.append(str(block['text']))

    raw_output = ''.join(text_blocks).strip()
    cleaned = strip_code_fences(raw_output)

    if not cleaned.strip():
        return None

    return cleaned.strip()


def parse_flow_document(flow_text: str) -> Optional[Dict[str, Any]]:
    """Parse YAML or JSON flow content into a Python dictionary."""
    if not flow_text or not flow_text.strip():
        return None

    if yaml is not None:
        try:
            parsed = yaml.safe_load(flow_text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    try:
        parsed_json = json.loads(flow_text)
        if isinstance(parsed_json, dict):
            return parsed_json
    except json.JSONDecodeError:
        return None

    return None


def validate_flow_spec(flow_spec: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate required FlowSpec structure."""
    if not isinstance(flow_spec, dict):
        return False, "Flow specification must be a mapping object."

    if flow_spec.get('version') != 1:
        return False, "FlowSpec version must be 1."

    flow_steps = flow_spec.get('flow')
    if not isinstance(flow_steps, list) or not flow_steps:
        return False, "FlowSpec must contain a non-empty 'flow' list."

    seen_ids: Set[str] = set()
    for idx, step in enumerate(flow_steps):
        if not isinstance(step, dict):
            return False, f"Flow step #{idx + 1} must be a mapping."

        step_id = step.get('id')
        if not step_id:
            return False, f"Flow step #{idx + 1} is missing an 'id'."

        if step_id in seen_ids:
            return False, f"Duplicate flow step id detected: {step_id}"

        seen_ids.add(step_id)

        request = step.get('request')
        if not isinstance(request, dict):
            return False, f"Flow step '{step_id}' is missing a request definition."

        method = request.get('method')
        url = request.get('url')
        if not method or not url:
            return False, f"Flow step '{step_id}' must define request.method and request.url."

    return True, ''

def enhance_with_claude(captured_data: Dict, api_key: str, instructions: Optional[str] = None) -> str:
    """
    Use Claude to enhance and clean captured API traffic before Postman export
    """
    client = anthropic.Anthropic(api_key=api_key)

    # Prepare captured requests summary
    requests_summary = []
    seen_patterns = set()

    for req in captured_data.get('requests', [])[:100]:
        # Create a pattern-based key to show unique endpoints to Claude
        url = req['url']
        method = req['method']
        pattern = normalize_url_for_matching(url)
        pattern_key = f"{method}::{pattern}"

        # Only add unique patterns to summary
        if pattern_key not in seen_patterns:
            seen_patterns.add(pattern_key)
            requests_summary.append({
                'method': method,
                'url': url,
                'status': req['status'],
                'duration_ms': req.get('duration_ms'),
            })

    default_instructions = """
    - Remove ALL duplicate requests (same endpoint called multiple times - keep only ONE)
    - Remove tracking/analytics requests (Google Analytics, Mixpanel, Segment, Amplitude, Hotjar, Facebook Pixel, etc.)
    - Remove OPTIONS preflight requests
    - Remove static asset requests (CSS, JS, images, fonts, etc.)
    - Remove health check/ping endpoints
    - Group related endpoints into logical folders
    - Add clear, human-readable descriptions for each request
    - Identify and extract common variables (auth tokens, base URLs, IDs)
    - Clean sensitive data but keep structure
    - Add example test scenarios where relevant
    - Suggest meaningful names for each request
    """

    user_instructions = instructions or default_instructions

    prompt = f"""
I captured {len(captured_data.get('requests', []))} API requests using a traffic capture tool. 
I want to create a clean, well-organized Postman collection from this data.

IMPORTANT: Many URLs contain session tokens or IDs in the path. When you see patterns like:
- /session/AAABBB123... (long tokens)
- /user/12345 (IDs)

These should be treated as the SAME endpoint and listed only ONCE in enhanced_requests.

Here's a sample of the UNIQUE captured endpoints:
{json.dumps(requests_summary, indent=2)}

CRITICAL INSTRUCTIONS:
1. Remove ALL duplicate requests - each unique endpoint should appear ONLY ONCE
2. Ignore differences in session tokens, user IDs, or other dynamic path parameters
3. In original_url, you can use {{{{variable_name}}}} placeholders for dynamic parts

Output ONLY valid JSON, no markdown formatting or code blocks.

Use this exact JSON structure:
{{
  "recommendations": {{
    "requests_to_remove": ["pattern1", "pattern2"],
    "folder_structure": [
      {{
        "folder_name": "Authentication",
        "description": "Login and auth endpoints",
        "requests": ["url1", "url2"]
      }}
    ],
    "variables": [
      {{"name": "base_url", "value": "https://api.example.com", "description": "API base URL"}}
    ]
  }},
  "enhanced_requests": [
    {{
      "original_url": "https://api.example.com/session/{{{{session_token}}}}",
      "suggested_name": "Get Session",
      "description": "Retrieves session information",
      "folder": "Authentication",
      "test_variations": ["valid session", "expired session"]
    }}
  ]
}}

Additional instructions:
{user_instructions}

Remember: Output ONLY the JSON object. Each unique endpoint should appear ONLY ONCE.
"""

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text


def remove_duplicates_from_enhanced_requests(enhanced_requests: List[Dict]) -> List[Dict]:
    """
    Remove duplicate requests from Claude's enhanced_requests based on URL patterns
    """
    seen = set()
    unique_requests = []

    for req in enhanced_requests:
        url = req.get('original_url', '')
        pattern = normalize_url_for_matching(url)

        if pattern not in seen:
            seen.add(pattern)
            unique_requests.append(req)
        else:
            print(f"  🗑️  Skipping duplicate in Claude's response: {req.get('suggested_name', url)}")

    if len(enhanced_requests) != len(unique_requests):
        print(f"📊 Deduplicated enhanced_requests: {len(enhanced_requests)} → {len(unique_requests)}")

    return unique_requests


def apply_enhancements(captured_data: Dict, enhancements_text: str) -> Optional[Dict]:
    """
    Apply Claude's recommendations to the captured data
    """
    recommendations = extract_json_from_response(enhancements_text)

    if not recommendations:
        print("⚠️  Could not parse Claude's recommendations as JSON")
        print("📄 Here's what Claude returned:")
        print("-" * 60)
        print(enhancements_text[:1000])
        print("-" * 60)
        return None

    # Remove duplicates from enhanced_requests
    enhanced_requests = recommendations.get('enhanced_requests', [])
    enhanced_requests = remove_duplicates_from_enhanced_requests(enhanced_requests)
    recommendations['enhanced_requests'] = enhanced_requests

    # Filter captured requests
    filtered_requests = []
    remove_patterns = recommendations.get('recommendations', {}).get('requests_to_remove', [])
    seen_patterns = set()
    options_removed = 0
    analytics_removed = 0
    duplicates_removed = 0

    for req in captured_data.get('requests', []):
        url = req['url']
        method = req.get('method', 'GET')

        # Create pattern for duplicate detection
        pattern = normalize_url_for_matching(url)
        request_key = f"{method}::{pattern}"

        # Check if duplicate
        if request_key in seen_patterns:
            duplicates_removed += 1
            continue

        # Check removal patterns
        should_remove = False
        for remove_pattern in remove_patterns:
            pattern_lower = remove_pattern.lower()
            url_lower = url.lower()
            method_lower = method.lower()

            # Remove OPTIONS requests
            if method_lower == 'options' and 'options' in pattern_lower:
                should_remove = True
                options_removed += 1
                if options_removed <= 3:
                    print(f"  ❌ Removing OPTIONS: {url[:70]}...")
                break

            # Remove analytics/tracking (check URL against common patterns)
            analytics_patterns = [
                'google-analytics', 'analytics.google', 'googletagmanager',
                'mixpanel', 'segment.', 'amplitude', 'heap.', 'hotjar',
                'facebook.com/tr', 'doubleclick', 'tracking', 'telemetry',
                'metrics', '/collect', '/track', '/beacon', 'pixel'
            ]

            if any(ap in url_lower for ap in analytics_patterns):
                should_remove = True
                analytics_removed += 1
                if analytics_removed <= 3:
                    print(f"  ❌ Removing analytics/tracking: {url[:70]}...")
                break

            # Remove based on other patterns Claude identified
            # Check if URL contains the pattern
            if pattern_lower in url_lower and 'duplicate' not in pattern_lower:
                should_remove = True
                if analytics_removed + options_removed <= 3:
                    print(f"  ❌ Removing (matched pattern '{remove_pattern}'): {url[:70]}...")
                break

        if not should_remove:
            filtered_requests.append(req)
            seen_patterns.add(request_key)

    removed_count = len(captured_data.get('requests', [])) - len(filtered_requests)
    print(f"\n📊 Filtering Summary:")
    print(f"   - Original requests: {len(captured_data.get('requests', []))}")
    print(f"   - Duplicates removed: {duplicates_removed}")
    print(f"   - OPTIONS preflights removed: {options_removed}")
    print(f"   - Analytics/tracking removed: {analytics_removed}")
    print(f"   - Unique requests kept: {len(filtered_requests)}")
    print(f"   - Total removed: {removed_count}")

    return {
        'filtered_requests': filtered_requests,
        'recommendations': recommendations
    }


def replace_variables_in_url(url: str, variables: List[Dict]) -> str:
    """
    Replace actual values in URL with Postman variable syntax {{variable_name}}
    """
    modified_url = url

    # Sort by value length (longest first) to avoid partial replacements
    sorted_vars = sorted(variables, key=lambda x: len(str(x.get('value', ''))), reverse=True)

    for var in sorted_vars:
        var_name = var['name']
        var_value = str(var['value'])

        if var_value and var_value in modified_url:
            modified_url = modified_url.replace(var_value, f"{{{{{var_name}}}}}")

    return modified_url


def expand_variables_in_enhanced_requests(enhanced_requests: List[Dict], variables: List[Dict]) -> List[Dict]:
    """
    Expand {{variable}} placeholders in enhanced request URLs with actual values
    This allows proper matching with captured URLs
    """
    var_map = {var['name']: var['value'] for var in variables}

    expanded = []
    for er in enhanced_requests:
        er_copy = er.copy()
        url = er_copy.get('original_url', '')

        # Replace {{variable}} with actual values
        for var_name, var_value in var_map.items():
            placeholder = f"{{{{{var_name}}}}}"
            if placeholder in url:
                url = url.replace(placeholder, str(var_value))

        er_copy['original_url_expanded'] = url  # Keep expanded version for matching
        expanded.append(er_copy)

    return expanded


def match_enhancement_to_request(req_url: str, enhanced_requests: List[Dict]) -> Optional[Dict]:
    """
    Find the best matching enhanced request for a captured request URL
    Uses pattern matching to handle dynamic IDs/tokens
    """
    req_parsed = urlparse(req_url)
    req_pattern = get_path_pattern(req_url)

    for er in enhanced_requests:
        # Use expanded URL for matching (with variables replaced)
        er_url = er.get('original_url_expanded', er.get('original_url', ''))
        er_parsed = urlparse(er_url)
        er_pattern = get_path_pattern(er_url)

        # Match if same host and same path pattern
        if req_parsed.netloc == er_parsed.netloc:
            # Exact pattern match
            if req_pattern == er_pattern:
                return er

            # Fuzzy match: ignore wildcards
            req_pattern_normalized = req_pattern.replace('/*', '')
            er_pattern_normalized = er_pattern.replace('/*', '')
            if req_pattern_normalized == er_pattern_normalized:
                return er

    return None


def debug_matching_issue(filtered_requests: List[Dict], enhanced_requests: List[Dict]):
    """Debug why requests aren't matching"""
    print("\n" + "=" * 70)
    print("🔬 DETAILED MATCHING DEBUG")
    print("=" * 70 + "\n")

    # Show first filtered request
    if filtered_requests:
        req = filtered_requests[0]
        req_url = req['url']
        print(f"📥 Sample Filtered Request:")
        print(f"  URL: {req_url}")
        print(f"  Pattern: {normalize_url_for_matching(req_url)}")
        print(f"  Parsed: {urlparse(req_url).netloc} | {get_path_pattern(req_url)}")
    else:
        print(f"⚠️  No filtered requests to debug!")

    print()

    # Show first enhanced request
    if enhanced_requests:
        er = enhanced_requests[0]
        er_url = er.get('original_url_expanded', er.get('original_url'))
        print(f"📤 Sample Enhanced Request:")
        print(f"  URL (original): {er.get('original_url')}")
        print(f"  URL (expanded): {er.get('original_url_expanded', '⚠️  NOT EXPANDED!')}")
        print(f"  Pattern: {normalize_url_for_matching(er_url)}")
        print(f"  Parsed: {urlparse(er_url).netloc} | {get_path_pattern(er_url)}")
    else:
        print(f"⚠️  No enhanced requests to debug!")

    print("\n" + "=" * 70 + "\n")


def generate_postman_collection(
    enhanced_data: Dict,
    session_name: str,
    flow_spec: Optional[Dict[str, Any]] = None,
    flow_strict: bool = False
) -> Dict:
    """
    Generate Postman Collection v2.1 with Claude's enhancements and optional flow ordering.
    """
    recommendations = enhanced_data['recommendations']['recommendations']
    enhanced_requests = enhanced_data['recommendations'].get('enhanced_requests', [])
    filtered_requests = enhanced_data['filtered_requests']
    variables = recommendations.get('variables', [])

    flow_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    flow_usage: Dict[str, Dict[str, Any]] = {}

    if flow_spec:
        flow_map, flow_usage = build_flow_map(flow_spec, variables)
        print(f"\n🔁 Applying inferred flow ordering with {len(flow_usage)} steps")

    request_counter = 0

    def annotate_request(postman_request: Dict[str, Any], method: str, original_url: str, url_with_vars: str) -> None:
        nonlocal request_counter
        request_counter += 1
        postman_request['_original_index'] = request_counter

        if not flow_map:
            return

        signatures_to_try = [
            compute_flow_signature(method, original_url),
        ]

        if url_with_vars and url_with_vars != original_url:
            signatures_to_try.append(compute_flow_signature(method, url_with_vars, variables))

        seen_signatures = set()
        for signature in signatures_to_try:
            if not signature or signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            entry = flow_map.get(signature)
            if not entry:
                entry = flow_map.get((signature[0], '', signature[2]))

            if entry:
                postman_request['_flow_order'] = entry['order']
                postman_request['_flow_step_id'] = entry['id']
                usage_entry = flow_usage.get(entry['id'])
                if usage_entry:
                    usage_entry['used'] = True
                break

    # 🔧 DEBUG: Print initial state
    print(f"\n{'=' * 70}")
    print(f"🔍 COLLECTION GENERATION DEBUG")
    print(f"{'=' * 70}\n")
    print(f"📊 Initial state:")
    print(f"   - Enhanced requests: {len(enhanced_requests)}")
    print(f"   - Filtered requests: {len(filtered_requests)}")
    print(f"   - Variables: {len(variables)}")

    if enhanced_requests:
        print(f"   - First enhanced URL (BEFORE expansion): {enhanced_requests[0].get('original_url')}")
    if filtered_requests:
        print(f"   - First filtered URL: {filtered_requests[0].get('url', 'N/A')[:80]}...")

    # ⭐⭐⭐ CRITICAL FIX: Expand variables in enhanced requests ⭐⭐⭐
    print(f"\n🔄 Expanding variables in enhanced requests...")
    enhanced_requests = expand_variables_in_enhanced_requests(enhanced_requests, variables)

    # 🔧 DEBUG: After expansion
    print(f"\n✅ After variable expansion:")
    if enhanced_requests:
        print(
            f"   - First enhanced URL (AFTER expansion): {enhanced_requests[0].get('original_url_expanded', '⚠️  MISSING!')}")

    # Debug matching
    debug_matching_issue(filtered_requests, enhanced_requests)

    # Build folder structure
    folders = {}
    for folder_info in recommendations.get('folder_structure', []):
        folder_name = folder_info['folder_name']
        folders[folder_name] = {
            'name': folder_name,
            'description': folder_info.get('description', ''),
            'item': []
        }

    if 'Uncategorized' not in folders:
        folders['Uncategorized'] = {
            'name': 'Uncategorized',
            'description': 'Requests without a specific category',
            'item': []
        }

    # Track added requests to prevent duplicates
    added_patterns = set()
    match_count = 0
    no_match_count = 0

    # Headers that should be auto-generated and not included
    skip_headers = {
        'content-length',
        'content-encoding',
        'transfer-encoding',
        'host',
        'connection',
        'keep-alive',
        'upgrade-insecure-requests',
        'te'
    }

    # Create a mapping of patterns to captured requests for quick lookup
    captured_by_pattern = {}
    for req in filtered_requests:
        pattern = normalize_url_for_matching(req['url'])
        method = req.get('method', 'GET')
        key = f"{method}::{pattern}"
        if key not in captured_by_pattern:
            captured_by_pattern[key] = req

    print(f"{'=' * 70}")
    print(f"🔗 MATCHING REQUESTS (in Claude's organized order)")
    print(f"{'=' * 70}\n")

    # Process each enhanced request IN ORDER (this maintains Claude's organization)
    for idx, enhancement in enumerate(enhanced_requests):
        # Find the matching captured request
        er_url = enhancement.get('original_url_expanded', enhancement.get('original_url', ''))
        er_pattern = normalize_url_for_matching(er_url)

        # Try to find captured request - check both GET and POST methods
        req = None
        method = None
        for test_method in ['POST', 'GET', 'PUT', 'DELETE', 'PATCH']:
            test_key = f"{test_method}::{er_pattern}"
            if test_key in captured_by_pattern:
                req = captured_by_pattern[test_key]
                method = test_method
                break

        if not req:
            no_match_count += 1
            if no_match_count <= 5:
                print(f"  ❌ NO MATCH #{no_match_count}: {enhancement.get('suggested_name')}")
                print(f"      → Pattern: {er_pattern}")
            continue

        original_url = req['url']
        method = req.get('method', 'GET')
        pattern = normalize_url_for_matching(original_url)
        request_id = f"{method}::{pattern}"

        # Skip if already added
        if request_id in added_patterns:
            continue

        match_count += 1
        if match_count <= 5:  # Show first 5 matches
            print(f"  ✅ MATCH #{match_count}: {enhancement.get('suggested_name')}")
            print(f"      → {method} {original_url[:60]}...")

        # Replace variables in URL
        url_with_vars = replace_variables_in_url(original_url, variables)

        # Determine folder from enhancement
        folder_name = enhancement.get('folder', 'Uncategorized')
        if folder_name not in folders:
            folders[folder_name] = {'name': folder_name, 'item': []}

        # Build Postman URL object
        parsed_vars = urlparse(url_with_vars)

        postman_url = {
            'raw': url_with_vars,
            'protocol': parsed_vars.scheme or 'https',
            'host': parsed_vars.netloc.split('.') if parsed_vars.netloc else [],
            'path': [p for p in parsed_vars.path.split('/') if p]
        }

        # Add query parameters
        if parsed_vars.query:
            query_params = parse_qs(parsed_vars.query)
            postman_url['query'] = []
            for key, values in query_params.items():
                for value in values:
                    value_with_vars = replace_variables_in_url(value, variables)
                    postman_url['query'].append({
                        'key': key,
                        'value': value_with_vars
                    })

        # Replace variables in headers
        headers = []
        for k, v in req.get('req_headers', {}).items():
            # Skip headers that should be auto-generated
            if k.lower() in skip_headers:
                continue

            value_with_vars = replace_variables_in_url(str(v), variables)
            headers.append({
                'key': k,
                'value': value_with_vars,
                'type': 'text'
            })

        # Build Postman request
        request_name = enhancement.get('suggested_name', f"{method} {er_pattern}")
        postman_request = {
            'name': request_name,
            'request': {
                'method': method,
                'header': headers,
                'url': postman_url
            },
            'response': []
        }

        # Add body if present
        if req.get('req_body'):
            body_with_vars = replace_variables_in_url(req['req_body'], variables)
            postman_request['request']['body'] = {
                'mode': 'raw',
                'raw': body_with_vars,
                'options': {
                    'raw': {
                        'language': 'json'
                    }
                }
            }

        # Add description with test variations
        description_parts = []
        if enhancement.get('description'):
            description_parts.append(enhancement['description'])

        if enhancement.get('test_variations'):
            description_parts.append("\n\n**Test Variations:**")
            for variation in enhancement['test_variations']:
                description_parts.append(f"- {variation}")

        if description_parts:
            postman_request['request']['description'] = '\n'.join(description_parts)

        annotate_request(postman_request, method, original_url, url_with_vars)
        # Add to folder
        folders[folder_name]['item'].append(postman_request)
        added_patterns.add(request_id)

    # Add any remaining unmatched requests to Uncategorized
    print(f"\n  🔍 Checking for unmatched captured requests...")
    unmatched_count = 0
    for req in filtered_requests:
        original_url = req['url']
        method = req.get('method', 'GET')
        pattern = normalize_url_for_matching(original_url)
        request_id = f"{method}::{pattern}"

        if request_id not in added_patterns:
            unmatched_count += 1
            if unmatched_count <= 3:
                print(f"  📝 Adding unmatched to Uncategorized: {method} {original_url[:60]}...")

            # Add to Uncategorized folder
            url_with_vars = replace_variables_in_url(original_url, variables)
            parsed_vars = urlparse(url_with_vars)

            postman_url = {
                'raw': url_with_vars,
                'protocol': parsed_vars.scheme or 'https',
                'host': parsed_vars.netloc.split('.') if parsed_vars.netloc else [],
                'path': [p for p in parsed_vars.path.split('/') if p]
            }

            if parsed_vars.query:
                query_params = parse_qs(parsed_vars.query)
                postman_url['query'] = []
                for key, values in query_params.items():
                    for value in values:
                        value_with_vars = replace_variables_in_url(value, variables)
                        postman_url['query'].append({
                            'key': key,
                            'value': value_with_vars
                        })

            headers = []
            for k, v in req.get('req_headers', {}).items():
                if k.lower() not in skip_headers:
                    value_with_vars = replace_variables_in_url(str(v), variables)
                    headers.append({
                        'key': k,
                        'value': value_with_vars,
                        'type': 'text'
                    })

            postman_request = {
                'name': f"{method} {pattern}",
                'request': {
                    'method': method,
                    'header': headers,
                    'url': postman_url
                },
                'response': []
            }

            if req.get('req_body'):
                body_with_vars = replace_variables_in_url(req['req_body'], variables)
                postman_request['request']['body'] = {
                    'mode': 'raw',
                    'raw': body_with_vars,
                    'options': {
                        'raw': {
                            'language': 'json'
                        }
                        }
                    }

            annotate_request(postman_request, method, original_url, url_with_vars)
            folders['Uncategorized']['item'].append(postman_request)
            added_patterns.add(request_id)

    if unmatched_count > 0:
        print(f"  📊 Added {unmatched_count} unmatched requests to Uncategorized")

    missing_flow_steps: List[Dict[str, Any]] = []
    matched_flow_steps_count = 0
    if flow_map:
        missing_flow_steps = [info for info in flow_usage.values() if not info.get('used')]
        matched_flow_steps_count = len(flow_usage) - len(missing_flow_steps)

    # Print match summary
    print(f"\n{'=' * 70}")
    print(f"📈 MATCHING SUMMARY")
    print(f"{'=' * 70}")
    print(f"  ✅ Matched (organized by Claude): {match_count}")
    print(f"  📝 Unmatched (added to Uncategorized): {unmatched_count if 'unmatched_count' in locals() else 0}")
    print(f"  ❌ Enhanced requests without captures: {no_match_count}")
    print(f"  📁 Total added to collection: {len(added_patterns)}")
    if flow_map:
        print(f"  🔁 Flow steps aligned: {matched_flow_steps_count}/{len(flow_usage)}")
        if missing_flow_steps:
            print(f"  ⚠️ Flow steps without matches:")
            for info in missing_flow_steps[:5]:
                step = info['step']
                print(f"     - {step.get('id')} ({step.get('name', 'Unnamed step')})")
            if len(missing_flow_steps) > 5:
                print(f"     ... and {len(missing_flow_steps) - 5} more")
    print(f"{'=' * 70}\n")

    if flow_map and flow_strict and missing_flow_steps:
        raise ValueError("Flow strict mode: some flow steps were not matched to captured requests.")

    # Remove empty folders
    folders = {k: v for k, v in folders.items() if v['item']}

    ordered_folder_entries: List[Tuple[float, int, Dict[str, Any]]] = []
    for idx, (folder_name, folder) in enumerate(folders.items()):
        items = folder['item']
        if flow_map:
            items.sort(key=lambda item: (item.get('_flow_order', float('inf')), item.get('_original_index', 0)))
        else:
            items.sort(key=lambda item: item.get('_original_index', 0))

        folder_flow_index = min((item.get('_flow_order', float('inf')) for item in items), default=float('inf'))

        for item in items:
            item.pop('_original_index', None)
            item.pop('_flow_order', None)
            item.pop('_flow_step_id', None)

        ordered_folder_entries.append((folder_flow_index, idx, folder))

    if flow_map:
        ordered_folders = [entry[2] for entry in sorted(ordered_folder_entries, key=lambda x: (x[0], x[1]))]
    else:
        ordered_folders = [entry[2] for entry in sorted(ordered_folder_entries, key=lambda x: x[1])]

    # Build final collection
    collection = {
        'info': {
            'name': f"{session_name} (AI Enhanced)",
            'description': (
                f"Generated by TraceTap + Claude AI on {datetime.now().isoformat()}\n\n"
                "**AI-Organized Structure** - Requests ordered logically by Claude\n"
                "**Noise Removed** - Analytics, tracking, OPTIONS, and duplicates filtered out\n"
                "**Variables extracted** - Check collection variables below\n"
                "**Auto-generated headers removed** - Content-Length, Host, etc."
            ),
            'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'
        },
        'item': ordered_folders,
        'variable': [
            {
                'key': var['name'],
                'value': var.get('value', ''),
                'type': 'string',
                'description': var.get('description', '')
            }
            for var in variables
        ]
    }

    return collection


def load_existing_collection(filepath: str) -> Optional[Dict]:
    """Load existing Postman collection"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  Collection file not found: {filepath}")
        return None
    except json.JSONDecodeError:
        print(f"⚠️  Invalid JSON in collection file: {filepath}")
        return None


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Enhance TraceTap captures with Claude AI'
    )
    parser.add_argument('capture_file', help='TraceTap JSON capture file')
    parser.add_argument('--api-key', help='Claude API key (or set ANTHROPIC_API_KEY)')
    parser.add_argument('--output', default='enhanced_collection.json', help='Output file')
    parser.add_argument('--instructions', help='Additional instructions for Claude')
    parser.add_argument('--save-analysis', help='Save Claude analysis to file')
    parser.add_argument('--infer-flow', action='store_true', help='Infer a FlowSpec YAML from the capture and flow intent')
    parser.add_argument('--flow-intent', help='Plain text description of the desired flow order')
    parser.add_argument('--flow-intent-file', help='File containing the flow intent description')
    parser.add_argument('--flow-template', help='Optional FlowSpec template YAML to include in the Claude prompt')
    parser.add_argument('--emit-flow', default='flow.generated.yaml', help='Where to write the generated FlowSpec YAML')
    parser.add_argument('--max-endpoints', type=int, default=120, help='Maximum unique endpoints summarized for flow inference')
    parser.add_argument('--flow-strict', action='store_true', help='Require every flow step to match a captured request')

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ Error: Claude API key required")
        print("Set via --api-key or ANTHROPIC_API_KEY environment variable")
        print("Get your key at: https://console.anthropic.com/")
        return

    # Load captured data
    print(f"📂 Loading TraceTap capture from {args.capture_file}...")
    with open(args.capture_file, 'r') as f:
        captured_data = json.load(f)

    print(f"📊 Found {len(captured_data.get('requests', []))} captured requests")

    flow_spec_data: Optional[Dict[str, Any]] = None
    flow_emit_path: Optional[Path] = None
    infer_flow_enabled = args.infer_flow

    if infer_flow_enabled:
        flow_emit_path = Path(args.emit_flow)
        flow_intent_parts: List[str] = []

        if args.flow_intent:
            flow_intent_parts.append(args.flow_intent.strip())

        if args.flow_intent_file:
            try:
                flow_intent_file_text = Path(args.flow_intent_file).read_text()
                flow_intent_parts.append(flow_intent_file_text.strip())
            except OSError as exc:
                print(f"❌ Failed to read flow intent file {args.flow_intent_file}: {exc}")
                if args.flow_strict:
                    return
                print("⚠️  Skipping flow inference due to missing intent file.")
                infer_flow_enabled = False

        flow_intent_text = '\n'.join(part for part in flow_intent_parts if part).strip()

        if infer_flow_enabled and not flow_intent_text:
            print("❌ Flow intent is required when using --infer-flow. Provide --flow-intent or --flow-intent-file.")
            if args.flow_strict:
                return
            print("⚠️  Continuing without inferred flow.")
            infer_flow_enabled = False

        flow_template_text = DEFAULT_FLOW_TEMPLATE
        if infer_flow_enabled and args.flow_template:
            try:
                flow_template_text = Path(args.flow_template).read_text()
            except OSError as exc:
                print(f"⚠️  Could not read flow template {args.flow_template}: {exc}")
                if args.flow_strict:
                    return
                print("⚠️  Falling back to built-in FlowSpec template.")
                flow_template_text = DEFAULT_FLOW_TEMPLATE

        if infer_flow_enabled:
            print("🧠 Inferring flow specification with Claude...")
            flow_yaml_text = infer_flow_yaml(
                captured_data,
                api_key,
                flow_intent_text,
                flow_template_text,
                args.max_endpoints,
            )

            # Persist raw output regardless of validity
            try:
                flow_emit_path.parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass

            flow_yaml_to_save = flow_yaml_text or ''

            try:
                flow_emit_path.write_text(flow_yaml_to_save)
                print(f"💾 Wrote FlowSpec draft to {flow_emit_path}")
            except OSError as exc:
                print(f"❌ Could not write FlowSpec file {flow_emit_path}: {exc}")
                if args.flow_strict:
                    return

            if not flow_yaml_text:
                print("⚠️  Claude did not return FlowSpec content. Please edit the generated file manually.")
            else:
                flow_spec_candidate = parse_flow_document(flow_yaml_text)
                if flow_spec_candidate is None:
                    print("❌ Could not parse Claude's FlowSpec output.")
                    print(f"   → Please review and fix {flow_emit_path} manually.")
                    if args.flow_strict:
                        return
                else:
                    valid, error = validate_flow_spec(flow_spec_candidate)
                    if not valid:
                        print(f"❌ FlowSpec validation failed: {error}")
                        print(f"   → Please review and fix {flow_emit_path} manually.")
                        if args.flow_strict:
                            return
                    else:
                        flow_spec_data = flow_spec_candidate
                        print(f"✅ FlowSpec validated with {len(flow_spec_candidate.get('flow', []))} steps")

    if args.flow_strict and flow_spec_data is None:
        target_path = flow_emit_path or Path(args.emit_flow)
        print("❌ Flow strict mode requires a valid FlowSpec. Please review the generated file and try again.")
        print(f"   → Expected FlowSpec at: {target_path}")
        return

    # Enhance with Claude
    print("🤖 Analyzing with Claude AI...")
    enhancements = enhance_with_claude(captured_data, api_key, args.instructions)

    # Save analysis
    if args.save_analysis:
        with open(args.save_analysis, 'w') as f:
            f.write(enhancements)
        print(f"💾 Saved Claude's analysis to {args.save_analysis}")

    # Apply enhancements
    print("✨ Applying enhancements...")
    enhanced_data = apply_enhancements(captured_data, enhancements)

    if not enhanced_data:
        print("\n⚠️  Could not apply enhancements")
        print(f"💡 Check {args.save_analysis or 'output above'} for details")
        return

    # Generate collection
    print("📝 Generating enhanced Postman collection...")
    session_name = captured_data.get('session', 'TraceTap Session')
    try:
        collection = generate_postman_collection(
            enhanced_data,
            session_name,
            flow_spec=flow_spec_data,
            flow_strict=args.flow_strict,
        )
    except ValueError as exc:
        print(f"❌ {exc}")
        if flow_emit_path or args.emit_flow:
            print(f"   → Update the flow definition at {flow_emit_path or Path(args.emit_flow)} and rerun.")
        return

    # Save collection
    with open(args.output, 'w') as f:
        json.dump(collection, f, indent=2)

    # Print summary
    variables = enhanced_data['recommendations']['recommendations'].get('variables', [])
    total_items = sum(len(folder['item']) for folder in collection.get('item', []))

    print(f"\n{'=' * 70}")
    print(f"✅ SUCCESS!")
    print(f"{'=' * 70}\n")
    print(f"Enhanced Postman collection saved to: {args.output}")
    print(f"\n📌 Summary:")
    print(f"   - Original requests: {len(captured_data.get('requests', []))}")
    print(f"   - Filtered requests: {len(enhanced_data['filtered_requests'])}")
    print(f"   - Unique endpoints in collection: {total_items}")
    print(f"   - Folders: {len(collection.get('item', []))}")
    print(f"   - Variables: {len(variables)}")
    if args.infer_flow:
        flow_steps = flow_spec_data.get('flow', []) if flow_spec_data else []
        print(f"   - Flow steps inferred: {len(flow_steps)}")
        print(f"   - Flow YAML: {flow_emit_path or Path(args.emit_flow)}")

    if variables:
        print(f"\n🔧 Collection Variables:")
        for var in variables[:5]:
            print(f"   - {{{{{var['name']}}}}}: {var.get('description', '')}")
        if len(variables) > 5:
            print(f"   ... and {len(variables) - 5} more")

    print(f"\n🚀 Next steps:")
    print(f"   1. Import {args.output} into Postman")
    print(f"   2. Check collection variables")
    print(f"   3. Update variable values as needed")
    print(f"   4. Start testing your API!")
    print(f"\n💡 Noise removal:")
    print(f"   ✅ Duplicates removed")
    print(f"   ✅ OPTIONS preflights removed")
    print(f"   ✅ Analytics/tracking removed")
    print(f"   ✅ Auto-generated headers removed (content-length, host, etc.)")
    print(f"\n{'=' * 70}\n")


if __name__ == '__main__':
    main()