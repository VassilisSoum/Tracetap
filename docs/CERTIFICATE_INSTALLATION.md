# Certificate Installation Guide

To use TraceTap with HTTPS traffic, you need to install the mitmproxy CA certificate so your browser and applications trust it.

TraceTap now uses a **simplified, unified certificate installer** that's more reliable and provides better error messages than previous versions.

## 🚀 Quick Start

### Prerequisites
- Python 3 (required for running TraceTap)
- mitmproxy certificate generated (automatically created when you first run TraceTap)

### Generate Certificate (First Time)
The certificate is automatically generated when you run TraceTap for the first time:
```bash
python tracetap.py --listen 8080
# Press Ctrl+C after a few seconds - certificate is now generated
```

### Install Certificate

**All platforms support both methods:**

#### Method 1: Direct Python Installation (Recommended)
```bash
# Navigate to the scripts directory
cd src/tracetap/scripts

# Install certificate
python3 cert_manager.py install

# Verify installation
python3 cert_manager.py verify

# Check certificate info
python3 cert_manager.py info
```

#### Method 2: Platform-Specific Scripts (Backwards Compatible)
```bash
# Linux
./chrome-cert-manager.sh install

# macOS
./macos-cert-manager.sh install

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 install
```

---

## 🐧 Linux

### Automatic Installation
```bash
cd src/tracetap/scripts
python3 cert_manager.py install
```

**What it does:**
- Installs certificate to system-wide trust store (requires sudo)
- Works with Chrome, Chromium, Curl, and all system apps
- Automatically detects your Linux distribution (Debian/Ubuntu, RHEL/Fedora, Arch)
- Uses appropriate update command for your distro

### Manual Installation
If automatic installation fails:

**Debian/Ubuntu:**
```bash
sudo cp ~/.mitmproxy/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt
sudo update-ca-certificates
```

**RHEL/Fedora/CentOS:**
```bash
sudo cp ~/.mitmproxy/mitmproxy-ca-cert.pem /etc/pki/ca-trust/source/anchors/mitmproxy.pem
sudo update-ca-trust
```

**Arch Linux:**
```bash
sudo cp ~/.mitmproxy/mitmproxy-ca-cert.pem /etc/ca-certificates/trust-source/anchors/mitmproxy.pem
sudo trust extract-compat
```

### Firefox on Linux
Firefox uses its own certificate store. For Firefox support:
```bash
# Install NSS tools
sudo apt-get install libnss3-tools  # Debian/Ubuntu
sudo dnf install nss-tools          # Fedora
sudo pacman -S nss                  # Arch

# Add certificate to Firefox
certutil -A -d sql:$HOME/.mozilla/firefox/*.default* \
  -t "C,," -n "mitmproxy" -i ~/.mitmproxy/mitmproxy-ca-cert.pem
```

### Verification
```bash
python3 cert_manager.py verify
# or
./chrome-cert-manager.sh status
```

---

## 🍎 macOS

### Automatic Installation
```bash
cd src/tracetap/scripts
python3 cert_manager.py install
```

**What it does:**
- Adds certificate to macOS login keychain
- Sets trust to "Always Trust"
- You will be prompted for your password
- Works with Safari, Chrome, and all macOS apps

### Manual Installation
If automatic installation fails:

#### Option 1: Command Line
```bash
security add-trusted-cert -d -r trustRoot \
  -k ~/Library/Keychains/login.keychain-db \
  ~/.mitmproxy/mitmproxy-ca-cert.pem
```

#### Option 2: Keychain Access (GUI)
1. Open **Keychain Access** (⌘+Space, type "Keychain")
2. Select **login** keychain in left sidebar
3. Drag and drop `~/.mitmproxy/mitmproxy-ca-cert.pem` to the keychain
4. Double-click the imported certificate
5. Expand **Trust** section
6. Set "When using this certificate" to **Always Trust**
7. Close window and enter your password

### Firefox on macOS
Firefox requires additional setup:
```bash
# Install NSS tools
brew install nss

# Add certificate to Firefox
certutil -A -d sql:$HOME/Library/Application\ Support/Firefox/Profiles/*.default* \
  -t "C,," -n "mitmproxy" -i ~/.mitmproxy/mitmproxy-ca-cert.pem
```

### Verification
```bash
python3 cert_manager.py verify
# or
./macos-cert-manager.sh status
```

---

## 🪟 Windows

### Automatic Installation
```powershell
cd src\tracetap\scripts
python cert_manager.py install
```

**What it does:**
- Installs certificate to Current User trust store (no admin required)
- Uses PowerShell's built-in certificate handling (reliable)
- Works with Chrome, Edge, and all Windows apps
- For system-wide trust, run PowerShell as Administrator

### Manual Installation
If automatic installation fails:

#### Option 1: PowerShell
```powershell
$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2("$env:USERPROFILE\.mitmproxy\mitmproxy-ca-cert.pem")
$store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
$store.Open("ReadWrite")
$store.Add($cert)
$store.Close()
```

#### Option 2: GUI
1. Double-click certificate file: `%USERPROFILE%\.mitmproxy\mitmproxy-ca-cert.pem`
2. Click **Install Certificate**
3. Select **Current User**
4. Select **Place all certificates in the following store**
5. Click **Browse** → Select **Trusted Root Certification Authorities**
6. Click **Next** → **Finish**
7. Click **Yes** on security warning

### Firefox on Windows
Firefox requires additional setup. **Note:** The old script had a bug in the Firefox path - this is now fixed.
```powershell
# Download certutil from Mozilla
# Install certificate to Firefox profiles manually
```

### Verification
```powershell
python cert_manager.py verify
# or
powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 status
```

---

## 📋 Complete Workflow

### 1. Generate Certificate (First Time)

Run TraceTap once to generate the certificate:
```bash
python tracetap.py --listen 8080
# Wait 5 seconds, then press Ctrl+C
```

### 2. Install Certificate

**Linux:**
```bash
cd src/tracetap/scripts
python3 cert_manager.py install
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

**All Platforms:**
```bash
cd src/tracetap/scripts

# Check certificate status
python3 cert_manager.py verify

# View certificate info
python3 cert_manager.py info

# Reinstall if needed
python3 cert_manager.py uninstall
python3 cert_manager.py install
```

**Platform-Specific Verification:**

**macOS:**
```bash
# Verify Keychain trust
open ~/Library/Keychains/login.keychain-db
# Search for "mitmproxy" and ensure it's trusted
```

**Windows:**
```powershell
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

**Still having issues?** See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) or open an issue on GitHub.