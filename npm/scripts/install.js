/**
 * Post-install script for TraceTap npm package
 *
 * Ensures Python and TraceTap are installed, guides user through setup
 */

const { execSync } = require('child_process');
const { platform } = require('os');

const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  red: '\x1b[31m',
};

function log(message, color = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

function checkPython() {
  const pythonCmd = platform() === 'win32' ? 'python' : 'python3';

  try {
    const version = execSync(`${pythonCmd} --version`, {
      encoding: 'utf-8',
      stdio: 'pipe'
    }).trim();

    log(`✓ Found ${version}`, colors.green);
    return true;
  } catch (error) {
    log('✗ Python not found', colors.red);
    log('', colors.reset);
    log('TraceTap requires Python 3.8 or higher.', colors.yellow);
    log('Install Python from: https://python.org', colors.blue);
    log('', colors.reset);
    return false;
  }
}

function checkTraceTap() {
  const pythonCmd = platform() === 'win32' ? 'python' : 'python3';

  try {
    execSync(`${pythonCmd} -m pip show tracetap`, {
      encoding: 'utf-8',
      stdio: 'pipe'
    });

    log('✓ TraceTap is already installed', colors.green);
    return true;
  } catch (error) {
    log('⚠ TraceTap not installed yet', colors.yellow);
    return false;
  }
}

function installTraceTap() {
  const pythonCmd = platform() === 'win32' ? 'python' : 'python3';

  log('', colors.reset);
  log('Installing TraceTap via pip...', colors.blue);
  log('', colors.reset);

  try {
    execSync(`${pythonCmd} -m pip install --user tracetap`, {
      stdio: 'inherit'
    });

    log('', colors.reset);
    log('✓ TraceTap installed successfully!', colors.green);
    return true;
  } catch (error) {
    log('', colors.reset);
    log('✗ Failed to install TraceTap automatically', colors.red);
    log('', colors.reset);
    log('Please install manually:', colors.yellow);
    log(`  ${pythonCmd} -m pip install tracetap`, colors.blue);
    log('', colors.reset);
    log('Or use the one-line installer:', colors.yellow);
    log('  curl -sSL https://get.tracetap.io | bash', colors.blue);
    log('', colors.reset);
    return false;
  }
}

function main() {
  log('', colors.reset);
  log('╔═══════════════════════════════════════════════════════════╗', colors.bright + colors.blue);
  log('║                                                           ║', colors.bright + colors.blue);
  log('║              TraceTap npm Package Setup                  ║', colors.bright + colors.blue);
  log('║                                                           ║', colors.bright + colors.blue);
  log('╚═══════════════════════════════════════════════════════════╝', colors.bright + colors.blue);
  log('', colors.reset);

  // Check Python
  log('Checking Python installation...', colors.blue);
  if (!checkPython()) {
    process.exit(1);
  }

  log('', colors.reset);

  // Check TraceTap
  log('Checking TraceTap installation...', colors.blue);
  if (checkTraceTap()) {
    log('', colors.reset);
    log('🎉 All set! Try running:', colors.green);
    log('  npx tracetap-quickstart', colors.bright);
    log('', colors.reset);
    return;
  }

  // Install TraceTap
  if (installTraceTap()) {
    log('', colors.reset);
    log('🎉 Installation complete!', colors.green);
    log('', colors.reset);
    log('Get started with:', colors.blue);
    log('  npx tracetap-quickstart', colors.bright);
    log('', colors.reset);
    log('Or see all commands:', colors.blue);
    log('  npx tracetap --help', colors.bright);
    log('', colors.reset);
  } else {
    process.exit(1);
  }
}

// Only run if called directly (not required as module)
if (require.main === module) {
  main();
}

module.exports = { checkPython, checkTraceTap, installTraceTap };
