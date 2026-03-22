#!/usr/bin/env node

/**
 * TraceTap Playwright Test Generator
 */

const { spawnTraceTap } = require('../scripts/wrapper');

const args = process.argv.slice(2);
spawnTraceTap('tracetap-playwright', args);
