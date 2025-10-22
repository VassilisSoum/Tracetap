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


def generate_postman_collection(enhanced_data: Dict, session_name: str) -> Dict:
    """
    Generate Postman Collection v2.1 with Claude's enhancements and NO duplicates
    """
    recommendations = enhanced_data['recommendations']['recommendations']
    enhanced_requests = enhanced_data['recommendations'].get('enhanced_requests', [])
    filtered_requests = enhanced_data['filtered_requests']
    variables = recommendations.get('variables', [])

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

            folders['Uncategorized']['item'].append(postman_request)
            added_patterns.add(request_id)

    if unmatched_count > 0:
        print(f"  📊 Added {unmatched_count} unmatched requests to Uncategorized")

    # Print match summary
    print(f"\n{'=' * 70}")
    print(f"📈 MATCHING SUMMARY")
    print(f"{'=' * 70}")
    print(f"  ✅ Matched (organized by Claude): {match_count}")
    print(f"  📝 Unmatched (added to Uncategorized): {unmatched_count if 'unmatched_count' in locals() else 0}")
    print(f"  ❌ Enhanced requests without captures: {no_match_count}")
    print(f"  📁 Total added to collection: {len(added_patterns)}")
    print(f"{'=' * 70}\n")

    # Remove empty folders
    folders = {k: v for k, v in folders.items() if v['item']}

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
        'item': list(folders.values()),
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
    collection = generate_postman_collection(enhanced_data, session_name)

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