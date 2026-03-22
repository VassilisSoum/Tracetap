#!/usr/bin/env node

/**
 * TraceTap npm wrapper - proxies commands to Python CLI
 *
 * This wrapper allows Node.js/JavaScript teams to use TraceTap
 * without worrying about Python installation or setup.
 */

const { spawnTraceTap } = require('../scripts/wrapper');

// Pass all arguments to the Python CLI
const args = process.argv.slice(2);
spawnTraceTap('tracetap', args);
