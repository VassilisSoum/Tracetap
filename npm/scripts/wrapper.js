/**
 * TraceTap npm wrapper core functionality
 *
 * Handles spawning Python CLI commands with proper error handling
 * and cross-platform compatibility.
 */

const { spawn } = require('child_process');
const { platform } = require('os');

/**
 * Find Python command on the system
 * @returns {string} Python command (python3, python, or py)
 */
function findPython() {
  const os = platform();

  // Windows typically uses 'py' launcher or 'python'
  if (os === 'win32') {
    return 'python';
  }

  // Unix-like systems prefer python3
  return 'python3';
}

/**
 * Spawn a TraceTap command
 * @param {string} command - TraceTap command name
 * @param {string[]} args - Command arguments
 */
function spawnTraceTap(command, args = []) {
  const python = findPython();

  // Spawn the Python process
  const child = spawn(python, ['-m', 'pip', 'show', 'tracetap'], {
    stdio: 'pipe'
  });

  child.on('close', (code) => {
    if (code !== 0) {
      // TraceTap not installed - try to guide user
      console.error('❌ TraceTap is not installed.');
      console.error('');
      console.error('Install it with:');
      console.error('  npm install -g tracetap');
      console.error('');
      console.error('Or use the one-line installer:');
      console.error('  curl -sSL https://get.tracetap.io | bash');
      console.error('');
      process.exit(1);
    }

    // TraceTap is installed - run the command
    const tracetapProcess = spawn(command, args, {
      stdio: 'inherit',
      shell: true
    });

    tracetapProcess.on('error', (error) => {
      if (error.code === 'ENOENT') {
        console.error(`❌ Command not found: ${command}`);
        console.error('');
        console.error('Make sure TraceTap is properly installed:');
        console.error('  pip install tracetap');
        console.error('');
        console.error('Or reinstall with:');
        console.error('  npm install -g tracetap');
        console.error('');
      } else {
        console.error(`❌ Error running TraceTap: ${error.message}`);
      }
      process.exit(1);
    });

    tracetapProcess.on('exit', (code, signal) => {
      if (signal) {
        process.exit(1);
      } else {
        process.exit(code || 0);
      }
    });
  });

  child.on('error', (error) => {
    console.error(`❌ Error checking TraceTap installation: ${error.message}`);
    console.error('');
    console.error('Python may not be installed. Install Python 3.8+ from:');
    console.error('  https://python.org');
    console.error('');
    process.exit(1);
  });
}

module.exports = { spawnTraceTap, findPython };
