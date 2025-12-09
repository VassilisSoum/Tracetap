"""
Playwright test generator from Postman collections.

Converts Postman Collection v2.1 JSON files into executable Playwright API tests.
"""

from .playwright_generator import PlaywrightGenerator, GenerationResult

__all__ = ['PlaywrightGenerator', 'GenerationResult']
