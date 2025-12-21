"""
Main Playwright test generator orchestrator.

Coordinates the conversion of Postman collections to Playwright tests.
"""

import os
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field

try:
    import anthropic
except ImportError:
    anthropic = None

from .postman_parser import PostmanParser, CollectionStructure
from .test_converter import TestConverter, PlaywrightTestFile
from .script_analyzer import ScriptAnalyzer
from .fixture_generator import FixtureGenerator
from .template_engine import TemplateEngine

# Import common utilities for secure API key handling
try:
    from ..common import create_anthropic_client
except ImportError:
    # Fallback if common module not available
    def create_anthropic_client(raise_on_error=False, verbose=True):
        import os
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if api_key and anthropic:
            try:
                return anthropic.Anthropic(api_key=api_key), True, "AI enabled"
            except:
                return None, False, "AI init failed"
        return None, False, "No API key"


@dataclass
class GenerationResult:
    """Result of test generation."""
    success: bool
    output_file: Optional[str] = None
    tests_generated: int = 0
    fixtures_generated: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class PlaywrightGenerator:
    """Main orchestrator for Playwright test generation."""

    def __init__(
        self,
        collection_path: str,
        output_dir: str,
        use_ai: bool = True,
        include_comments: bool = True
    ):
        """
        Initialize generator.

        Args:
            collection_path: Path to Postman collection JSON
            output_dir: Directory for generated test files
            use_ai: Whether to use AI for test script conversion
            include_comments: Include helpful comments in generated code

        Note:
            SECURITY: API key must be set via ANTHROPIC_API_KEY environment variable.
            Never pass API keys as constructor parameters.
        """
        self.collection_path = collection_path
        self.output_dir = Path(output_dir)
        self.include_comments = include_comments

        # Initialize AI client if requested (SECURITY: API key from environment only)
        self.ai_client = None
        if use_ai:
            self.ai_client, _, _ = create_anthropic_client(
                raise_on_error=True,
                verbose=False
            )

        # Initialize components
        self.parser = PostmanParser(collection_path)
        self.converter = None  # Will be initialized with variables
        self.script_analyzer = ScriptAnalyzer(self.ai_client, use_ai=use_ai)
        self.fixture_generator = FixtureGenerator()
        self.template_engine = TemplateEngine()

    def generate(self) -> GenerationResult:
        """
        Generate Playwright tests from Postman collection.

        Returns:
            GenerationResult with success status and details
        """
        try:
            print("🔍 Parsing Postman collection...")
            structure = self.parser.extract_structure()

            print(f"✓ Found {len(structure.requests)} requests")
            if structure.folders:
                print(f"✓ Folder structure: {len(structure.folders)} folders")

            # Initialize converter with variables
            self.converter = TestConverter(structure.variables)

            print("\n🔄 Converting requests to Playwright tests...")
            test_file = self.converter.convert_collection(structure)

            # Convert test scripts
            print("📝 Converting test scripts...")
            self._convert_test_scripts(structure.requests, test_file.tests)

            # Detect which variables are used
            used_variables = self.converter.detect_variable_usage(test_file.tests)

            # Collect all variable extractions
            all_extractions = []
            for test in test_file.tests:
                all_extractions.extend(test.variable_extractions)

            # Generate fixtures
            print("🔧 Generating fixtures...")
            fixtures = self.fixture_generator.generate_fixtures(
                variables=structure.variables,
                auth_config=structure.auth_config,
                used_variables=used_variables,
                variable_extractions=all_extractions
            )

            fixture_extension = ""
            if fixtures:
                fixture_extension = self.fixture_generator.generate_fixture_extension(fixtures)
                print(f"✓ Generated {len(fixtures)} fixtures")

            # Generate TypeScript code
            print("📄 Generating TypeScript test file...")
            typescript_code = self.template_engine.render_test_file(
                test_file=test_file,
                fixtures=fixtures,
                fixture_extension=fixture_extension,
                include_comments=self.include_comments
            )

            # Format code
            typescript_code = self.template_engine.format_typescript(typescript_code)

            # Write to file
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename from collection name
            filename = self._sanitize_filename(structure.name) + '.spec.ts'
            output_path = self.output_dir / filename

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(typescript_code)

            print(f"\n✅ Successfully generated test file!")
            print(f"   Output: {output_path}")
            print(f"   Tests: {len(test_file.tests)}")
            print(f"   Fixtures: {len(fixtures)}")

            return GenerationResult(
                success=True,
                output_file=str(output_path),
                tests_generated=len(test_file.tests),
                fixtures_generated=len(fixtures)
            )

        except Exception as e:
            print(f"\n❌ Error during generation: {e}")
            return GenerationResult(
                success=False,
                errors=[str(e)]
            )

    def _convert_test_scripts(self, requests, tests):
        """Convert test scripts for all requests."""
        for request, test in zip(requests, tests):
            if request.test_script:
                try:
                    assertions, extractions = self.script_analyzer.convert_script(request.test_script)

                    # Add assertions to test
                    test.assertions = assertions

                    # Add extractions
                    test.variable_extractions = [
                        {
                            'variable_name': e.variable_name,
                            'json_path': e.json_path,
                            'description': e.description
                        }
                        for e in extractions
                    ]

                except Exception as e:
                    print(f"   Warning: Could not convert test script for '{test.name}': {e}")
                    # Add as comment
                    test.assertions.append(f"// TODO: Manual review needed - Original test script:")
                    for line in request.test_script:
                        test.assertions.append(f"// {line}")

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize collection name for use as filename."""
        import re
        # Remove special characters
        sanitized = re.sub(r'[^\w\s-]', '', name)
        # Replace spaces and underscores with hyphens
        sanitized = re.sub(r'[\s_]+', '-', sanitized)
        # Convert to lowercase
        sanitized = sanitized.lower()
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')

        return sanitized or 'api-tests'

    def generate_config_template(self) -> str:
        """
        Generate Playwright config template for reference.

        Returns:
            TypeScript config file content
        """
        return """import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',

  // API testing doesn't need browser
  use: {
    baseURL: process.env.BASE_URL || 'https://api.example.com',
    extraHTTPHeaders: {
      // Add any default headers here
    },
  },

  // Timeouts
  timeout: 30000,
  expect: {
    timeout: 5000,
  },

  // Reporters
  reporter: [
    ['html'],
    ['list'],
  ],

  // Run tests in parallel
  workers: process.env.CI ? 1 : undefined,
});
"""
