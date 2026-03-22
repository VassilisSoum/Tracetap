# TraceTap Homebrew Formula

This directory contains the Homebrew formula for installing TraceTap on macOS.

## For Users: Installing TraceTap via Homebrew

### Option 1: Install from this tap (once published)

```bash
brew tap VassilisSoum/tracetap
brew install tracetap
```

### Option 2: Install directly from formula URL

```bash
brew install https://raw.githubusercontent.com/VassilisSoum/tracetap/master/tracetap.rb
```

### Verify Installation

```bash
tracetap --version
tracetap --help
```

## For Maintainers: Publishing to Homebrew

### Step 1: Update SHA256 Hash

Before publishing, you need to update the SHA256 hash in `tracetap.rb`:

```bash
# Download the package from PyPI
wget https://files.pythonhosted.org/packages/source/t/tracetap/tracetap-1.0.0.tar.gz

# Calculate SHA256
shasum -a 256 tracetap-1.0.0.tar.gz
```

Replace `PLACEHOLDER_SHA256_HASH` in the formula with the calculated hash.

### Step 2: Test the Formula Locally

```bash
# Audit the formula
brew audit --new-formula tracetap.rb

# Install locally to test
brew install --build-from-source ./tracetap.rb

# Run tests
brew test tracetap

# Verify installation
tracetap --version
```

### Step 3: Create a Homebrew Tap (Optional)

To create an official tap at `homebrew-tracetap`:

```bash
# Create a new GitHub repository: homebrew-tracetap
# Copy tracetap.rb to the repository root or Formula/ directory
# Users can then install with:
#   brew tap VassilisSoum/tracetap
#   brew install tracetap
```

### Step 4: Submit to Homebrew Core (Advanced)

For inclusion in the main Homebrew repository:

1. Fork https://github.com/Homebrew/homebrew-core
2. Add `tracetap.rb` to `Formula/` directory
3. Test thoroughly on Intel and Apple Silicon Macs
4. Submit a Pull Request

**Requirements for homebrew-core:**
- Must be a notable project (significant user base)
- Active maintenance
- Stable releases
- Pass all brew audit checks

## Updating the Formula

When releasing a new version:

1. Update the `version` and `url` in the formula
2. Calculate new SHA256 hash
3. Update `sha256` in the formula
4. Test installation
5. Commit and push changes

```bash
# Example update process
VERSION=1.1.0
URL="https://files.pythonhosted.org/packages/source/t/tracetap/tracetap-${VERSION}.tar.gz"
SHA256=$(curl -sL "$URL" | shasum -a 256 | cut -d' ' -f1)

# Update formula with new version and hash
# Test
brew upgrade tracetap
```

## Troubleshooting

### Formula Audit Failures

```bash
# Check for issues
brew audit --strict tracetap.rb

# Common fixes:
# - Ensure all resources have proper SHA256 hashes
# - Check Python version compatibility
# - Verify dependencies are available in Homebrew
```

### Installation Fails

```bash
# Verbose install for debugging
brew install -v tracetap

# Check logs
brew gist-logs tracetap
```

### Python Version Issues

The formula uses `python@3.11` by default. For different Python versions:

```bash
# In formula, change:
depends_on "python@3.12"  # or desired version
```

## Resources

- [Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [Python Formula Guide](https://docs.brew.sh/Python-for-Formula-Authors)
- [Homebrew Node for New Formulae](https://docs.brew.sh/Node-for-New-Formulae)
- [Acceptable Formulae](https://docs.brew.sh/Acceptable-Formulae)

## Support

For issues with the Homebrew formula:
- Open an issue at: https://github.com/VassilisSoum/tracetap/issues
- Tag with `homebrew` label
