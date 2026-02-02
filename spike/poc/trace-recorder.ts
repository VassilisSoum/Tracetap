/**
 * Trace Recorder POC
 *
 * Records user interactions in a Playwright browser session using trace files.
 *
 * Usage:
 *   npx ts-node trace-recorder.ts https://example.com output-trace.zip
 *
 * How it works:
 * 1. Launches Playwright browser with tracing enabled
 * 2. Navigates to target URL
 * 3. Lets user interact manually
 * 4. Stops tracing when user presses Enter
 * 5. Saves trace.zip with microsecond-precision timestamps
 */

import { chromium, BrowserContext, Page } from 'playwright';
import * as readline from 'readline';

interface RecorderOptions {
  headless: boolean;
  screenshots: boolean;
  snapshots: boolean;
  sources: boolean;
}

class TraceRecorder {
  private browser: any;
  private context: BrowserContext | null = null;
  private page: Page | null = null;
  private options: RecorderOptions;

  constructor(options: Partial<RecorderOptions> = {}) {
    this.options = {
      headless: false,  // Visual browser for manual interaction
      screenshots: true,
      snapshots: true,
      sources: true,
      ...options
    };
  }

  /**
   * Start recording session
   */
  async startRecording(url: string): Promise<void> {
    console.log('🎬 Starting trace recorder...');
    console.log(`   URL: ${url}`);
    console.log(`   Headless: ${this.options.headless}`);

    // Launch browser
    console.log('\n📱 Launching browser...');
    this.browser = await chromium.launch({
      headless: this.options.headless,
      slowMo: 0  // No artificial slowdown
    });

    // Create context
    this.context = await this.browser.newContext({
      viewport: { width: 1280, height: 720 },
      // Set up proxy for mitmproxy integration (future)
      // proxy: { server: 'http://localhost:8080' }
    });

    // Start tracing BEFORE opening page
    console.log('🔴 Starting trace capture...');
    await this.context.tracing.start({
      screenshots: this.options.screenshots,
      snapshots: this.options.snapshots,
      sources: this.options.sources
    });

    // Open page
    this.page = await this.context.newPage();

    console.log(`🌐 Navigating to ${url}...`);
    await this.page.goto(url);

    console.log('\n✅ Recording started!');
    console.log('👉 Interact with the browser manually.');
    console.log('👉 Press ENTER when you\'re done to stop recording.\n');
  }

  /**
   * Wait for user to complete interactions
   */
  async waitForUserCompletion(): Promise<void> {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    return new Promise((resolve) => {
      rl.question('Press ENTER to stop recording... ', () => {
        rl.close();
        resolve();
      });
    });
  }

  /**
   * Stop recording and save trace
   */
  async stopRecording(outputPath: string): Promise<void> {
    if (!this.context) {
      throw new Error('Recording not started');
    }

    console.log('\n⏹️  Stopping trace capture...');

    // Stop tracing and save
    await this.context.tracing.stop({ path: outputPath });

    console.log(`💾 Trace saved to: ${outputPath}`);

    // Close browser
    await this.browser.close();

    console.log('✅ Recording complete!');
  }

  /**
   * Complete recording workflow
   */
  async record(url: string, outputPath: string): Promise<void> {
    try {
      await this.startRecording(url);
      await this.waitForUserCompletion();
      await this.stopRecording(outputPath);
    } catch (error) {
      console.error('❌ Recording failed:', error);
      if (this.browser) {
        await this.browser.close();
      }
      throw error;
    }
  }
}

/**
 * CLI Entry Point
 */
async function main() {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.log('Usage: npx ts-node trace-recorder.ts <url> <output-path>');
    console.log('');
    console.log('Example:');
    console.log('  npx ts-node trace-recorder.ts https://example.com session.zip');
    process.exit(1);
  }

  const [url, outputPath] = args;

  const recorder = new TraceRecorder({
    headless: false,
    screenshots: true,
    snapshots: true,
    sources: true
  });

  await recorder.record(url, outputPath);

  console.log('\n📊 Next steps:');
  console.log('1. View trace visually:');
  console.log(`   npx playwright show-trace ${outputPath}`);
  console.log('2. Parse trace events:');
  console.log(`   npx ts-node trace-parser.ts ${outputPath}`);
}

// Run CLI
if (require.main === module) {
  main().catch(console.error);
}

export { TraceRecorder, RecorderOptions };
