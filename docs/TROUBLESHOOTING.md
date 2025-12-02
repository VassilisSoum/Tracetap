# TraceTap Troubleshooting Guide

This guide helps you solve common issues with TraceTap certificate installation and HTTPS interception.

## 🔍 Quick Diagnostics

Before diving into specific issues, run these diagnostic commands:

```bash
# Navigate to scripts directory
cd src/tracetap/scripts

# Check certificate info
python3 cert_manager.py info

# Verify certificate is installed
python3 cert_manager.py verify
```

---

## 🚨 Common Issues

### Issue 1: "Certificate not found" Error

**Symptoms:**
```
❌ Certificate file not found
Expected location: ~/.mitmproxy/mitmproxy-ca-cert.pem
```

**Cause:** Certificate hasn't been generated yet.

**Solution:**
```bash
# Generate certificate by running TraceTap briefly
python tracetap.py --listen 8080
# Wait 5 seconds, then press Ctrl+C

# Verify certificate was created
ls ~/.mitmproxy/mitmproxy-ca-cert.pem

# Now install it
cd src/tracetap/scripts
python3 cert_manager.py install
```

---

### Issue 2: Browser Still Shows Certificate Warnings

**Symptoms:**
- Visit HTTPS site → "Your connection is not private" warning
- Certificate error: NET::ERR_CERT_AUTHORITY_INVALID

**Diagnostic Steps:**

1. **Verify certificate is installed:**
   ```bash
   python3 cert_manager.py verify
   ```

2. **Check browser is using proxy:**
   - Open: http://mitm.it
   - Should show mitmproxy web interface
   - If it doesn't load: proxy not configured

3. **Check TraceTap is running:**
   ```bash
   # Should see TraceTap process
   ps aux | grep tracetap
   # or
   lsof -i :8080
   ```

**Solutions:**

**Solution A: Reinstall Certificate**
```bash
cd src/tracetap/scripts
python3 cert_manager.py uninstall
python3 cert_manager.py install
```

**Solution B: Restart Browser**
```bash
# Close ALL browser windows completely
# Then reopen browser
```

**Solution C: Clear Browser Cache** (Chrome/Edge)
```
1. Settings → Privacy and Security → Clear browsing data
2. Select "Cached images and files"
3. Clear data
4. Restart browser
```

**Solution D: Platform-Specific Fixes**

**macOS:**
```bash
# Verify certificate trust in Keychain
security find-certificate -c "mitmproxy" -p login.keychain | openssl x509 -noout -text

# If not trusted, manually set trust:
# 1. Open Keychain Access
# 2. Search for "mitmproxy"
# 3. Double-click certificate
# 4. Expand "Trust" section
# 5. Set "When using this certificate" to "Always Trust"
```

**Windows:**
```powershell
# Verify certificate in trust store
Get-ChildItem Cert:\CurrentUser\Root | Where-Object { $_.Subject -like "*mitmproxy*" }

# If not found, check installation:
certmgr.msc
# Look in: Trusted Root Certification Authorities → Certificates
```

**Linux:**
```bash
# Verify system-wide certificate
ls -l /usr/local/share/ca-certificates/mitmproxy.crt

# If missing, reinstall
sudo cp ~/.mitmproxy/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt
sudo update-ca-certificates
```

---

### Issue 3: Firefox-Specific Certificate Warnings

**Symptoms:**
- Other browsers work fine
- Firefox shows: "Warning: Potential Security Risk Ahead"

**Cause:** Firefox uses its own certificate store, separate from system.

**Solution:**

**Install NSS Tools:**
```bash
# macOS
brew install nss

# Debian/Ubuntu
sudo apt-get install libnss3-tools

# Fedora/RHEL
sudo dnf install nss-tools

# Arch
sudo pacman -S nss
```

**Add Certificate to Firefox:**
```bash
# Find Firefox profiles
# macOS
ls ~/Library/Application\ Support/Firefox/Profiles/

# Linux
ls ~/.mozilla/firefox/

# Windows
dir %APPDATA%\Mozilla\Firefox\Profiles\

# Install to each profile
certutil -A -d sql:$HOME/.mozilla/firefox/*.default* \
  -t "C,," -n "mitmproxy" -i ~/.mitmproxy/mitmproxy-ca-cert.pem
```

**Verify Installation:**
```bash
# List certificates in Firefox
certutil -L -d sql:$HOME/.mozilla/firefox/*.default*

# Should see "mitmproxy" in the list
```

---

### Issue 4: "Python 3 not found" Error

**Symptoms:**
```
❌ Python 3 is required but not found
```

**Solution:**

**macOS:**
```bash
# Install Python 3 via Homebrew
brew install python3

# or download from python.org
open https://www.python.org/downloads/macos/
```

**Windows:**
```powershell
# Download Python from python.org
start https://www.python.org/downloads/windows/

# During installation:
# ✅ Check "Add Python to PATH"
# ✅ Check "Install for all users" (optional)
```

**Linux:**
```bash
# Debian/Ubuntu
sudo apt-get install python3

# Fedora/RHEL
sudo dnf install python3

# Arch
sudo pacman -S python
```

**Verify Installation:**
```bash
python3 --version
# Should show: Python 3.x.x
```

---

### Issue 5: "Permission Denied" Errors

**Symptoms:**

**macOS:**
```
security: SecKeychainItemImport: User interaction is not allowed.
```

**Linux:**
```
cp: cannot create regular file '/usr/local/share/ca-certificates/...': Permission denied
```

**Windows:**
```
Access to the path is denied
```

**Solutions:**

**macOS:**
```bash
# Run in interactive terminal (not background job)
# Ensure you enter password when prompted

# If still failing, manual installation:
open ~/Library/Keychains/login.keychain-db
# Drag and drop certificate file into Keychain Access
```

**Linux:**
```bash
# System-wide installation requires sudo
python3 cert_manager.py install
# Enter sudo password when prompted

# For user-only (Chrome/Chromium):
certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n mitmproxy \
  -i ~/.mitmproxy/mitmproxy-ca-cert.pem
```

**Windows:**
```powershell
# For system-wide trust, run PowerShell as Administrator:
# Right-click PowerShell → "Run as Administrator"
python cert_manager.py install

# For current user only (no admin required):
# This should work without admin rights
python cert_manager.py install
```

---

### Issue 6: Command-Line Tools (curl, wget) Don't Trust Certificate

**Symptoms:**
```bash
curl https://example.com
# SSL certificate problem: unable to get local issuer certificate
```

**Cause:** System-wide certificate not installed.

**Solution:**

**Linux:**
```bash
# Install system-wide (requires sudo)
sudo cp ~/.mitmproxy/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt
sudo update-ca-certificates

# Verify
curl -I https://example.com
```

**macOS:**
```bash
# macOS keychain is automatically system-wide
# If curl still fails, use certificate directly:
curl --cacert ~/.mitmproxy/mitmproxy-ca-cert.pem https://example.com
```

**Windows:**
```powershell
# Install to system store (requires admin):
# Run PowerShell as Administrator
python cert_manager.py install

# Or use certificate directly:
curl --cacert %USERPROFILE%\.mitmproxy\mitmproxy-ca-cert.pem https://example.com
```

---

### Issue 7: "Failed to install certificate" (Windows)

**Symptoms:**
```
❌ PowerShell installation failed
Error: Exception calling "Add" with "1" argument(s)
```

**Cause:** Corrupt certificate file or PowerShell execution policy.

**Solutions:**

**Solution A: Regenerate Certificate**
```powershell
# Remove old certificate
Remove-Item -Recurse -Force $env:USERPROFILE\.mitmproxy

# Generate new certificate
python tracetap.py --listen 8080
# Press Ctrl+C after 5 seconds

# Reinstall
cd src\tracetap\scripts
python cert_manager.py install
```

**Solution B: Manual GUI Installation**
```powershell
# 1. Double-click certificate file
explorer $env:USERPROFILE\.mitmproxy\mitmproxy-ca-cert.pem

# 2. Follow installation wizard:
#    - Click "Install Certificate"
#    - Select "Current User"
#    - Select "Place all certificates in the following store"
#    - Browse → "Trusted Root Certification Authorities"
#    - Finish
```

**Solution C: Check Execution Policy**
```powershell
# Check current policy
Get-ExecutionPolicy

# If "Restricted", temporarily bypass:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Then try installation again
python cert_manager.py install
```

---

### Issue 8: Certificate Expired

**Symptoms:**
```
NET::ERR_CERT_DATE_INVALID
Certificate has expired
```

**Cause:** mitmproxy certificates expire after 1 year.

**Solution:**
```bash
# 1. Uninstall old certificate
cd src/tracetap/scripts
python3 cert_manager.py uninstall

# 2. Remove certificate directory
rm -rf ~/.mitmproxy/

# 3. Generate new certificate
python tracetap.py --listen 8080
# Press Ctrl+C after 5 seconds

# 4. Install new certificate
python3 cert_manager.py install

# 5. Verify
python3 cert_manager.py verify
```

---

### Issue 9: Proxy Not Intercepting HTTPS Traffic

**Symptoms:**
- HTTP sites work fine
- HTTPS sites: connection errors or certificate warnings
- TraceTap doesn't show HTTPS requests

**Diagnostic Steps:**

1. **Verify proxy is running:**
   ```bash
   lsof -i :8080
   # or
   netstat -an | grep 8080
   ```

2. **Test proxy with HTTP first:**
   ```bash
   curl -x http://localhost:8080 http://httpbin.org/get
   # Should work and show in TraceTap
   ```

3. **Test HTTPS:**
   ```bash
   curl -x http://localhost:8080 https://httpbin.org/get
   # Should work if certificate installed correctly
   ```

**Solutions:**

**Solution A: Verify Proxy Configuration**

**Browser Environment Variables:**
```bash
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# Test
curl https://example.com
```

**FoxyProxy Settings:**
- Protocol: HTTP (not HTTPS, not SOCKS)
- Host: localhost
- Port: 8080
- Enable proxy

**Solution B: Check Certificate Installation**
```bash
python3 cert_manager.py verify

# Should show:
# ✅ Certificate is installed and trusted
```

**Solution C: Restart Everything**
```bash
# 1. Stop TraceTap (Ctrl+C)
# 2. Close all browser windows
# 3. Start TraceTap
python tracetap.py --listen 8080

# 4. Reopen browser
# 5. Test: https://httpbin.org/get
```

---

## 🛠️ Advanced Troubleshooting

### Debug Mode

Enable verbose output for debugging:

```bash
python3 cert_manager.py install --verbose

# Shows detailed command execution and error messages
```

### Collect Diagnostic Information

If you need to report an issue, collect this information:

```bash
# 1. Platform info
uname -a  # Linux/macOS
systeminfo  # Windows

# 2. Python version
python3 --version

# 3. Certificate status
python3 cert_manager.py info

# 4. Certificate file
ls -la ~/.mitmproxy/

# 5. Platform-specific verification
# macOS:
security find-certificate -a -c "mitmproxy" login.keychain

# Windows:
Get-ChildItem Cert:\CurrentUser\Root | Where-Object { $_.Subject -like "*mitmproxy*" } | Format-List

# Linux:
ls -l /usr/local/share/ca-certificates/mitmproxy.crt
```

### Clean Reinstall

If all else fails, perform a clean reinstallation:

```bash
# 1. Uninstall certificate
cd src/tracetap/scripts
python3 cert_manager.py uninstall

# 2. Remove all mitmproxy data
rm -rf ~/.mitmproxy/

# 3. Close all browsers

# 4. Generate fresh certificate
python tracetap.py --listen 8080
# Press Ctrl+C after 5 seconds

# 5. Verify certificate exists
ls ~/.mitmproxy/mitmproxy-ca-cert.pem

# 6. Install certificate
python3 cert_manager.py install

# 7. Verify installation
python3 cert_manager.py verify

# 8. Restart browsers

# 9. Test HTTPS
curl https://httpbin.org/get
```

---

## 📖 Additional Resources

- **Certificate Installation Guide:** [CERTIFICATE_INSTALLATION.md](./CERTIFICATE_INSTALLATION.md)
- **Getting Started:** [getting-started.md](./getting-started.md)
- **GitHub Issues:** [Report a bug](https://github.com/VassilisSoum/tracetap/issues)
- **mitmproxy Docs:** [https://docs.mitmproxy.org](https://docs.mitmproxy.org)

---

## 🆘 Still Stuck?

If you've tried everything and still have issues:

1. **Check existing issues:** [GitHub Issues](https://github.com/VassilisSoum/tracetap/issues)
2. **Create a new issue** with:
   - Operating system and version
   - Python version
   - Error messages (full output)
   - Output of `python3 cert_manager.py info`
   - Steps you've already tried
3. **Community support:** Discuss in GitHub Discussions

We're here to help! 🚀
