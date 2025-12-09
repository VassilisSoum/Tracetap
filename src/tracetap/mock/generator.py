"""
TraceTap Response Generator

AI-powered response generation for mock server.

Features:
- Dynamic response generation based on request
- Template variable substitution
- Response transformation and modification
- AI-powered intelligent responses using Claude
- Stateful response sequences
- Data faker integration for realistic mock data
"""

import json
import re
import os
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from textwrap import dedent

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from faker import Faker
    FAKER_AVAILABLE = True
except ImportError:
    FAKER_AVAILABLE = False


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
        default_transformers: Optional[List[Callable]] = None,
        use_faker: bool = False,
        faker_locale: str = "en_US",
        faker_seed: Optional[int] = None
    ):
        """
        Initialize response generator.

        Args:
            use_ai: Enable AI-powered response generation
            api_key: Anthropic API key for Claude
            default_transformers: List of default transformation functions
            use_faker: Enable Faker for realistic data generation
            faker_locale: Locale for Faker (e.g., en_US, fr_FR)
            faker_seed: Seed for Faker (for reproducible data)
        """
        self.use_ai = use_ai and ANTHROPIC_AVAILABLE
        self.client = None
        self.templates = {}
        self.transformers = default_transformers or []
        self.sequences = {}  # For stateful sequential responses

        # Initialize Faker
        self.use_faker = use_faker and FAKER_AVAILABLE
        self.faker = None
        if self.use_faker:
            try:
                self.faker = Faker(faker_locale)
                if faker_seed is not None:
                    self.faker.seed_instance(faker_seed)
            except Exception:
                self.use_faker = False

        # Initialize Claude client
        if self.use_ai:
            actual_api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
            if actual_api_key:
                try:
                    self.client = anthropic.Anthropic(api_key=actual_api_key)
                except Exception:
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
            mode: Generation mode (static, template, transform, faker, ai, intelligent)

        Returns:
            Response dict with status, headers, body
        """
        if mode == "static":
            return self._generate_static(capture)
        elif mode == "template":
            return self._generate_from_template(capture, request_context or {})
        elif mode == "transform":
            return self._generate_transformed(capture, request_context or {})
        elif mode == "faker":
            return self._generate_faker(capture, request_context or {})
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

    def _generate_faker(
        self,
        capture: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate response with Faker realistic data.

        Args:
            capture: Captured request/response data
            context: Request context

        Returns:
            Response dict with Faker-generated data
        """
        if not self.faker:
            # Fallback to static if Faker not available
            return self._generate_static(capture)

        response = self._generate_static(capture)
        body = response.get('resp_body', '')

        if not body or not isinstance(body, str):
            return response

        try:
            # Try to parse as JSON
            data = json.loads(body)

            # Generate realistic data
            value_cache = {}  # Cache for consistent values within response
            faked_data = self._faker_transform_value(data, value_cache)

            # Update response
            response['resp_body'] = json.dumps(faked_data)
            response['resp_headers'] = response.get('resp_headers', {})
            response['resp_headers']['x-generated-by'] = 'tracetap-faker'

        except json.JSONDecodeError:
            # Not JSON, return as-is
            pass

        return response

    def _faker_transform_value(
        self,
        value: Any,
        cache: Dict[str, Any],
        key: str = ''
    ) -> Any:
        """
        Recursively transform value using Faker.

        Args:
            value: Value to transform
            cache: Cache for consistent values
            key: Current key name (for type detection)

        Returns:
            Transformed value
        """
        if not self.faker:
            return value

        # Handle different value types
        if isinstance(value, dict):
            return {k: self._faker_transform_value(v, cache, k) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._faker_transform_value(item, cache, key) for item in value]
        elif isinstance(value, str):
            return self._faker_generate_string(value, key.lower(), cache)
        elif isinstance(value, (int, float)) and key:
            return self._faker_generate_number(value, key.lower(), cache)
        else:
            return value

    def _faker_generate_string(
        self,
        original: str,
        key: str,
        cache: Dict[str, Any]
    ) -> str:
        """
        Generate realistic string value based on key name.

        Args:
            original: Original value
            key: Field name
            cache: Value cache for consistency

        Returns:
            Faker-generated string
        """
        if not self.faker:
            return original

        # Check cache first for consistency
        cache_key = f"{key}:{original}"
        if cache_key in cache:
            return cache[key]

        # Detect field type and generate appropriate data
        generated = original

        # Email detection
        if 'email' in key or '@' in original:
            generated = self.faker.email()

        # Name detection
        elif 'name' in key or 'username' in key:
            if 'first' in key or 'fname' in key:
                generated = self.faker.first_name()
            elif 'last' in key or 'lname' in key:
                generated = self.faker.last_name()
            else:
                generated = self.faker.name()

        # Phone detection
        elif 'phone' in key or 'mobile' in key or 'tel' in key:
            generated = self.faker.phone_number()

        # Address detection
        elif 'address' in key or 'street' in key:
            generated = self.faker.address()
        elif 'city' in key:
            generated = self.faker.city()
        elif 'state' in key:
            generated = self.faker.state()
        elif 'zip' in key or 'postal' in key:
            generated = self.faker.zipcode()
        elif 'country' in key:
            generated = self.faker.country()

        # Company detection
        elif 'company' in key or 'organization' in key:
            generated = self.faker.company()

        # URL detection
        elif 'url' in key or 'website' in key or original.startswith('http'):
            generated = self.faker.url()

        # Description/text detection
        elif 'description' in key or 'comment' in key or 'bio' in key:
            generated = self.faker.text(max_nb_chars=len(original) if len(original) > 20 else 100)

        # Title detection
        elif 'title' in key or 'subject' in key:
            generated = self.faker.sentence(nb_words=5).rstrip('.')

        # UUID detection
        elif 'uuid' in key or 'guid' in key or len(original) == 36:
            generated = self.faker.uuid4()

        # Date/time detection
        elif 'date' in key or 'time' in key or 'created' in key or 'updated' in key:
            if 'date' in key:
                generated = self.faker.date()
            else:
                generated = self.faker.iso8601()

        # Color detection
        elif 'color' in key:
            generated = self.faker.color_name()

        # IP address detection
        elif 'ip' in key or re.match(r'\d+\.\d+\.\d+\.\d+', original):
            generated = self.faker.ipv4()

        # Cache the generated value
        cache[cache_key] = generated
        return generated

    def _faker_generate_number(
        self,
        original: Any,
        key: str,
        cache: Dict[str, Any]
    ) -> Any:
        """
        Generate realistic number value based on key name.

        Args:
            original: Original value
            key: Field name
            cache: Value cache for consistency

        Returns:
            Faker-generated number
        """
        if not self.faker:
            return original

        # Check cache
        cache_key = f"{key}:{original}"
        if cache_key in cache:
            return cache[cache_key]

        generated = original

        # ID detection (generate new ID)
        if 'id' in key:
            if isinstance(original, int):
                generated = self.faker.random_int(min=1, max=999999)
            else:
                generated = self.faker.random_int(min=1, max=999999)

        # Age detection
        elif 'age' in key:
            generated = self.faker.random_int(min=18, max=80)

        # Price/amount detection
        elif 'price' in key or 'amount' in key or 'cost' in key:
            if isinstance(original, float):
                generated = round(self.faker.random.uniform(1.0, 1000.0), 2)
            else:
                generated = self.faker.random_int(min=1, max=10000)

        # Quantity/count detection
        elif 'quantity' in key or 'count' in key or 'qty' in key:
            generated = self.faker.random_int(min=1, max=100)

        # Percentage detection
        elif 'percent' in key or 'rate' in key:
            if isinstance(original, float):
                generated = round(self.faker.random.uniform(0.0, 100.0), 2)
            else:
                generated = self.faker.random_int(min=0, max=100)

        # Cache and return
        cache[cache_key] = generated
        return generated

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

    def add_transformer(self, transformer: Callable):
        """
        Add a response transformer function.

        Transformer signature: (response: Dict, context: Dict) -> Dict

        Args:
            transformer: Transformer function
        """
        self.transformers.append(transformer)

    def create_sequence(self, name: str, responses: List[Dict[str, Any]]):
        """
        Create a named sequence of responses.

        Each time this sequence is requested, it returns the next response
        in the list (cycling back to start).

        Args:
            name: Sequence name
            responses: List of response dicts
        """
        self.sequences[name] = {
            'responses': responses,
            'index': 0
        }

    def get_next_from_sequence(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get next response from named sequence.

        Args:
            name: Sequence name

        Returns:
            Next response or None if sequence not found
        """
        if name not in self.sequences:
            return None

        sequence = self.sequences[name]
        responses = sequence['responses']
        index = sequence['index']

        if not responses:
            return None

        # Get current response
        response = responses[index]

        # Advance index (cycling)
        sequence['index'] = (index + 1) % len(responses)

        return response

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
