#!/usr/bin/env node

/**
 * TraceTap Quickstart - Interactive onboarding
 */

const { spawnTraceTap } = require('../scripts/wrapper');

const args = process.argv.slice(2);
spawnTraceTap('tracetap-quickstart', args);
