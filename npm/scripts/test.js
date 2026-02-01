/**
 * Test script to verify npm package works correctly
 */

const { execSync } = require('child_process');

console.log('Testing TraceTap npm package...\n');

try {
  // Test that tracetap command is available
  const output = execSync('tracetap --version', {
    encoding: 'utf-8',
    stdio: 'pipe'
  });

  console.log('✓ TraceTap command works');
  console.log(`  Version: ${output.trim()}`);
  console.log('\nAll tests passed! ✓');
} catch (error) {
  console.error('✗ TraceTap command failed');
  console.error(`  Error: ${error.message}`);
  process.exit(1);
}
