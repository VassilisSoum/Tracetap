#!/usr/bin/env node

/**
 * TraceTap WireMock Stub Generator
 */

const { spawnTraceTap } = require('../scripts/wrapper');

const args = process.argv.slice(2);
spawnTraceTap('tracetap2wiremock', args);
