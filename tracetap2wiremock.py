#!/usr/bin/env python3
"""
AI-Powered WireMock Stub Generator
Generates intelligent WireMock stubs using Claude AI, flow YAML, and raw capture files
"""

import argparse
import json
import yaml
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import hashlib

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from tracetap.common import safe_json_parse, create_anthropic_client


class AIWireMockGenerator:
    """Generate intelligent WireMock stubs using Claude AI"""

    def __init__(self):
        """
        Initialize AI WireMock generator.

        Note:
            SECURITY: API key must be set via ANTHROPIC_API_KEY environment variable.
        """
        # Use centralized AI client initialization
        self.client, self.ai_available, _ = create_anthropic_client(
            raise_on_error=False,
            verbose=True
        )

    def analyze_and_generate_stubs(self,
                                   flow_data: Dict[str, Any],
                                   raw_captures: List[Dict[str, Any]],
                                   priority: int = 5) -> List[Dict[str, Any]]:
        """Use Claude AI to analyze flow and captures, generate intelligent stubs"""

        if not self.ai_available:
            print("⚠ AI not available, using basic stub generation")
            return self._generate_basic_stubs(raw_captures, priority)

        print("\n🤖 Using Claude AI to generate intelligent stubs...")

        # Prepare data for Claude
        flow_summary = self._summarize_flow(flow_data)
        captures_summary = self._summarize_captures(raw_captures)

        prompt = f"""Analyze this HTTP flow and raw captures to generate intelligent WireMock stub configurations.

FLOW DEFINITION:
{json.dumps(flow_summary, indent=2)}

RAW CAPTURES (first 10):
{json.dumps(captures_summary[:10], indent=2)}

TASK:
Generate WireMock stub configurations for each request. For each stub:

1. Identify dynamic parameters (IDs, tokens, timestamps) and use regex patterns
2. Determine appropriate URL matching strategy (url, urlPattern, urlPath, urlPathPattern)
3. Set realistic priorities based on specificity
4. Add descriptive names explaining the endpoint purpose
5. Identify which request/response fields should use flexible matching
6. Group related stubs logically

Return a JSON array of stub configurations with this structure:
{{
  "stubs": [
    {{
      "name": "descriptive_name",
      "priority": 1-10,
      "url_strategy": "url|urlPath|urlPattern|urlPathPattern",
      "url_or_pattern": "actual url or pattern",
      "method": "GET|POST|PUT|DELETE",
      "match_headers": ["header1", "header2"],
      "ignore_headers": ["dynamic-header"],
      "match_query_params": ["param1"],
      "ignore_query_params": ["timestamp"],
      "request_body_pattern": "regex pattern or null",
      "response_status": 200,
      "response_body": {{}},
      "response_headers": {{}},
      "notes": "explanation of this stub",
      "tags": ["auth", "user", "payment"]
    }}
  ],
  "recommendations": {{
    "global_ignore_headers": [],
    "global_ignore_query_params": [],
    "dynamic_path_segments": []
  }}
}}

Focus on making stubs reusable and maintainable."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=16000,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse Claude's response
            content = response.content[0].text

            # Extract JSON from response with balanced bracket detection
            json_start = content.find('{')
            if json_start >= 0:
                # Find matching closing brace with proper nesting
                depth = 0
                json_end = -1
                in_string = False
                escape_next = False

                for i in range(json_start, len(content)):
                    char = content[i]

                    if escape_next:
                        escape_next = False
                        continue

                    if char == '\\':
                        escape_next = True
                        continue

                    if char == '"' and not escape_next:
                        in_string = not in_string

                    if not in_string:
                        if char == '{':
                            depth += 1
                        elif char == '}':
                            depth -= 1
                            if depth == 0:
                                json_end = i + 1
                                break

                if json_end > json_start:
                    ai_config = json.loads(content[json_start:json_end])
                    print(f"✓ Claude generated {len(ai_config.get('stubs', []))} intelligent stub configurations")
                    return self._convert_ai_config_to_stubs(ai_config, raw_captures, priority)

            print("⚠ Could not parse AI response, using basic stubs")
            return self._generate_basic_stubs(raw_captures, priority)

        except Exception as e:
            print(f"⚠ AI generation failed: {e}")
            return self._generate_basic_stubs(raw_captures, priority)

    def _summarize_flow(self, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of flow for AI analysis"""
        return {
            "name": flow_data.get("name", "Unknown"),
            "description": flow_data.get("description", ""),
            "steps": [
                {
                    "id": step.get("id"),
                    "name": step.get("name"),
                    "method": step.get("request", {}).get("method"),
                    "url": step.get("request", {}).get("url"),
                    "expect_status": step.get("expect", {}).get("status")
                }
                for step in flow_data.get("steps", [])
            ]
        }

    def _summarize_captures(self, captures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Summarize captures for AI analysis"""
        return [
            {
                "method": cap.get("method"),
                "url": cap.get("url"),
                "status": cap.get("status"),
                "request_headers": list(cap.get("request_headers", {}).keys()),
                "response_headers": list(cap.get("response_headers", {}).keys()),
                "has_request_body": bool(cap.get("request_body")),
                "has_response_body": bool(cap.get("response_body"))
            }
            for cap in captures
        ]

    def _convert_ai_config_to_stubs(self,
                                    ai_config: Dict[str, Any],
                                    raw_captures: List[Dict[str, Any]],
                                    base_priority: int) -> List[Dict[str, Any]]:
        """Convert AI configuration to WireMock stub format"""
        stubs = []
        ai_stubs = ai_config.get("stubs", [])

        for idx, ai_stub in enumerate(ai_stubs):
            # Find matching capture
            capture = self._find_matching_capture(ai_stub, raw_captures)

            if not capture:
                continue

            # Build WireMock stub
            stub = {
                "priority": ai_stub.get("priority", base_priority),
                "request": self._build_request_matcher(ai_stub, capture),
                "response": self._build_response(ai_stub, capture)
            }

            # Add metadata
            stub["metadata"] = {
                "name": ai_stub.get("name", f"stub_{idx}"),
                "notes": ai_stub.get("notes", ""),
                "tags": ai_stub.get("tags", [])
            }

            stubs.append(stub)

        return stubs

    def _find_matching_capture(self, ai_stub: Dict[str, Any], captures: List[Dict[str, Any]]) -> Optional[
        Dict[str, Any]]:
        """Find raw capture matching AI stub configuration"""
        method = ai_stub.get("method", "GET")
        url_pattern = ai_stub.get("url_or_pattern", "")

        for capture in captures:
            if capture.get("method") == method:
                if url_pattern in capture.get("url", ""):
                    return capture

        # No match found - return None instead of first capture
        return None

    def _build_request_matcher(self, ai_stub: Dict[str, Any], capture: Dict[str, Any]) -> Dict[str, Any]:
        """Build WireMock request matcher from AI config and capture"""
        request = {
            "method": ai_stub.get("method", capture.get("method", "GET"))
        }

        # URL matching
        url_strategy = ai_stub.get("url_strategy", "url")
        url_value = ai_stub.get("url_or_pattern", capture.get("url", ""))
        request[url_strategy] = url_value

        # Headers matching
        match_headers = ai_stub.get("match_headers", [])
        if match_headers:
            request["headers"] = {}
            for header in match_headers:
                if header in capture.get("request_headers", {}):
                    request["headers"][header] = {
                        "equalTo": capture["request_headers"][header]
                    }

        # Query parameters
        match_params = ai_stub.get("match_query_params", [])
        if match_params:
            request["queryParameters"] = {}
            parsed = urlparse(capture.get("url", ""))
            for param in match_params:
                request["queryParameters"][param] = {"matches": ".*"}

        # Body matching
        body_pattern = ai_stub.get("request_body_pattern")
        if body_pattern:
            request["bodyPatterns"] = [{"matches": body_pattern}]
        elif capture.get("request_body"):
            body = safe_json_parse(capture["request_body"])
            if body is not None:
                request["bodyPatterns"] = [{"equalToJson": json.dumps(body)}]

        return request

    def _build_response(self, ai_stub: Dict[str, Any], capture: Dict[str, Any]) -> Dict[str, Any]:
        """Build WireMock response from AI config and capture"""
        response = {
            "status": ai_stub.get("response_status", capture.get("status", 200))
        }

        # Response headers
        resp_headers = ai_stub.get("response_headers", {})
        if not resp_headers and capture.get("response_headers"):
            resp_headers = capture["response_headers"]
        if resp_headers:
            response["headers"] = resp_headers

        # Response body
        resp_body = ai_stub.get("response_body")
        if not resp_body and capture.get("response_body"):
            resp_body = safe_json_parse(capture["response_body"], default=capture["response_body"])

        if resp_body:
            if isinstance(resp_body, dict):
                response["jsonBody"] = resp_body
            else:
                response["body"] = str(resp_body)

        return response

    def _generate_basic_stubs(self, captures: List[Dict[str, Any]], priority: int) -> List[Dict[str, Any]]:
        """Fallback basic stub generation without AI"""
        stubs = []

        for idx, capture in enumerate(captures):
            stub = {
                "priority": priority,
                "request": {
                    "method": capture.get("method", "GET"),
                    "url": capture.get("url", "")
                },
                "response": {
                    "status": capture.get("status", 200)
                }
            }

            # Add response body if present
            if capture.get("response_body"):
                body = safe_json_parse(capture["response_body"])
                if body is not None:
                    stub["response"]["jsonBody"] = body
                else:
                    stub["response"]["body"] = capture["response_body"]

            # Add response headers
            if capture.get("response_headers"):
                stub["response"]["headers"] = capture["response_headers"]

            stubs.append(stub)

        return stubs


def load_flow_yaml(filepath: str) -> Dict[str, Any]:
    """Load flow YAML file"""
    try:
        with open(filepath, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"✗ Error loading flow file: {e}")
        sys.exit(1)


def load_raw_captures(filepath: str) -> List[Dict[str, Any]]:
    """Load raw capture JSON file"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            return data.get("requests", data if isinstance(data, list) else [])
    except Exception as e:
        print(f"✗ Error loading captures: {e}")
        sys.exit(1)


def save_stubs(stubs: List[Dict[str, Any]], output_dir: str):
    """Save WireMock stubs to directory"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n💾 Saving {len(stubs)} stubs to {output_path}...")

    for idx, stub in enumerate(stubs, 1):
        # Generate filename
        metadata = stub.get("metadata", {})
        name = metadata.get("name", f"stub_{idx}")

        # Sanitize filename
        name = name.replace(" ", "_").replace("/", "_")
        filename = f"{name}.json"

        # Write stub
        filepath = output_path / filename
        with open(filepath, 'w') as f:
            json.dump(stub, f, indent=2)

        print(f"  ✓ {filename}")

    print(f"\n✓ Successfully created {len(stubs)} WireMock stubs")
    print(f"\nTo use with WireMock:")
    print(f"  java -jar wiremock-standalone.jar --port 8080 --root-dir .")
    print(f"  Or: docker run -p 8080:8080 -v {output_path.absolute()}:/home/wiremock/mappings wiremock/wiremock")


def main():
    parser = argparse.ArgumentParser(
        description='Generate intelligent WireMock stubs using Claude AI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate stubs with AI from flow and captures
  python ai_wiremock_generator.py \\
    --flow flow.yaml \\
    --captures raw_capture.json \\
    --output wiremock/mappings/

  # With custom priority and API key
  python ai_wiremock_generator.py \\
    --flow flow.yaml \\
    --captures raw_capture.json \\
    --output stubs/ \\
    --priority 3 \\
    --api-key sk-ant-xxx

  # Without AI (basic mode)
  python ai_wiremock_generator.py \\
    --captures raw_capture.json \\
    --output stubs/
        """
    )

    parser.add_argument('--flow', '-f',
                        help='Flow YAML file path')

    parser.add_argument('--captures', '-c',
                        required=True,
                        help='Raw capture JSON file path')

    parser.add_argument('--output', '-o',
                        required=True,
                        help='Output directory for WireMock stubs')

    parser.add_argument('--priority', '-p',
                        type=int,
                        default=5,
                        help='Default stub priority (default: 5)')

    parser.add_argument('--api-key',
                        help='Anthropic API key (or set ANTHROPIC_API_KEY env var)')

    args = parser.parse_args()

    print("AI-Powered WireMock Stub Generator")
    print("=" * 50)

    # Load data
    flow_data = {}
    if args.flow:
        print(f"📄 Loading flow: {args.flow}")
        flow_data = load_flow_yaml(args.flow)
        print(f"  ✓ Loaded flow: {flow_data.get('name', 'Unknown')}")

    print(f"📄 Loading captures: {args.captures}")
    raw_captures = load_raw_captures(args.captures)
    print(f"  ✓ Loaded {len(raw_captures)} HTTP captures")

    # Initialize AI generator
    generator = AIWireMockGenerator(api_key=args.api_key)

    # Generate stubs
    stubs = generator.analyze_and_generate_stubs(
        flow_data=flow_data,
        raw_captures=raw_captures,
        priority=args.priority
    )

    # Save stubs
    save_stubs(stubs, args.output)


if __name__ == '__main__':
    main()