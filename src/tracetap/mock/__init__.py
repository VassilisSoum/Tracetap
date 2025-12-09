"""
TraceTap Mock Server Module

Mock HTTP server functionality for serving captured traffic responses.

This module provides:
- FastAPI-based mock server
- Request matching engine
- AI-powered response generation
- Chaos engineering features
"""

from .server import MockServer, MockConfig, MockMetrics, create_mock_server
from .matcher import RequestMatcher, MatchResult, MatchScore
from .generator import (
    ResponseGenerator,
    ResponseTemplate,
    add_timestamp_transformer,
    replace_ids_transformer,
    cors_headers_transformer,
    pretty_json_transformer
)

__all__ = [
    # Server
    'MockServer',
    'MockConfig',
    'MockMetrics',
    'create_mock_server',

    # Matcher
    'RequestMatcher',
    'MatchResult',
    'MatchScore',

    # Generator
    'ResponseGenerator',
    'ResponseTemplate',
    'add_timestamp_transformer',
    'replace_ids_transformer',
    'cors_headers_transformer',
    'pretty_json_transformer',
]

__version__ = '1.0.0'
