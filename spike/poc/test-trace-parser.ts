/**
 * Test script for trace parser
 *
 * Creates a sample trace manually to test the parser without browser interaction
 */

import { TraceParser } from './trace-parser';
import AdmZip from 'adm-zip';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Create a sample trace file for testing
 */
function createSampleTrace(outputPath: string): void {
  const sampleTrace = {
    actions: [
      {
        type: 'action',
        apiName: 'page.goto',
        wallTime: Date.now(),
        startTime: 0,
        endTime: 100,
        params: {
          url: 'https://example.com'
        }
      },
      {
        type: 'action',
        apiName: 'page.click',
        wallTime: Date.now() + 1000,
        startTime: 1000,
        endTime: 1050,
        params: {
          selector: 'button[data-testid="login-btn"]'
        }
      },
      {
        type: 'action',
        apiName: 'page.fill',
        wallTime: Date.now() + 2000,
        startTime: 2000,
        endTime: 2200,
        params: {
          selector: 'input[name="email"]',
          value: 'user@example.com'
        }
      },
      {
        type: 'action',
        apiName: 'page.fill',
        wallTime: Date.now() + 3000,
        startTime: 3000,
        endTime: 3150,
        params: {
          selector: 'input[name="password"]',
          value: 'password123'
        }
      },
      {
        type: 'action',
        apiName: 'page.click',
        wallTime: Date.now() + 4000,
        startTime: 4000,
        endTime: 4050,
        params: {
          selector: 'button[type="submit"]'
        }
      }
    ]
  };

  // Create ZIP with trace.trace file
  const zip = new AdmZip();
  zip.addFile('trace.trace', Buffer.from(JSON.stringify(sampleTrace), 'utf8'));
  zip.writeZip(outputPath);

  console.log(`✅ Created sample trace: ${outputPath}`);
}

/**
 * Test the parser
 */
async function testParser() {
  console.log('🧪 Testing Trace Parser\n');

  // Create sample trace
  const samplePath = path.join(__dirname, 'sample-trace.zip');
  createSampleTrace(samplePath);

  // Parse the trace
  const parser = new TraceParser();
  const result = await parser.parse(samplePath);

  // Print results
  parser.printSummary(result);
  parser.printTimeline(result);

  // Validate results
  console.log('\n✅ Validation:');
  console.log(`   Events extracted: ${result.events.length === 5 ? '✅' : '❌'} (expected 5, got ${result.events.length})`);
  console.log(`   Navigate event: ${result.events[0].type === 'navigate' ? '✅' : '❌'}`);
  console.log(`   Click events: ${result.events.filter(e => e.type === 'click').length === 2 ? '✅' : '❌'}`);
  console.log(`   Fill events: ${result.events.filter(e => e.type === 'fill').length === 2 ? '✅' : '❌'}`);

  // Clean up
  fs.unlinkSync(samplePath);
  console.log('\n🧹 Cleaned up test files');
}

// Run test
if (require.main === module) {
  testParser().catch(console.error);
}
