#!/usr/bin/env python3
"""
Unit tests for CodegenParser.

Tests the parsing of Playwright codegen output into TraceTap events.
"""

import tempfile
import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tracetap.record.codegen_parser import CodegenParser


# Sample codegen output (what playwright codegen generates)
SAMPLE_CODEGEN = """
import asyncio
from playwright.async_api import Playwright, async_playwright


async def run(playwright: Playwright) -> None:
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    await page.goto("https://example.com")
    await page.click("#login-button")
    await page.fill("input[name='email']", "user@example.com")
    await page.fill("input[name='password']", "secretpass123")
    await page.press("input[name='password']", "Enter")
    await page.click("text=Dashboard")
    await page.hover(".profile-menu")
    await page.select_option("select[name='country']", "US")

    await context.close()
    await browser.close()


async def main() -> None:
    async with async_playwright() as playwright:
        await run(playwright)


asyncio.run(main())
"""


class TestCodegenParser(unittest.TestCase):
    """Test cases for CodegenParser."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = CodegenParser()

    def test_parse_sample_codegen(self):
        """Test parsing a sample codegen output."""
        # Create temporary file with sample code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(SAMPLE_CODEGEN)
            temp_path = f.name

        try:
            # Parse the sample code
            events = self.parser.parse(temp_path)

            # Verify event count
            self.assertEqual(len(events), 8, "Should extract 8 events")

            # Verify event sequence
            expected_api_names = [
                'goto',
                'click',
                'fill',
                'fill',
                'press',
                'click',
                'hover',
                'selectOption',
            ]
            actual_api_names = [e['apiName'] for e in events]
            self.assertEqual(actual_api_names, expected_api_names)

            # Verify specific events
            self.assertEqual(events[0]['apiName'], 'goto')
            self.assertEqual(events[0]['params']['url'], 'https://example.com')

            self.assertEqual(events[1]['apiName'], 'click')
            self.assertEqual(events[1]['params']['selector'], '#login-button')

            self.assertEqual(events[2]['apiName'], 'fill')
            self.assertEqual(events[2]['params']['selector'], "input[name='email']")
            self.assertEqual(events[2]['params']['value'], 'user@example.com')

            self.assertEqual(events[7]['apiName'], 'selectOption')
            self.assertEqual(events[7]['params']['values'], ['US'])

        finally:
            # Clean up temp file
            Path(temp_path).unlink()

    def test_event_structure(self):
        """Test that events have correct structure."""
        code = """
import asyncio
from playwright.async_api import async_playwright

async def run(playwright):
    browser = await playwright.chromium.launch()
    page = await browser.new_page()
    await page.goto("https://test.com")
    await browser.close()

asyncio.run(run)
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            events = self.parser.parse(temp_path)

            # Should have exactly one event (goto)
            self.assertEqual(len(events), 1)

            event = events[0]

            # Verify required fields
            self.assertIn('type', event)
            self.assertIn('apiName', event)
            self.assertIn('sequence', event)
            self.assertIn('timestamp', event)
            self.assertIn('params', event)

            # Verify types
            self.assertEqual(event['type'], 'action')
            self.assertIsInstance(event['sequence'], int)
            self.assertIsInstance(event['timestamp'], (int, float))
            self.assertIsInstance(event['params'], dict)

        finally:
            Path(temp_path).unlink()

    def test_empty_file(self):
        """Test parsing an empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            events = self.parser.parse(temp_path)
            self.assertEqual(len(events), 0, "Empty file should yield no events")
        finally:
            Path(temp_path).unlink()

    def test_nonexistent_file(self):
        """Test parsing a nonexistent file."""
        with self.assertRaises(FileNotFoundError):
            self.parser.parse("/nonexistent/file.py")

    def test_format_events(self):
        """Test formatting events as JSON."""
        events = [
            {
                'type': 'action',
                'apiName': 'click',
                'sequence': 0,
                'timestamp': 1234567890,
                'params': {'selector': '#button'}
            }
        ]

        json_str = self.parser.format_events(events)

        # Should be valid JSON
        import json
        parsed = json.loads(json_str)

        self.assertIn('events', parsed)
        self.assertEqual(len(parsed['events']), 1)
        self.assertEqual(parsed['events'][0]['apiName'], 'click')


if __name__ == '__main__':
    unittest.main()
