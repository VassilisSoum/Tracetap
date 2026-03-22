#!/usr/bin/env node

/**
 * TraceTap Replay & Mock Server
 */

const { spawnTraceTap } = require('../scripts/wrapper');

const args = process.argv.slice(2);
spawnTraceTap('tracetap-replay', args);
