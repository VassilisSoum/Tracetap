/**
 * Event Correlator POC
 *
 * Correlates UI events from Playwright traces with network traffic from mitmproxy.
 *
 * Usage:
 *   npx ts-node event-correlator.ts ui-events.json traffic.json
 *   npx ts-node event-correlator.ts ui-events.json traffic.json --output correlated.json
 *   npx ts-node event-correlator.ts ui-events.json traffic.json --window 1000
 *
 * How it works:
 * 1. Loads UI events from trace parser
 * 2. Loads network traffic from mitmproxy
 * 3. Correlates by timestamp (default ±500ms window)
 * 4. Builds interaction graph (UI event → API calls)
 * 5. Calculates correlation confidence scores
 * 6. Outputs correlated events for test generation
 */

import * as fs from 'fs';
import { TraceTapEvent, ParseResult } from './trace-parser';

/**
 * Network request from mitmproxy
 */
interface NetworkRequest {
  method: string;
  url: string;
  host: string;
  path: string;
  timestamp: number;  // Unix timestamp in milliseconds
  request: {
    headers: Record<string, string>;
    body?: string;
  };
  response?: {
    status: number;
    headers: Record<string, string>;
    body?: string;
  };
  duration?: number;
}

/**
 * Correlated event combining UI action and network calls
 */
interface CorrelatedEvent {
  sequence: number;
  uiEvent: TraceTapEvent;
  networkCalls: NetworkRequest[];
  correlation: {
    confidence: number;      // 0.0 to 1.0
    timeDelta: number;       // Average ms between UI event and network calls
    method: 'exact' | 'window' | 'inference';
    reasoning: string;
  };
}

/**
 * Correlation result with statistics
 */
interface CorrelationResult {
  correlatedEvents: CorrelatedEvent[];
  stats: {
    totalUIEvents: number;
    totalNetworkCalls: number;
    correlatedUIEvents: number;
    correlatedNetworkCalls: number;
    averageConfidence: number;
    averageTimeDelta: number;
    correlationRate: number;  // Percentage of UI events successfully correlated
  };
}

/**
 * Correlation options
 */
interface CorrelationOptions {
  windowMs: number;          // Time window for correlation (default 500ms)
  minConfidence: number;     // Minimum confidence threshold (default 0.5)
  includeOrphans: boolean;   // Include UI events with no network calls (default false)
}

class EventCorrelator {
  private options: CorrelationOptions;

  constructor(options: Partial<CorrelationOptions> = {}) {
    this.options = {
      windowMs: 500,
      minConfidence: 0.5,
      includeOrphans: false,
      ...options
    };
  }

  /**
   * Correlate UI events with network traffic
   */
  correlate(
    uiEvents: TraceTapEvent[],
    networkCalls: NetworkRequest[]
  ): CorrelationResult {
    console.log('🔗 Starting correlation...');
    console.log(`   UI Events: ${uiEvents.length}`);
    console.log(`   Network Calls: ${networkCalls.length}`);
    console.log(`   Time Window: ±${this.options.windowMs}ms`);

    const correlatedEvents: CorrelatedEvent[] = [];
    const usedNetworkCalls = new Set<number>();

    // Sort events by timestamp
    const sortedUIEvents = [...uiEvents].sort((a, b) => a.timestamp - b.timestamp);
    const sortedNetworkCalls = [...networkCalls].sort((a, b) => a.timestamp - b.timestamp);

    // Correlate each UI event with network calls
    for (let i = 0; i < sortedUIEvents.length; i++) {
      const uiEvent = sortedUIEvents[i];

      // Find network calls within time window
      const relatedCalls = this.findRelatedNetworkCalls(
        uiEvent,
        sortedNetworkCalls,
        usedNetworkCalls
      );

      // Calculate correlation confidence
      const correlation = this.calculateCorrelation(uiEvent, relatedCalls);

      // Only include if confidence meets threshold (or if including orphans)
      if (correlation.confidence >= this.options.minConfidence ||
          (this.options.includeOrphans && relatedCalls.length === 0)) {

        correlatedEvents.push({
          sequence: i + 1,
          uiEvent,
          networkCalls: relatedCalls,
          correlation
        });

        // Mark network calls as used
        relatedCalls.forEach((_, idx) => {
          const originalIndex = sortedNetworkCalls.findIndex(
            nc => nc.timestamp === relatedCalls[idx].timestamp &&
                  nc.url === relatedCalls[idx].url
          );
          if (originalIndex >= 0) {
            usedNetworkCalls.add(originalIndex);
          }
        });
      }
    }

    // Calculate statistics
    const stats = this.calculateStats(
      uiEvents,
      networkCalls,
      correlatedEvents,
      usedNetworkCalls
    );

    console.log('✅ Correlation complete!');
    console.log(`   Correlated Events: ${correlatedEvents.length}`);
    console.log(`   Correlation Rate: ${(stats.correlationRate * 100).toFixed(1)}%`);
    console.log(`   Average Confidence: ${(stats.averageConfidence * 100).toFixed(1)}%`);

    return { correlatedEvents, stats };
  }

  /**
   * Find network calls related to a UI event
   */
  private findRelatedNetworkCalls(
    uiEvent: TraceTapEvent,
    allNetworkCalls: NetworkRequest[],
    usedCalls: Set<number>
  ): NetworkRequest[] {
    const relatedCalls: NetworkRequest[] = [];
    const uiTimestamp = uiEvent.timestamp;

    // Search for network calls within the time window
    for (let i = 0; i < allNetworkCalls.length; i++) {
      if (usedCalls.has(i)) continue; // Skip already correlated calls

      const networkCall = allNetworkCalls[i];
      const timeDelta = networkCall.timestamp - uiTimestamp;

      // Network call must happen AFTER UI event (within window)
      if (timeDelta >= 0 && timeDelta <= this.options.windowMs) {
        relatedCalls.push(networkCall);
      }

      // Stop searching if we're past the window
      if (timeDelta > this.options.windowMs) {
        break;
      }
    }

    return relatedCalls;
  }

  /**
   * Calculate correlation confidence and metadata
   */
  private calculateCorrelation(
    uiEvent: TraceTapEvent,
    networkCalls: NetworkRequest[]
  ): CorrelatedEvent['correlation'] {
    if (networkCalls.length === 0) {
      return {
        confidence: 0.0,
        timeDelta: 0,
        method: 'inference',
        reasoning: 'No network calls within time window'
      };
    }

    // Calculate average time delta
    const timeDeltas = networkCalls.map(
      nc => nc.timestamp - uiEvent.timestamp
    );
    const avgTimeDelta = timeDeltas.reduce((a, b) => a + b, 0) / timeDeltas.length;

    // Base confidence on timing and event type
    let confidence = 0.5; // Base confidence

    // Boost confidence for shorter time deltas
    if (avgTimeDelta < 100) confidence += 0.3;
    else if (avgTimeDelta < 250) confidence += 0.2;
    else if (avgTimeDelta < 500) confidence += 0.1;

    // Boost confidence for specific event types
    if (uiEvent.type === 'click' || uiEvent.type === 'navigate') {
      confidence += 0.1; // Clicks/navigation often trigger API calls
    }

    // Boost confidence if there's exactly one network call (clear correlation)
    if (networkCalls.length === 1) {
      confidence += 0.1;
    }

    // Boost confidence for POST/PUT/DELETE (mutations)
    const hasMutation = networkCalls.some(
      nc => ['POST', 'PUT', 'DELETE', 'PATCH'].includes(nc.method)
    );
    if (hasMutation && uiEvent.type === 'click') {
      confidence += 0.1;
    }

    // Cap confidence at 1.0
    confidence = Math.min(confidence, 1.0);

    // Determine correlation method
    let method: 'exact' | 'window' | 'inference' = 'window';
    if (avgTimeDelta < 50) method = 'exact';

    // Generate reasoning
    const reasoning = this.generateReasoning(uiEvent, networkCalls, avgTimeDelta);

    return {
      confidence,
      timeDelta: avgTimeDelta,
      method,
      reasoning
    };
  }

  /**
   * Generate human-readable reasoning for correlation
   */
  private generateReasoning(
    uiEvent: TraceTapEvent,
    networkCalls: NetworkRequest[],
    avgTimeDelta: number
  ): string {
    if (networkCalls.length === 0) {
      return 'No network activity';
    }

    const methods = networkCalls.map(nc => nc.method).join(', ');
    const urls = networkCalls.map(nc => new URL(nc.url).pathname).join(', ');

    return `${uiEvent.type} triggered ${networkCalls.length} call(s) [${methods}] to ${urls} after ${avgTimeDelta.toFixed(0)}ms`;
  }

  /**
   * Calculate correlation statistics
   */
  private calculateStats(
    allUIEvents: TraceTapEvent[],
    allNetworkCalls: NetworkRequest[],
    correlatedEvents: CorrelatedEvent[],
    usedNetworkCalls: Set<number>
  ): CorrelationResult['stats'] {
    const totalUIEvents = allUIEvents.length;
    const totalNetworkCalls = allNetworkCalls.length;
    const correlatedUIEvents = correlatedEvents.length;
    const correlatedNetworkCalls = usedNetworkCalls.size;

    const averageConfidence = correlatedEvents.length > 0
      ? correlatedEvents.reduce((sum, e) => sum + e.correlation.confidence, 0) / correlatedEvents.length
      : 0;

    const averageTimeDelta = correlatedEvents.length > 0
      ? correlatedEvents.reduce((sum, e) => sum + e.correlation.timeDelta, 0) / correlatedEvents.length
      : 0;

    const correlationRate = totalUIEvents > 0
      ? correlatedUIEvents / totalUIEvents
      : 0;

    return {
      totalUIEvents,
      totalNetworkCalls,
      correlatedUIEvents,
      correlatedNetworkCalls,
      averageConfidence,
      averageTimeDelta,
      correlationRate
    };
  }

  /**
   * Print correlation summary
   */
  printSummary(result: CorrelationResult): void {
    console.log('\n📊 Correlation Statistics:');
    console.log(`   Total UI Events: ${result.stats.totalUIEvents}`);
    console.log(`   Total Network Calls: ${result.stats.totalNetworkCalls}`);
    console.log(`   Correlated UI Events: ${result.stats.correlatedUIEvents}`);
    console.log(`   Correlated Network Calls: ${result.stats.correlatedNetworkCalls}`);
    console.log(`   Correlation Rate: ${(result.stats.correlationRate * 100).toFixed(1)}%`);
    console.log(`   Average Confidence: ${(result.stats.averageConfidence * 100).toFixed(1)}%`);
    console.log(`   Average Time Delta: ${result.stats.averageTimeDelta.toFixed(1)}ms`);

    // Quality assessment
    console.log('\n🎯 Quality Assessment:');
    const rate = result.stats.correlationRate;
    const confidence = result.stats.averageConfidence;

    if (rate >= 0.8 && confidence >= 0.7) {
      console.log('   ✅ EXCELLENT - High correlation with strong confidence');
    } else if (rate >= 0.6 && confidence >= 0.6) {
      console.log('   ✅ GOOD - Acceptable correlation quality');
    } else if (rate >= 0.4 || confidence >= 0.5) {
      console.log('   ⚠️  MODERATE - May need tuning or longer time windows');
    } else {
      console.log('   ❌ POOR - Correlation quality insufficient');
    }
  }

  /**
   * Print correlation timeline
   */
  printTimeline(result: CorrelationResult, limit: number = 10): void {
    console.log(`\n⏱️  Correlation Timeline (first ${limit}):`);

    result.correlatedEvents.slice(0, limit).forEach((event) => {
      const time = new Date(event.uiEvent.timestamp).toISOString().substr(11, 12);
      const uiType = event.uiEvent.type.padEnd(8);
      const selector = event.uiEvent.selector || event.uiEvent.url || '';
      const networkCount = event.networkCalls.length;
      const confidence = (event.correlation.confidence * 100).toFixed(0);

      console.log(`   ${event.sequence}. [${time}] ${uiType} ${selector}`);
      console.log(`      └─ ${networkCount} call(s), ${confidence}% confidence, +${event.correlation.timeDelta.toFixed(0)}ms`);

      event.networkCalls.forEach((nc, i) => {
        const url = new URL(nc.url).pathname;
        console.log(`         ${i + 1}. ${nc.method} ${url} (${nc.response?.status || '?'})`);
      });
    });

    if (result.correlatedEvents.length > limit) {
      console.log(`   ... and ${result.correlatedEvents.length - limit} more events`);
    }
  }

  /**
   * Format result as JSON
   */
  formatResult(result: CorrelationResult): string {
    return JSON.stringify(result, null, 2);
  }
}

/**
 * Load mitmproxy traffic from JSON
 */
function loadMitmproxyTraffic(filePath: string): NetworkRequest[] {
  console.log('📂 Loading mitmproxy traffic:', filePath);

  const content = fs.readFileSync(filePath, 'utf8');
  const data = JSON.parse(content);

  // Assume mitmproxy exports in TraceTap raw log format
  // Adapt this based on actual mitmproxy export format
  const requests: NetworkRequest[] = (data.requests || data).map((req: any) => ({
    method: req.method,
    url: req.url,
    host: req.host || new URL(req.url).host,
    path: req.path || new URL(req.url).pathname,
    timestamp: req.timestamp || Date.parse(req.start_time),
    request: {
      headers: req.request?.headers || req.headers || {},
      body: req.request?.body || req.body
    },
    response: req.response ? {
      status: req.response.status || req.status,
      headers: req.response.headers || {},
      body: req.response.body
    } : undefined,
    duration: req.duration || req.response_time
  }));

  console.log(`✅ Loaded ${requests.length} network requests`);
  return requests;
}

/**
 * CLI Entry Point
 */
async function main() {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.log('Usage: npx ts-node event-correlator.ts <ui-events.json> <traffic.json> [options]');
    console.log('');
    console.log('Options:');
    console.log('  --output <file>    Save correlated events to JSON file');
    console.log('  --window <ms>      Time window for correlation (default: 500)');
    console.log('  --timeline         Show detailed correlation timeline');
    console.log('  --include-orphans  Include UI events with no network calls');
    console.log('');
    console.log('Example:');
    console.log('  npx ts-node event-correlator.ts events.json traffic.json');
    console.log('  npx ts-node event-correlator.ts events.json traffic.json --output correlated.json');
    console.log('  npx ts-node event-correlator.ts events.json traffic.json --window 1000 --timeline');
    process.exit(1);
  }

  const uiEventsPath = args[0];
  const trafficPath = args[1];
  const outputPath = args.includes('--output')
    ? args[args.indexOf('--output') + 1]
    : null;
  const windowMs = args.includes('--window')
    ? parseInt(args[args.indexOf('--window') + 1])
    : 500;
  const showTimeline = args.includes('--timeline');
  const includeOrphans = args.includes('--include-orphans');

  // Validate input files
  if (!fs.existsSync(uiEventsPath)) {
    console.error(`❌ Error: UI events file not found: ${uiEventsPath}`);
    process.exit(1);
  }
  if (!fs.existsSync(trafficPath)) {
    console.error(`❌ Error: Traffic file not found: ${trafficPath}`);
    process.exit(1);
  }

  // Load UI events
  console.log('📂 Loading UI events:', uiEventsPath);
  const uiEventsData: ParseResult = JSON.parse(fs.readFileSync(uiEventsPath, 'utf8'));
  const uiEvents = uiEventsData.events;
  console.log(`✅ Loaded ${uiEvents.length} UI events`);

  // Load network traffic
  const networkCalls = loadMitmproxyTraffic(trafficPath);

  // Correlate
  const correlator = new EventCorrelator({
    windowMs,
    minConfidence: 0.5,
    includeOrphans
  });

  const result = correlator.correlate(uiEvents, networkCalls);

  // Print summary
  correlator.printSummary(result);

  // Print timeline if requested
  if (showTimeline) {
    correlator.printTimeline(result, 15);
  }

  // Save to file if requested
  if (outputPath) {
    const json = correlator.formatResult(result);
    fs.writeFileSync(outputPath, json, 'utf8');
    console.log(`\n💾 Correlated events saved to: ${outputPath}`);
  }

  // Print sample correlated event
  if (result.correlatedEvents.length > 0) {
    console.log('\n📋 Sample Correlated Event:');
    console.log(JSON.stringify(result.correlatedEvents[0], null, 2));
  }

  console.log('\n✅ Correlation complete!');

  // Go/No-Go assessment
  console.log('\n🚦 Spike Validation:');
  const passThreshold = result.stats.correlationRate >= 0.8 && result.stats.averageConfidence >= 0.7;
  if (passThreshold) {
    console.log('   ✅ GO - Correlation quality meets requirements (>80% rate, >70% confidence)');
    console.log('   ✅ Proceed with full 12-week implementation');
  } else {
    console.log('   ⚠️  CONDITIONAL - Quality below target, but may be acceptable');
    console.log(`   Current: ${(result.stats.correlationRate * 100).toFixed(1)}% rate, ${(result.stats.averageConfidence * 100).toFixed(1)}% confidence`);
    console.log('   Consider: Tuning time windows, improving heuristics, or alternative approaches');
  }
}

// Run CLI
if (require.main === module) {
  main().catch(console.error);
}

export { EventCorrelator, CorrelatedEvent, CorrelationResult, NetworkRequest };
