#!/usr/bin/env node

/**
 * TraceTap AI Postman Generator
 */

const { spawnTraceTap } = require('../scripts/wrapper');

const args = process.argv.slice(2);
spawnTraceTap('tracetap-ai-postman', args);
