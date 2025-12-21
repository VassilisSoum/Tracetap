"""
TraceTap Response Generator

AI-powered response generation for mock server.

Features:
- Dynamic response generation based on request
- Template variable substitution
- Response transformation and modification
- AI-powered intelligent responses using Claude
- Stateful response sequences
"""

import json
import re
import os
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from textwrap import dedent

# Import common utilities for AI client
from ..common import create_anthropic_client, ANTHROPIC_AVAILABLE


@dataclass
class ResponseTemplate:
    """Template for generating dynamic responses."""

    status_code: int
    headers: Dict[str, str]
    body_template: str
    variables: Dict[str, Any]

    def render(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render template with context variables.

        Args:
            context: Variables for substitution

        Returns:
            Rendered response dict
        """
        # Merge variables with context
        all_vars = {**self.variables, **context}

        # Substitute in body
        rendered_body = self.body_template
        for key, value in all_vars.items():
            placeholder = f'{{{{{key}}}}}'
            rendered_body = rendered_body.replace(placeholder, str(value))

        # Substitute in headers
        rendered_headers = {}
        for key, value in self.headers.items():
            rendered_value = value
            for var_key, var_value in all_vars.items():
                placeholder = f'{{{{{var_key}}}}}'
                rendered_value = rendered_value.replace(placeholder, str(var_value))
            rendered_headers[key] = rendered_value

        return {
            'status': self.status_code,
            'resp_headers': rendered_headers,
            'resp_body': rendered_body
        }


class ResponseGenerator:
    """
    AI-powered response generator for mock server.

    Provides multiple response generation strategies:
    - Static: Return captured response as-is
    - Template: Variable substitution in response
    - Transform: Apply transformations to response data
    - AI-Generated: Use Claude to generate contextual responses
    - Sequence: Return different responses in sequence

    Example:
        # Simple usage
        generator = ResponseGenerator()
        response = generator.generate(capture, request_context)

        # With AI
        generator = ResponseGenerator(
            use_ai=True,
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )
        response = generator.generate_intelligent(
            capture,
            request_context,
            intent="Create a realistic user profile response"
        )

        # With templates
        template = ResponseTemplate(
            status_code=200,
            headers={'content-type': 'application/json'},
            body_template='{"id": "{{user_id}}", "name": "{{name}}"}'
        )
        generator.add_template('create_user', template)
        response = generator.generate_from_template('create_user', context)
    """

    def __init__(
        self,
        use_ai: bool = False,
        api_key: Optional[str] = None,
        default_transformers: Optional[List[Callable]] = None
    ):
        """
        Initialize response generator.

        Args:
            use_ai: Enable AI-powered response generation
            api_key: Anthropic API key for Claude
            default_transformers: List of default transformation functions
        """
        self.use_ai = use_ai and ANTHROPIC_AVAILABLE
        self.client = None
        self.templates = {}
        self.transformers = default_transformers or []
        self.sequences = {}  # For stateful sequential responses

        # Initialize Claude client using centralized utility
        if self.use_ai:
            self.client, ai_initialized, _ = create_anthropic_client(
                api_key=api_key,
                raise_on_error=False,
                verbose=False
            )
            if not ai_initialized:
                self.use_ai = False

    def generate(
        self,
        capture: Dict[str, Any],
        request_context: Optional[Dict[str, Any]] = None,
        mode: str = "static"
    ) -> Dict[str, Any]:
        """
        Generate response from capture.

        Args:
            capture: Captured request/response data
            request_context: Context from incoming request (path params, query, etc.)
            mode: Generation mode (static, template, transform, ai, intelligent)

        Returns:
            Response dict with status, headers, body
        """
        if mode == "static":
            return self._generate_static(capture)
        elif mode == "template":
            return self._generate_from_template(capture, request_context or {})
        elif mode == "transform":
            return self._generate_transformed(capture, request_context or {})
        elif mode == "ai":
            return self._generate_ai(capture, request_context or {})
        elif mode == "intelligent":
            return self.generate_intelligent(capture, request_context or {})
        else:
            return self._generate_static(capture)

    def _generate_static(self, capture: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate static response (return capture as-is).

        Args:
            capture: Captured request/response data

        Returns:
            Response dict
        """
        return {
            'status': capture.get('status', 200),
            'resp_headers': capture.get('resp_headers', {}),
            'resp_body': capture.get('resp_body', '')
        }

    def _generate_from_template(
        self,
        capture: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate response with template variable substitution.

        Args:
            capture: Captured request/response data
            context: Variables for substitution

        Returns:
            Response dict with substituted values
        """
        response = self._generate_static(capture)

        # Substitute variables in body
        body = response['resp_body']
        if isinstance(body, str):
            for key, value in context.items():
                # Support {{variable}} syntax
                pattern = re.compile(r'\{\{' + re.escape(key) + r'\}\}')
                body = pattern.sub(str(value), body)
            response['resp_body'] = body

        # Substitute in headers
        headers = response['resp_headers']
        for header_key, header_value in headers.items():
            if isinstance(header_value, str):
                for key, value in context.items():
                    pattern = re.compile(r'\{\{' + re.escape(key) + r'\}\}')
                    header_value = pattern.sub(str(value), header_value)
                headers[header_key] = header_value

        return response

    def _generate_transformed(
        self,
        capture: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate response with transformations applied.

        Args:
            capture: Captured request/response data
            context: Request context

        Returns:
            Transformed response dict
        """
        response = self._generate_static(capture)

        # Apply all registered transformers
        for transformer in self.transformers:
            response = transformer(response, context)

        return response

    def _generate_ai(
        self,
        capture: Dict[str, Any],
        context: Dict[str, Any],
        intent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate response using Claude AI.

        Args:
            capture: Captured request/response data
            context: Request context
            intent: Optional intent description

        Returns:
            AI-generated response dict
        """
        if not self.client:
            # Fallback to static
            return self._generate_static(capture)

        # Extract request details from context
        method = context.get('method', 'GET')
        url = context.get('url', '')
        request_body = context.get('body', '')

        # Get original response for reference
        original_response = capture.get('resp_body', '')

        # Create prompt for Claude
        prompt = self._create_generation_prompt(
            method,
            url,
            request_body,
            original_response,
            intent
        )

        try:
            # Call Claude
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            response_text = message.content[0].text
            generated_body = self._extract_response_body(response_text)

            # Determine content type
            content_type = 'application/json'
            try:
                json.loads(generated_body)
            except json.JSONDecodeError:
                content_type = 'text/plain'

            return {
                'status': capture.get('status', 200),
                'resp_headers': {
                    'content-type': content_type,
                    'x-generated-by': 'tracetap-ai'
                },
                'resp_body': generated_body
            }

        except Exception:
            # Fallback to static on error
            return self._generate_static(capture)

    def _create_generation_prompt(
        self,
        method: str,
        url: str,
        request_body: str,
        original_response: str,
        intent: Optional[str] = None
    ) -> str:
        """
        Create prompt for Claude to generate response.

        Args:
            method: HTTP method
            url: Request URL
            request_body: Request body
            original_response: Original captured response
            intent: Optional intent description

        Returns:
            Prompt string
        """
        intent_section = f"\n\nINTENT: {intent}" if intent else ""

        return dedent(f"""
        You are generating a mock HTTP response for API testing.

        INCOMING REQUEST:
        Method: {method}
        URL: {url}
        Body: {request_body[:500] if request_body else '(empty)'}

        ORIGINAL CAPTURED RESPONSE (for reference):
        {original_response[:500] if original_response else '(empty)'}
        {intent_section}

        TASK: Generate a realistic, contextually appropriate HTTP response body.

        INSTRUCTIONS:
        1. Analyze the request to understand what data is expected
        2. Use the original captured response as a reference for structure
        3. Generate realistic, contextually relevant data
        4. If it's JSON, ensure valid JSON syntax
        5. Include appropriate fields based on the request
        6. Make IDs, timestamps, and values realistic

        EXAMPLES:
        - For GET /users/123: Return user details with realistic name, email, etc.
        - For POST /users: Return created user with generated ID
        - For GET /products?category=electronics: Return list of electronic products

        Output ONLY the response body (JSON or text), no explanations:
        """).strip()

    def _extract_response_body(self, response_text: str) -> str:
        """
        Extract response body from Claude's response.

        Args:
            response_text: Claude's full response

        Returns:
            Extracted body content
        """
        # Try to extract JSON from code blocks
        json_pattern = r'```(?:json)?\s*\n(.*?)\n```'
        matches = re.findall(json_pattern, response_text, re.DOTALL)

        if matches:
            return matches[0]

        # Try to parse entire response as JSON
        try:
            json.loads(response_text)
            return response_text
        except json.JSONDecodeError:
            pass

        # Return as-is
        return response_text

    def add_template(self, name: str, template: ResponseTemplate):
        """
        Add a named response template.

        Args:
            name: Template name
            template: ResponseTemplate instance
        """
        self.templates[name] = template

    def generate_from_named_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate response from named template.

        Args:
            template_name: Name of template
            context: Variables for substitution

        Returns:
            Rendered response or None if template not found
        """
        template = self.templates.get(template_name)
        if not template:
            return None

        return template.render(context)

    def generate_intelligent(
        self,
        capture: Dict[str, Any],
        request_context: Dict[str, Any],
        intent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate intelligent response using best available method.

        Tries methods in order:
        1. AI generation (if enabled)
        2. Template substitution (if context has variables)
        3. Transformation (if transformers registered)
        4. Static response

        Args:
            capture: Captured request/response data
            request_context: Request context
            intent: Optional intent description

        Returns:
            Generated response dict
        """
        # Try AI generation first
        if self.use_ai and self.client:
            try:
                return self._generate_ai(capture, request_context, intent)
            except Exception:
                pass

        # Try template if we have context variables
        if request_context:
            try:
                return self._generate_from_template(capture, request_context)
            except Exception:
                pass

        # Try transformers
        if self.transformers:
            try:
                return self._generate_transformed(capture, request_context)
            except Exception:
                pass

        # Fallback to static
        return self._generate_static(capture)


# Common transformer functions

def add_timestamp_transformer(response: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Add current timestamp to response."""
    body = response.get('resp_body', '')

    if isinstance(body, str):
        try:
            data = json.loads(body)
            if isinstance(data, dict):
                data['timestamp'] = datetime.now().isoformat()
                response['resp_body'] = json.dumps(data)
        except json.JSONDecodeError:
            pass

    return response


def replace_ids_transformer(response: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Replace IDs in response with values from context."""
    body = response.get('resp_body', '')

    if isinstance(body, str):
        try:
            data = json.loads(body)

            # Replace IDs recursively
            def replace_in_dict(d: Dict) -> Dict:
                for key, value in d.items():
                    if key in context:
                        d[key] = context[key]
                    elif isinstance(value, dict):
                        d[key] = replace_in_dict(value)
                    elif isinstance(value, list):
                        d[key] = [replace_in_dict(item) if isinstance(item, dict) else item for item in value]
                return d

            if isinstance(data, dict):
                data = replace_in_dict(data)
                response['resp_body'] = json.dumps(data)

        except json.JSONDecodeError:
            pass

    return response


def cors_headers_transformer(response: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Add CORS headers to response."""
    headers = response.get('resp_headers', {})

    headers.update({
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    })

    response['resp_headers'] = headers
    return response


def pretty_json_transformer(response: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Pretty-print JSON responses."""
    body = response.get('resp_body', '')

    if isinstance(body, str):
        try:
            data = json.loads(body)
            response['resp_body'] = json.dumps(data, indent=2)
        except json.JSONDecodeError:
            pass

    return response
