# Certificate Installation Guide

To use TraceTap with HTTPS traffic, you need to install the mitmproxy CA certificate so your browser trusts it. Use the appropriate script for your operating system.

## 🐧 Linux

### Requirements
- `libnss3-tools` (auto-installed by script)

### Installation

```bash
# Make script executable
chmod +x chrome-cert-manager.sh

# Install certificate
./chrome-cert-manager.sh install

# Follow prompts:
# - Chrome/Chromium: Yes (automatic)
# - System-wide: Optional (recommended for curl/CLI tools)
# - Firefox: Optional
```

### Usage

```bash
# Check status
./chrome-cert-manager.sh status

# Verify HTTPS works
./chrome-cert-manager.sh verify

# Remove certificate
./chrome-cert-manager.sh remove
```

### Supported Browsers
- ✅ Chrome
- ✅ Chromium
- ✅ Firefox (optional, requires certutil)
- ✅ All Chromium-based browsers (Brave, Vivaldi, etc.)

---

## 🪟 Windows

### Requirements
- PowerShell (built-in)
- Administrator rights (optional, for system-wide install)

### Installation

```powershell
# Run PowerShell as regular user (recommended)
# Or as Administrator for system-wide installation

# Install certificate
powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 install

# Follow prompts:
# - Firefox: Optional
```

### Usage

```powershell
# Check status
powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 status

# Remove certificate
powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 remove
```

### Supported Browsers
- ✅ Chrome
- ✅ Edge
- ✅ Internet Explorer
- ✅ All Windows applications
- ✅ Firefox (optional, requires NSS certutil)

---

## 📋 Complete Workflow

### 1. Install Certificate (One-time)

**Linux:**
```bash
./chrome-cert-manager.sh install
```

**macOS:**
```bash
./macos-cert-manager.sh install
```

**Windows:**
```powershell
powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 install
```

### 2. Restart Browsers

Close and reopen all browser windows for the certificate to take effect.

### 3. Start TraceTap

**Linux/macOS:**
```bash
./tracetap-linux-x64 --listen 8080 --raw-log captures.json
# or
./tracetap-macos-x64 --listen 8080 --raw-log captures.json
```

**Windows:**
```powershell
.\tracetap-windows-x64.exe --listen 8080 --raw-log captures.json
```

### 4. Configure Browser Proxy

**Option A: FoxyProxy Extension (Recommended)**

1. Install FoxyProxy Standard from your browser's extension store
2. Add new proxy:
   - Title: TraceTap
   - Type: HTTP
   - Hostname: `localhost`
   - Port: `8080`
3. Enable the proxy

**Option B: Manual Proxy Settings**

**Chrome/Edge:**
- Settings → System → Open proxy settings
- Manual proxy: `localhost:8080`

**Firefox:**
- Settings → Network Settings → Manual proxy
- HTTP Proxy: `localhost`, Port: `8080`
- Check "Also use this proxy for HTTPS"

**Safari (macOS):**
- System Preferences → Network → Advanced → Proxies
- Check "Web Proxy (HTTP)" and "Secure Web Proxy (HTTPS)"
- Server: `localhost:8080`

### 5. Test HTTPS

Visit any HTTPS site (e.g., `https://httpbin.org/get`)

✅ **Expected:** No certificate warnings
❌ **If you see warnings:** Certificate not installed correctly

---

## 🔧 Troubleshooting

### Certificate Warnings Still Appear

**Linux:**
```bash
# Check certificate status
./chrome-cert-manager.sh status

# Reinstall
./chrome-cert-manager.sh remove
./chrome-cert-manager.sh install
```

**macOS:**
```bash
# Check status
./macos-cert-manager.sh status

# Verify Keychain trust
open ~/Library/Keychains/login.keychain-db
# Search for "mitmproxy" and ensure it's trusted
```

**Windows:**
```powershell
# Check status
powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 status

# Open Certificate Manager manually
certmgr.msc
# Navigate to: Trusted Root Certification Authorities → Certificates
# Look for "mitmproxy"
```

### Certificate File Not Found

The certificate is generated the first time you run mitmproxy/TraceTap:

```bash
# Generate certificate manually
mitmdump -p 8081
# Wait 5 seconds, then press Ctrl+C

# Or run TraceTap briefly
./tracetap-* --listen 8081
# Press Ctrl+C after a few seconds

# Certificate will be at ~/.mitmproxy/mitmproxy-ca-cert.pem
```

### Firefox Still Shows Warnings

Firefox uses its own certificate store. Install separately:

**Linux:**
```bash
# Install NSS tools
sudo apt-get install libnss3-tools  # Debian/Ubuntu
sudo dnf install nss-tools          # Fedora
sudo pacman -S nss                  # Arch

# Run install script and answer "yes" for Firefox
```

**macOS:**
```bash
# Install NSS tools
brew install nss

# Run install script and answer "yes" for Firefox
```

**Windows:**
- Download NSS tools from Mozilla
- Run install script and answer "yes" for Firefox

### System Tools (curl, wget) Don't Trust Certificate

Install system-wide:

**Linux:**
```bash
./chrome-cert-manager.sh install
# Answer "yes" to "Install system-wide"
```

**macOS:**
- Certificate is automatically system-wide on macOS

**Windows:**
- Run PowerShell as Administrator
- Install certificate

### "Access Denied" on Windows

Run PowerShell as Administrator:

```powershell
# Right-click PowerShell → "Run as Administrator"
powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 install
```

### Certificate Expired

Regenerate certificate:

```bash
# Remove old certificate files
rm -rf ~/.mitmproxy/

# Generate new certificate
./tracetap-* --listen 8081
# Press Ctrl+C after a few seconds

# Reinstall
./chrome-cert-manager.sh install    # Linux
./macos-cert-manager.sh install     # macOS
# or Windows PowerShell script
```

---

## 🔐 Security Notes

### What Does This Certificate Do?

The mitmproxy CA certificate allows TraceTap to intercept HTTPS traffic by:

1. Acting as a "man-in-the-middle" proxy
2. Creating certificates for sites you visit on-the-fly
3. Re-encrypting traffic between you and the destination

This is the **same technique** used by:
- Corporate security proxies
- Parental control software
- Network debugging tools

### Is This Safe?

**For local development: YES ✅**
- Certificate is only on your machine
- Only works when TraceTap is running
- Only intercepts traffic you send through the proxy

**Important warnings: ⚠️**
- Don't install on shared/public computers
- Don't share your `~/.mitmproxy/` directory
- Remove certificate when done testing
- Don't use for capturing credentials in production

### When to Remove the Certificate

Remove the certificate when:
- You're done using TraceTap
- Switching to a different computer
- You no longer need HTTPS interception

```bash
# Linux
./chrome-cert-manager.sh remove

# macOS  
./macos-cert-manager.sh remove

# Windows
powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 remove
```

---

## 📚 Additional Resources

### Certificate Locations

**Linux:**
- Certificate file: `~/.mitmproxy/mitmproxy-ca-cert.pem`
- Chrome/Chromium: `~/.pki/nssdb/`
- Firefox: `~/.mozilla/firefox/*.default*/`
- System-wide: `/usr/local/share/ca-certificates/`

**macOS:**
- Certificate file: `~/.mitmproxy/mitmproxy-ca-cert.pem`
- Keychain: `~/Library/Keychains/login.keychain-db`
- Firefox: `~/Library/Application Support/Firefox/Profiles/`

**Windows:**
- Certificate file: `%USERPROFILE%\.mitmproxy\mitmproxy-ca-cert.pem`
- Certificate Store: `Cert:\CurrentUser\Root`
- Firefox: `%APPDATA%\Mozilla\Firefox\Profiles\`

### Manual Installation

If scripts don't work, install manually:

**Linux Chrome:**
```bash
certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n mitmproxy \
  -i ~/.mitmproxy/mitmproxy-ca-cert.pem
```

**macOS:**
```bash
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain \
  ~/.mitmproxy/mitmproxy-ca-cert.pem
```

**Windows:**
```powershell
# Open Certificate Manager
certmgr.msc

# Import → Trusted Root Certification Authorities → Certificates
# Browse to: %USERPROFILE%\.mitmproxy\mitmproxy-ca-cert.pem
```

### Getting Help

**Check certificate status:**
```bash
# Linux
./chrome-cert-manager.sh status

# macOS
./macos-cert-manager.sh status

# Windows
powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 status
```

**Common issues:**
1. Certificate not found → Run TraceTap once to generate it
2. Still seeing warnings → Browser not restarted or wrong proxy settings
3. Firefox issues → Install NSS tools and reinstall for Firefox
4. System tools failing → Install system-wide certificate

---

## ✅ Quick Verification

After installation, verify everything works:

1. **Certificate installed:**
   ```bash
   # Check with status command (see above for your OS)
   ```

2. **TraceTap running:**
   ```bash
   # Start TraceTap
   ./tracetap-* --listen 8080
   ```

3. **Proxy configured:**
   - FoxyProxy enabled OR
   - Manual proxy settings applied

4. **HTTPS works:**
   - Visit: https://httpbin.org/get
   - Should load without warnings ✅

5. **Traffic captured:**
   - Check TraceTap output
   - Should show captured requests ✅

**All green?** You're ready to capture traffic! 🎉

**Still having issues?** Check the troubleshooting section above or open an issue on GitHub.

## 🍎 macOS

### Requirements
- macOS Keychain (built-in)
- Optional: `nss` for Firefox (`brew install nss`)

### Installation

```bash
# Make script executable
chmod +x macos-cert-manager.sh

# Install certificate
./macos-cert-manager.sh install

# You'll be prompted for your password to modify Keychain
```

### Usage

```bash
# Check status
./macos-cert-manager.sh status

# Remove certificate
./macos-cert-manager.sh remove
```

### Supported Browsers
- ✅ Safari
- ✅ Chrome
- ✅ Edge
- ✅ All system browsers
- ✅ Firefox (optional, requires certutil)

---