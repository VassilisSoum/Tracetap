/**
 * Trace Parser POC
 *
 * Parses Playwright trace files and extracts UI events in TraceTap format.
 *
 * Usage:
 *   npx ts-node trace-parser.ts session.zip
 *   npx ts-node trace-parser.ts session.zip --output events.json
 *
 * How it works:
 * 1. Extracts trace.zip archive
 * 2. Parses trace.json with microsecond timestamps
 * 3. Filters for relevant UI actions
 * 4. Converts to TraceTap event format
 * 5. Outputs JSON event stream
 */

import AdmZip from 'adm-zip';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Playwright trace action from trace.json
 */
interface PlaywrightTraceAction {
  type: string;
  apiName: string;
  wallTime: number;  // Unix timestamp in milliseconds
  startTime: number; // Relative time in milliseconds
  endTime?: number;
  params?: {
    selector?: string;
    url?: string;
    value?: string;
    key?: string;
    button?: string;
    files?: string[];
    [key: string]: any;
  };
  result?: any;
  error?: string;
}

/**
 * TraceTap event format
 */
interface TraceTapEvent {
  type: 'click' | 'fill' | 'navigate' | 'press' | 'select' | 'check' | 'upload' | 'hover';
  timestamp: number;      // Unix timestamp in milliseconds
  duration: number;       // Duration in milliseconds
  selector?: string;      // Element selector (if applicable)
  value?: string;         // Input value (for fill, press)
  url?: string;           // URL (for navigate)
  metadata: {
    apiName: string;      // Original Playwright API call
    params: any;          // Original parameters
    success: boolean;     // Whether action succeeded
    error?: string;       // Error message if failed
  };
}

/**
 * Parse result with statistics
 */
interface ParseResult {
  events: TraceTapEvent[];
  stats: {
    totalActions: number;
    relevantActions: number;
    duration: number;       // Total session duration in ms
    startTime: number;      // Session start timestamp
    endTime: number;        // Session end timestamp
  };
}

class TraceParser {
  /**
   * Parse trace ZIP file and extract events
   */
  async parse(tracePath: string): Promise<ParseResult> {
    console.log('📂 Opening trace file:', tracePath);

    // Extract ZIP
    const zip = new AdmZip(tracePath);
    const traceEntry = zip.getEntry('trace.trace');

    if (!traceEntry) {
      throw new Error('trace.trace not found in ZIP. This may not be a valid Playwright trace file.');
    }

    // Parse trace data
    console.log('📖 Reading trace data...');
    const traceData = JSON.parse(traceEntry.getData().toString('utf8'));

    // Extract actions
    const actions: PlaywrightTraceAction[] = traceData.actions || [];
    console.log(`📊 Found ${actions.length} total actions`);

    // Convert to TraceTap events
    const events = this.convertToTraceTapEvents(actions);
    console.log(`✅ Extracted ${events.length} relevant events`);

    // Calculate statistics
    const stats = this.calculateStats(actions, events);

    return { events, stats };
  }

  /**
   * Convert Playwright actions to TraceTap events
   */
  private convertToTraceTapEvents(actions: PlaywrightTraceAction[]): TraceTapEvent[] {
    return actions
      .filter(action => this.isRelevantAction(action))
      .map(action => this.convertAction(action))
      .filter((event): event is TraceTapEvent => event !== null);
  }

  /**
   * Check if action is relevant for test generation
   */
  private isRelevantAction(action: PlaywrightTraceAction): boolean {
    const relevantAPIs = [
      'click',
      'dblclick',
      'fill',
      'type',
      'press',
      'selectOption',
      'check',
      'uncheck',
      'setInputFiles',
      'hover',
      'goto',
      'goBack',
      'goForward'
    ];

    return relevantAPIs.some(api => action.apiName?.includes(api));
  }

  /**
   * Convert single Playwright action to TraceTap event
   */
  private convertAction(action: PlaywrightTraceAction): TraceTapEvent | null {
    try {
      const baseEvent = {
        timestamp: action.wallTime,
        duration: action.endTime ? action.endTime - action.startTime : 0,
        metadata: {
          apiName: action.apiName,
          params: action.params || {},
          success: !action.error,
          error: action.error
        }
      };

      // Map Playwright API to TraceTap event type
      if (action.apiName.includes('click')) {
        return {
          ...baseEvent,
          type: 'click',
          selector: action.params?.selector
        } as TraceTapEvent;
      }

      if (action.apiName.includes('fill') || action.apiName.includes('type')) {
        return {
          ...baseEvent,
          type: 'fill',
          selector: action.params?.selector,
          value: action.params?.value || action.params?.text
        } as TraceTapEvent;
      }

      if (action.apiName.includes('press')) {
        return {
          ...baseEvent,
          type: 'press',
          selector: action.params?.selector,
          value: action.params?.key
        } as TraceTapEvent;
      }

      if (action.apiName.includes('selectOption')) {
        return {
          ...baseEvent,
          type: 'select',
          selector: action.params?.selector,
          value: JSON.stringify(action.params?.values || action.params?.value)
        } as TraceTapEvent;
      }

      if (action.apiName.includes('check') || action.apiName.includes('uncheck')) {
        return {
          ...baseEvent,
          type: 'check',
          selector: action.params?.selector
        } as TraceTapEvent;
      }

      if (action.apiName.includes('setInputFiles')) {
        return {
          ...baseEvent,
          type: 'upload',
          selector: action.params?.selector,
          value: JSON.stringify(action.params?.files)
        } as TraceTapEvent;
      }

      if (action.apiName.includes('hover')) {
        return {
          ...baseEvent,
          type: 'hover',
          selector: action.params?.selector
        } as TraceTapEvent;
      }

      if (action.apiName.includes('goto')) {
        return {
          ...baseEvent,
          type: 'navigate',
          url: action.params?.url
        } as TraceTapEvent;
      }

      return null;
    } catch (error) {
      console.warn(`⚠️  Failed to convert action: ${action.apiName}`, error);
      return null;
    }
  }

  /**
   * Calculate session statistics
   */
  private calculateStats(
    actions: PlaywrightTraceAction[],
    events: TraceTapEvent[]
  ): ParseResult['stats'] {
    if (actions.length === 0) {
      return {
        totalActions: 0,
        relevantActions: 0,
        duration: 0,
        startTime: 0,
        endTime: 0
      };
    }

    const startTime = Math.min(...actions.map(a => a.wallTime));
    const endTime = Math.max(...actions.map(a => a.wallTime));

    return {
      totalActions: actions.length,
      relevantActions: events.length,
      duration: endTime - startTime,
      startTime,
      endTime
    };
  }

  /**
   * Format events as pretty JSON
   */
  formatEvents(result: ParseResult): string {
    return JSON.stringify(result, null, 2);
  }

  /**
   * Print summary statistics
   */
  printSummary(result: ParseResult): void {
    console.log('\n📊 Session Statistics:');
    console.log(`   Total Actions: ${result.stats.totalActions}`);
    console.log(`   Relevant Events: ${result.stats.relevantActions}`);
    console.log(`   Session Duration: ${(result.stats.duration / 1000).toFixed(1)}s`);
    console.log(`   Start Time: ${new Date(result.stats.startTime).toISOString()}`);
    console.log(`   End Time: ${new Date(result.stats.endTime).toISOString()}`);

    console.log('\n📝 Event Breakdown:');
    const eventTypes = result.events.reduce((acc, event) => {
      acc[event.type] = (acc[event.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    Object.entries(eventTypes)
      .sort(([, a], [, b]) => b - a)
      .forEach(([type, count]) => {
        console.log(`   ${type}: ${count}`);
      });
  }

  /**
   * Print event timeline
   */
  printTimeline(result: ParseResult, limit: number = 10): void {
    console.log(`\n⏱️  Event Timeline (first ${limit}):`);

    result.events.slice(0, limit).forEach((event, index) => {
      const time = new Date(event.timestamp).toISOString().substr(11, 12);
      const selector = event.selector ? ` ${event.selector}` : '';
      const value = event.value ? ` = "${event.value}"` : '';
      const url = event.url ? ` → ${event.url}` : '';

      console.log(`   ${index + 1}. [${time}] ${event.type}${selector}${value}${url}`);
    });

    if (result.events.length > limit) {
      console.log(`   ... and ${result.events.length - limit} more events`);
    }
  }
}

/**
 * CLI Entry Point
 */
async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.log('Usage: npx ts-node trace-parser.ts <trace-file.zip> [options]');
    console.log('');
    console.log('Options:');
    console.log('  --output <file>   Save events to JSON file');
    console.log('  --timeline        Show detailed event timeline');
    console.log('');
    console.log('Example:');
    console.log('  npx ts-node trace-parser.ts session.zip');
    console.log('  npx ts-node trace-parser.ts session.zip --output events.json');
    console.log('  npx ts-node trace-parser.ts session.zip --timeline');
    process.exit(1);
  }

  const tracePath = args[0];
  const outputPath = args.includes('--output')
    ? args[args.indexOf('--output') + 1]
    : null;
  const showTimeline = args.includes('--timeline');

  // Validate input file
  if (!fs.existsSync(tracePath)) {
    console.error(`❌ Error: File not found: ${tracePath}`);
    process.exit(1);
  }

  // Parse trace
  const parser = new TraceParser();
  const result = await parser.parse(tracePath);

  // Print summary
  parser.printSummary(result);

  // Print timeline if requested
  if (showTimeline) {
    parser.printTimeline(result, 20);
  }

  // Save to file if requested
  if (outputPath) {
    const json = parser.formatEvents(result);
    fs.writeFileSync(outputPath, json, 'utf8');
    console.log(`\n💾 Events saved to: ${outputPath}`);
  }

  // Print sample event
  if (result.events.length > 0) {
    console.log('\n📋 Sample Event:');
    console.log(JSON.stringify(result.events[0], null, 2));
  }

  console.log('\n✅ Parsing complete!');
  console.log('\n📊 Next steps:');
  console.log('1. Correlate with network traffic:');
  console.log(`   npx ts-node event-correlator.ts ${outputPath || 'events.json'} traffic.json`);
  console.log('2. View original trace:');
  console.log(`   npx playwright show-trace ${tracePath}`);
}

// Run CLI
if (require.main === module) {
  main().catch(console.error);
}

export { TraceParser, TraceTapEvent, ParseResult };
