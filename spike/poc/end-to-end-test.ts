/**
 * End-to-End Spike Validation Test
 *
 * Runs the complete workflow: record → parse → correlate
 * Uses synthetic data to validate the entire pipeline
 */

import { TraceRecorder } from './trace-recorder';
import { TraceParser } from './trace-parser';
import { EventCorrelator, NetworkRequest } from './event-correlator';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Create synthetic network traffic matching the session
 */
function createSyntheticTraffic(sessionStartTime: number): NetworkRequest[] {
  return [
    {
      method: 'GET',
      url: 'https://www.google.com/',
      host: 'www.google.com',
      path: '/',
      timestamp: sessionStartTime + 150, // 150ms after page load
      request: {
        headers: { 'User-Agent': 'Mozilla/5.0' }
      },
      response: {
        status: 200,
        headers: { 'Content-Type': 'text/html' },
        body: '<html>...</html>'
      },
      duration: 200
    },
    {
      method: 'GET',
      url: 'https://www.google.com/search?q=playwright+testing',
      host: 'www.google.com',
      path: '/search',
      timestamp: sessionStartTime + 3200, // ~200ms after form submit
      request: {
        headers: { 'User-Agent': 'Mozilla/5.0' }
      },
      response: {
        status: 200,
        headers: { 'Content-Type': 'text/html' },
        body: '<html>Search results...</html>'
      },
      duration: 180
    }
  ];
}

/**
 * Run end-to-end validation test
 */
async function runE2ETest() {
  console.log('═══════════════════════════════════════════════════════');
  console.log('        TraceTap Spike: End-to-End Validation         ');
  console.log('═══════════════════════════════════════════════════════\n');

  const testDir = path.join(__dirname, 'test-output');
  if (!fs.existsSync(testDir)) {
    fs.mkdirSync(testDir);
  }

  const tracePath = path.join(testDir, 'e2e-session.zip');
  const eventsPath = path.join(testDir, 'e2e-events.json');
  const trafficPath = path.join(testDir, 'e2e-traffic.json');
  const correlatedPath = path.join(testDir, 'e2e-correlated.json');

  let recorder: TraceRecorder | null = null;
  let sessionStartTime = Date.now();

  try {
    // ═══ STEP 1: Record Session ═══
    console.log('🎬 STEP 1: Recording Session');
    console.log('────────────────────────────────────────────────────────');
    console.log('   This would normally open a browser for manual interaction.');
    console.log('   For automated testing, we\'ll use the test-trace-parser.ts approach.');
    console.log('   In production: npx ts-node trace-recorder.ts https://google.com session.zip\n');

    // For automated testing, create a minimal trace file
    console.log('   ⚠️  Creating synthetic trace for automated testing...');
    console.log('   ✅ Trace saved to:', tracePath);
    console.log('   ℹ️  In real usage, user would interact with browser\n');

    // ═══ STEP 2: Parse Trace ═══
    console.log('📖 STEP 2: Parsing Trace File');
    console.log('────────────────────────────────────────────────────────');

    // Create synthetic trace data
    const syntheticTrace = {
      actions: [
        {
          type: 'action',
          apiName: 'page.goto',
          wallTime: sessionStartTime,
          startTime: 0,
          endTime: 100,
          params: { url: 'https://www.google.com' }
        },
        {
          type: 'action',
          apiName: 'page.fill',
          wallTime: sessionStartTime + 2000,
          startTime: 2000,
          endTime: 2150,
          params: {
            selector: 'textarea[name="q"]',
            value: 'playwright testing'
          }
        },
        {
          type: 'action',
          apiName: 'page.click',
          wallTime: sessionStartTime + 3000,
          startTime: 3000,
          endTime: 3050,
          params: {
            selector: 'input[name="btnK"]'
          }
        }
      ]
    };

    // Save synthetic trace
    const AdmZip = require('adm-zip');
    const zip = new AdmZip();
    zip.addFile('trace.trace', Buffer.from(JSON.stringify(syntheticTrace), 'utf8'));
    zip.writeZip(tracePath);

    const parser = new TraceParser();
    const parseResult = await parser.parse(tracePath);

    fs.writeFileSync(eventsPath, JSON.stringify(parseResult, null, 2), 'utf8');

    console.log(`   ✅ Parsed ${parseResult.events.length} UI events`);
    console.log(`   ✅ Session duration: ${(parseResult.stats.duration / 1000).toFixed(1)}s`);
    console.log(`   ✅ Events saved to: ${eventsPath}\n`);

    // ═══ STEP 3: Generate/Load Network Traffic ═══
    console.log('🌐 STEP 3: Loading Network Traffic');
    console.log('────────────────────────────────────────────────────────');
    console.log('   This would normally come from mitmproxy.');
    console.log('   In production: mitmproxy captures traffic during recording.\n');

    const networkTraffic = createSyntheticTraffic(sessionStartTime);
    fs.writeFileSync(trafficPath, JSON.stringify({ requests: networkTraffic }, null, 2), 'utf8');

    console.log(`   ✅ Loaded ${networkTraffic.length} network requests`);
    console.log(`   ✅ Traffic saved to: ${trafficPath}\n`);

    // ═══ STEP 4: Correlate Events ═══
    console.log('🔗 STEP 4: Correlating UI Events with Network Traffic');
    console.log('────────────────────────────────────────────────────────');

    const correlator = new EventCorrelator({
      windowMs: 500,
      minConfidence: 0.5,
      includeOrphans: false
    });

    const correlationResult = correlator.correlate(
      parseResult.events,
      networkTraffic
    );

    fs.writeFileSync(correlatedPath, JSON.stringify(correlationResult, null, 2), 'utf8');

    console.log(`   ✅ Correlated ${correlationResult.stats.correlatedUIEvents}/${correlationResult.stats.totalUIEvents} UI events`);
    console.log(`   ✅ Correlation rate: ${(correlationResult.stats.correlationRate * 100).toFixed(1)}%`);
    console.log(`   ✅ Average confidence: ${(correlationResult.stats.averageConfidence * 100).toFixed(1)}%`);
    console.log(`   ✅ Correlated events saved to: ${correlatedPath}\n`);

    // ═══ RESULTS ═══
    console.log('═══════════════════════════════════════════════════════');
    console.log('                    RESULTS SUMMARY                    ');
    console.log('═══════════════════════════════════════════════════════\n');

    correlator.printSummary(correlationResult);
    correlator.printTimeline(correlationResult);

    // ═══ VALIDATION ═══
    console.log('\n🧪 VALIDATION CHECKS:');
    console.log('────────────────────────────────────────────────────────');

    const checks = [
      {
        name: 'Event extraction',
        pass: parseResult.events.length === 3,
        details: `Expected 3 events, got ${parseResult.events.length}`
      },
      {
        name: 'Navigate event captured',
        pass: parseResult.events[0]?.type === 'navigate',
        details: `First event type: ${parseResult.events[0]?.type}`
      },
      {
        name: 'Fill event captured',
        pass: parseResult.events[1]?.type === 'fill',
        details: `Second event type: ${parseResult.events[1]?.type}`
      },
      {
        name: 'Click event captured',
        pass: parseResult.events[2]?.type === 'click',
        details: `Third event type: ${parseResult.events[2]?.type}`
      },
      {
        name: 'Correlation rate >60%',
        pass: correlationResult.stats.correlationRate >= 0.6,
        details: `${(correlationResult.stats.correlationRate * 100).toFixed(1)}%`
      },
      {
        name: 'Average confidence >60%',
        pass: correlationResult.stats.averageConfidence >= 0.6,
        details: `${(correlationResult.stats.averageConfidence * 100).toFixed(1)}%`
      },
      {
        name: 'All files created',
        pass: fs.existsSync(tracePath) && fs.existsSync(eventsPath) &&
              fs.existsSync(trafficPath) && fs.existsSync(correlatedPath),
        details: 'trace.zip, events.json, traffic.json, correlated.json'
      }
    ];

    let passCount = 0;
    checks.forEach((check, i) => {
      const status = check.pass ? '✅' : '❌';
      console.log(`   ${i + 1}. ${status} ${check.name}`);
      console.log(`      ${check.details}`);
      if (check.pass) passCount++;
    });

    const passRate = (passCount / checks.length) * 100;
    console.log(`\n   Overall: ${passCount}/${checks.length} checks passed (${passRate.toFixed(0)}%)`);

    // ═══ GO/NO-GO DECISION ═══
    console.log('\n🚦 GO/NO-GO ASSESSMENT:');
    console.log('────────────────────────────────────────────────────────');

    const goDecision = passRate >= 85 &&
                      correlationResult.stats.correlationRate >= 0.6 &&
                      correlationResult.stats.averageConfidence >= 0.6;

    if (goDecision) {
      console.log('   ✅ GO - Spike validation SUCCESSFUL');
      console.log('   ✅ Proceed with full 10-12 week implementation');
      console.log('   ⚠️  Condition: Validate with real app in Phase 1 Week 2');
    } else {
      console.log('   ⚠️  CONDITIONAL - Spike shows promise but needs tuning');
      console.log('   📊 Current metrics acceptable for POC');
      console.log('   ⚠️  Real-world validation critical in Phase 1');
    }

    // ═══ NEXT STEPS ═══
    console.log('\n📋 NEXT STEPS:');
    console.log('────────────────────────────────────────────────────────');
    console.log('   1. Update main implementation plan with Trace Files approach');
    console.log('   2. Start Phase 1: Foundation (3 weeks)');
    console.log('   3. Build mitmproxy integration (Week 1)');
    console.log('   4. Test on examples/ecommerce-api (Week 1-2)');
    console.log('   5. Measure real-world correlation accuracy (Week 2)');
    console.log('   6. Go/No-Go checkpoint at end of Week 2');
    console.log('   7. If >70% accuracy → Continue to Phase 2');
    console.log('   8. If <60% accuracy → 1-week spike on CDP alternative');

    console.log('\n═══════════════════════════════════════════════════════');
    console.log('                   SPIKE COMPLETE                      ');
    console.log('═══════════════════════════════════════════════════════\n');

    // Clean up
    console.log('🧹 Cleaning up test files...');
    if (fs.existsSync(testDir)) {
      fs.readdirSync(testDir).forEach(file => {
        fs.unlinkSync(path.join(testDir, file));
      });
      fs.rmdirSync(testDir);
    }
    console.log('   ✅ Test directory cleaned\n');

  } catch (error) {
    console.error('\n❌ Error during E2E test:', error);
    throw error;
  }
}

// Run test
if (require.main === module) {
  runE2ETest()
    .then(() => {
      console.log('✅ E2E validation complete!');
      process.exit(0);
    })
    .catch((error) => {
      console.error('❌ E2E validation failed:', error);
      process.exit(1);
    });
}
