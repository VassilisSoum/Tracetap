/**
 * Test script for event correlator
 *
 * Creates sample UI events and network traffic to test correlation
 */

import { EventCorrelator, NetworkRequest } from './event-correlator';
import { TraceTapEvent } from './trace-parser';
import * as fs from 'fs';

/**
 * Create sample UI events
 */
function createSampleUIEvents(): TraceTapEvent[] {
  const baseTime = Date.now();

  return [
    {
      type: 'navigate',
      timestamp: baseTime,
      duration: 100,
      url: 'https://example.com/login',
      metadata: {
        apiName: 'page.goto',
        params: { url: 'https://example.com/login' },
        success: true
      }
    },
    {
      type: 'fill',
      timestamp: baseTime + 2000,
      duration: 150,
      selector: 'input[name="email"]',
      value: 'user@example.com',
      metadata: {
        apiName: 'page.fill',
        params: { selector: 'input[name="email"]', value: 'user@example.com' },
        success: true
      }
    },
    {
      type: 'fill',
      timestamp: baseTime + 3000,
      duration: 120,
      selector: 'input[name="password"]',
      value: 'password123',
      metadata: {
        apiName: 'page.fill',
        params: { selector: 'input[name="password"]', value: 'password123' },
        success: true
      }
    },
    {
      type: 'click',
      timestamp: baseTime + 4000,
      duration: 50,
      selector: 'button[type="submit"]',
      metadata: {
        apiName: 'page.click',
        params: { selector: 'button[type="submit"]' },
        success: true
      }
    },
    {
      type: 'navigate',
      timestamp: baseTime + 6000,
      duration: 80,
      url: 'https://example.com/dashboard',
      metadata: {
        apiName: 'page.goto',
        params: { url: 'https://example.com/dashboard' },
        success: true
      }
    }
  ];
}

/**
 * Create sample network traffic
 */
function createSampleNetworkTraffic(): NetworkRequest[] {
  const baseTime = Date.now();

  return [
    {
      method: 'GET',
      url: 'https://example.com/login',
      host: 'example.com',
      path: '/login',
      timestamp: baseTime + 50,  // 50ms after navigate
      request: {
        headers: { 'User-Agent': 'Mozilla/5.0' }
      },
      response: {
        status: 200,
        headers: { 'Content-Type': 'text/html' },
        body: '<html>...</html>'
      },
      duration: 150
    },
    {
      method: 'POST',
      url: 'https://example.com/api/auth/login',
      host: 'example.com',
      path: '/api/auth/login',
      timestamp: baseTime + 4080,  // 80ms after click
      request: {
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'user@example.com',
          password: 'password123'
        })
      },
      response: {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: 'abc123', userId: 42 })
      },
      duration: 200
    },
    {
      method: 'GET',
      url: 'https://example.com/dashboard',
      host: 'example.com',
      path: '/dashboard',
      timestamp: baseTime + 6100,  // 100ms after navigate
      request: {
        headers: { 'Authorization': 'Bearer abc123' }
      },
      response: {
        status: 200,
        headers: { 'Content-Type': 'text/html' },
        body: '<html>Dashboard...</html>'
      },
      duration: 120
    },
    {
      method: 'GET',
      url: 'https://example.com/api/user/42',
      host: 'example.com',
      path: '/api/user/42',
      timestamp: baseTime + 6250,  // 250ms after dashboard load
      request: {
        headers: { 'Authorization': 'Bearer abc123' }
      },
      response: {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: 42, name: 'Test User', email: 'user@example.com' })
      },
      duration: 80
    }
  ];
}

/**
 * Test the correlator
 */
async function testCorrelator() {
  console.log('🧪 Testing Event Correlator\n');

  // Create sample data
  const uiEvents = createSampleUIEvents();
  const networkCalls = createSampleNetworkTraffic();

  console.log(`📊 Test Data:`);
  console.log(`   UI Events: ${uiEvents.length}`);
  console.log(`   Network Calls: ${networkCalls.length}\n`);

  // Test with default settings
  console.log('═══ Test 1: Default Settings (500ms window) ═══\n');
  const correlator1 = new EventCorrelator({
    windowMs: 500,
    minConfidence: 0.5,
    includeOrphans: false
  });

  const result1 = correlator1.correlate(uiEvents, networkCalls);
  correlator1.printSummary(result1);
  correlator1.printTimeline(result1);

  // Test with longer window
  console.log('\n═══ Test 2: Longer Window (1000ms) ═══\n');
  const correlator2 = new EventCorrelator({
    windowMs: 1000,
    minConfidence: 0.5,
    includeOrphans: false
  });

  const result2 = correlator2.correlate(uiEvents, networkCalls);
  correlator2.printSummary(result2);

  // Test with orphans included
  console.log('\n═══ Test 3: Include Orphans ═══\n');
  const correlator3 = new EventCorrelator({
    windowMs: 500,
    minConfidence: 0.0,
    includeOrphans: true
  });

  const result3 = correlator3.correlate(uiEvents, networkCalls);
  correlator3.printSummary(result3);

  // Validation
  console.log('\n✅ Validation:');
  console.log(`   Test 1 - Correlation rate: ${result1.stats.correlationRate >= 0.6 ? '✅' : '❌'} (${(result1.stats.correlationRate * 100).toFixed(1)}%)`);
  console.log(`   Test 1 - Average confidence: ${result1.stats.averageConfidence >= 0.6 ? '✅' : '❌'} (${(result1.stats.averageConfidence * 100).toFixed(1)}%)`);
  console.log(`   Test 2 - More correlations: ${result2.stats.correlatedNetworkCalls >= result1.stats.correlatedNetworkCalls ? '✅' : '❌'}`);
  console.log(`   Test 3 - Includes all UI events: ${result3.stats.correlatedUIEvents === uiEvents.length ? '✅' : '❌'}`);

  // Save sample output
  const samplePath = 'sample-correlated.json';
  fs.writeFileSync(samplePath, correlator1.formatResult(result1), 'utf8');
  console.log(`\n💾 Sample output saved to: ${samplePath}`);

  console.log('\n🎯 Test Complete!');
}

// Run test
if (require.main === module) {
  testCorrelator().catch(console.error);
}
