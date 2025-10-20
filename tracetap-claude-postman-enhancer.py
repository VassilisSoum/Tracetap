import json
import anthropic
import os
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def extract_json_from_response(text):
    """
    Extract JSON from Claude's response, handling markdown code blocks
    """
    # Try to find JSON in code blocks first
    json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    matches = re.findall(json_pattern, text, re.DOTALL)

    if matches:
        # Try each match until we find valid JSON
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

    # If no code blocks, try to parse the entire response as JSON
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


def enhance_with_claude(captured_data, api_key, instructions=None):
    """
    Use Claude to enhance and clean captured API traffic before Postman export
    """
    client = anthropic.Anthropic(api_key=api_key)

    # Prepare captured requests summary
    requests_summary = []
    for req in captured_data.get('requests', [])[:50]:  # Limit for context
        requests_summary.append({
            'method': req['method'],
            'url': req['url'],
            'status': req['status'],
            'duration_ms': req.get('duration_ms'),
            'req_headers': {k: v for k, v in list(req.get('req_headers', {}).items())[:5]},  # Limit headers
            'has_body': bool(req.get('req_body', '')),
        })

    default_instructions = """
    - Remove tracking/analytics requests (Google Analytics, Mixpanel, etc.)
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

Here's a sample of the captured requests:
{json.dumps(requests_summary, indent=2)}

Please analyze these requests and provide recommendations.

IMPORTANT: Output ONLY valid JSON, no markdown formatting or code blocks.

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
      "original_url": "https://api.example.com/login",
      "suggested_name": "Login User",
      "description": "Authenticates user and returns JWT token",
      "folder": "Authentication",
      "test_variations": ["successful login", "invalid credentials"]
    }}
  ]
}}

Additional instructions:
{user_instructions}

Remember: Output ONLY the JSON object, nothing else.
"""

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text


def replace_variables_in_url(url, variables):
    """
    Replace actual values in URL with Postman variable syntax {{variable_name}}
    """
    modified_url = url

    # Sort variables by value length (longest first) to avoid partial replacements
    sorted_vars = sorted(variables, key=lambda x: len(str(x.get('value', ''))), reverse=True)

    for var in sorted_vars:
        var_name = var['name']
        var_value = str(var['value'])

        if var_value and var_value in modified_url:
            modified_url = modified_url.replace(var_value, f"{{{{{var_name}}}}}")

    return modified_url


def apply_enhancements(captured_data, enhancements_text):
    """
    Apply Claude's recommendations to the captured data
    """
    # Try to extract JSON from the response
    recommendations = extract_json_from_response(enhancements_text)

    if not recommendations:
        print("⚠️  Could not parse Claude's recommendations as JSON")
        print("📄 Here's what Claude returned:")
        print("-" * 60)
        print(enhancements_text[:1000])
        print("-" * 60)
        return None

    # Filter out noise
    filtered_requests = []
    remove_patterns = recommendations.get('recommendations', {}).get('requests_to_remove', [])

    for req in captured_data.get('requests', []):
        should_keep = True
        for pattern in remove_patterns:
            if pattern.lower() in req['url'].lower() or pattern.lower() in req['method'].lower():
                should_keep = False
                print(f"  ❌ Removing: {req['method']} {req['url'][:80]}... (matches: {pattern})")
                break
        if should_keep:
            filtered_requests.append(req)

    print(f"📊 Filtered: {len(captured_data.get('requests', []))} → {len(filtered_requests)} requests")

    return {
        'filtered_requests': filtered_requests,
        'recommendations': recommendations
    }


def generate_postman_collection(enhanced_data, session_name):
    """
    Generate Postman Collection v2.1 with Claude's enhancements
    """
    recommendations = enhanced_data['recommendations']['recommendations']
    enhanced_requests = enhanced_data['recommendations'].get('enhanced_requests', [])
    filtered_requests = enhanced_data['filtered_requests']
    variables = recommendations.get('variables', [])

    # Create variable lookup
    request_enhancements = {er.get('original_url', ''): er for er in enhanced_requests}

    # Build folder structure
    folders = {}
    for folder_info in recommendations.get('folder_structure', []):
        folder_name = folder_info['folder_name']
        folders[folder_name] = {
            'name': folder_name,
            'description': folder_info.get('description', ''),
            'item': []
        }

    # Add "Uncategorized" folder for requests without a folder
    if 'Uncategorized' not in folders:
        folders['Uncategorized'] = {
            'name': 'Uncategorized',
            'description': 'Requests without a specific category',
            'item': []
        }

    # Add requests to folders
    for req in filtered_requests:
        original_url = req['url']

        # Replace variables in URL
        url_with_vars = replace_variables_in_url(original_url, variables)

        enhancement = request_enhancements.get(original_url, {})

        folder_name = enhancement.get('folder', 'Uncategorized')
        if folder_name not in folders:
            folders[folder_name] = {'name': folder_name, 'item': []}

        # Parse URL with variables
        parsed = urlparse(url_with_vars)
        protocol = parsed.scheme or 'https'
        host = parsed.netloc
        path = parsed.path
        query = parsed.query

        # Build URL object for Postman
        postman_url = {
            'raw': url_with_vars,
            'protocol': protocol,
            'host': host.split('.') if host else [],
            'path': [p for p in path.split('/') if p]
        }

        # Add query parameters if present
        if query:
            query_params = parse_qs(query)
            postman_url['query'] = []
            for key, values in query_params.items():
                for value in values:
                    # Replace variables in query parameter values too
                    value_with_vars = replace_variables_in_url(value, variables)
                    postman_url['query'].append({
                        'key': key,
                        'value': value_with_vars
                    })

        # Replace variables in headers
        headers = []
        for k, v in req.get('req_headers', {}).items():
            value_with_vars = replace_variables_in_url(str(v), variables)
            headers.append({
                'key': k,
                'value': value_with_vars,
                'type': 'text'
            })

        # Build Postman request
        postman_request = {
            'name': enhancement.get('suggested_name', f"{req['method']} {original_url}"),
            'request': {
                'method': req['method'],
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

        folders[folder_name]['item'].append(postman_request)

    # Remove empty folders
    folders = {k: v for k, v in folders.items() if v['item']}

    # Build collection
    collection = {
        'info': {
            'name': f"{session_name} (AI Enhanced)",
            'description': f"Generated by TraceTap + Claude AI on {datetime.now().isoformat()}\n\n**Variables have been extracted** - check the collection variables below.",
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


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Enhance TraceTap captures with Claude AI before generating Postman collections'
    )
    parser.add_argument('capture_file', help='TraceTap JSON capture file')
    parser.add_argument('--api-key', help='Claude API key (or set ANTHROPIC_API_KEY env var)')
    parser.add_argument('--output', default='enhanced_collection.json', help='Output Postman collection file')
    parser.add_argument('--instructions', help='Additional instructions for Claude')
    parser.add_argument('--save-analysis', help='Save Claude\'s analysis to a file')

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ Error: Please provide Claude API key via --api-key or ANTHROPIC_API_KEY env var")
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

    # Save analysis if requested
    if args.save_analysis:
        with open(args.save_analysis, 'w') as f:
            f.write(enhancements)
        print(f"💾 Saved Claude's analysis to {args.save_analysis}")

    # Apply enhancements
    print("✨ Applying enhancements...")
    enhanced_data = apply_enhancements(captured_data, enhancements)

    if not enhanced_data:
        print("\n⚠️  Could not apply enhancements automatically")
        print(f"💡 Check {args.save_analysis or 'the output above'} to see what Claude returned")
        print("💡 You may need to manually format the JSON or adjust the prompt")
        return

    # Generate Postman collection
    print("📝 Generating enhanced Postman collection...")
    session_name = captured_data.get('session', 'TraceTap Session')
    collection = generate_postman_collection(enhanced_data, session_name)

    # Save collection
    with open(args.output, 'w') as f:
        json.dump(collection, f, indent=2)

    variables = enhanced_data['recommendations']['recommendations'].get('variables', [])

    print(f"\n✅ Done! Enhanced Postman collection saved to {args.output}")
    print(f"\n📌 Summary:")
    print(
        f"   - Filtered: {len(captured_data.get('requests', []))} → {len(enhanced_data['filtered_requests'])} requests")
    print(f"   - Folders: {len(enhanced_data['recommendations']['recommendations'].get('folder_structure', []))}")
    print(f"   - Variables extracted: {len(variables)}")

    if variables:
        print(f"\n🔧 Collection Variables:")
        for var in variables:
            print(f"   - {{{{{{{{var['name']}}}}}}}}: {var.get('description', 'No description')}")

    print(f"\n🚀 Import {args.output} into Postman to use your enhanced collection!")
    print(
        f"💡 All URLs have been updated to use collection variables like {{{{base_url}}}}, {{{{session_token}}}}, etc.")


if __name__ == '__main__':
    main()