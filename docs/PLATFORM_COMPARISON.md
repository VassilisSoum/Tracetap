# Platform Comparison

Quick reference for certificate installation across different platforms.

## Scripts Overview

| Platform | Script | Language | Requirements |
|----------|--------|----------|--------------|
| **Linux** | `chrome-cert-manager.sh` | Bash | libnss3-tools (auto-installed) |
| **macOS** | `macos-cert-manager.sh` | Bash | Built-in (Keychain) |
| **Windows** | `windows-cert-manager.ps1` | PowerShell | Built-in |

## Feature Comparison

| Feature | Linux | macOS | Windows |
|---------|-------|-------|---------|
| Chrome/Chromium | ✅ | ✅ | ✅ |
| Firefox | ✅ Optional | ✅ Optional | ✅ Optional |
| Safari | N/A | ✅ | N/A |
| Edge | N/A | ✅ | ✅ |
| System-wide | ✅ Optional | ✅ Automatic | ✅ Admin required |
| Auto-install deps | ✅ | ❌ | N/A |
| Verify command | ✅ | ❌ | ❌ |

## Quick Start Commands

### Linux
```bash
chmod +x chrome-cert-manager.sh
./chrome-cert-manager.sh install
./chrome-cert-manager.sh status
```

### macOS
```bash
chmod +x macos-cert-manager.sh
./macos-cert-manager.sh install
./macos-cert-manager.sh status
```

### Windows
```powershell
powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 install
powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 status
```

## Certificate Storage Locations

| Platform | Browser Store | System Store | Certificate File |
|----------|---------------|--------------|------------------|
| **Linux** | `~/.pki/nssdb/` | `/usr/local/share/ca-certificates/` | `~/.mitmproxy/*.pem` |
| **macOS** | Keychain | Keychain (same) | `~/.mitmproxy/*.pem` |
| **Windows** | `Cert:\CurrentUser\Root` | `Cert:\LocalMachine\Root` | `%USERPROFILE%\.mitmproxy\*.pem` |

## Browser-Specific Notes

### Chrome/Chromium
- **Linux:** Uses NSS database (same as Firefox on Linux)
- **macOS:** Uses system Keychain
- **Windows:** Uses Windows Certificate Store

### Firefox
- **All platforms:** Uses its own certificate store (requires separate installation)
- **Requires:** certutil from NSS tools
- **Linux:** `apt-get install libnss3-tools`
- **macOS:** `brew install nss`
- **Windows:** Download NSS tools from Mozilla

### Safari
- **macOS only:** Automatically uses system Keychain
- **No separate installation needed**

### Edge
- **Windows:** Uses Windows Certificate Store
- **macOS:** Uses system Keychain

## Common Issues by Platform

### Linux
| Issue | Solution |
|-------|----------|
| certutil not found | Auto-installed on Debian/Ubuntu, manual on others |
| System tools don't trust | Install system-wide (answer "yes" during install) |
| Chromium vs Chrome | Same certificate store, works for both |

### macOS
| Issue | Solution |
|-------|----------|
| Password prompt | Normal - needed to modify Keychain |
| Firefox not working | Install NSS tools: `brew install nss` |
| Multiple keychains | Script uses login keychain (most common) |

### Windows
| Issue | Solution |
|-------|----------|
| Access denied | Run PowerShell as Administrator |
| Execution policy error | Use `-ExecutionPolicy Bypass` flag |
| Firefox not working | Download NSS certutil from Mozilla |

## Testing

### Verify Certificate is Installed

**Linux:**
```bash
certutil -L -d sql:$HOME/.pki/nssdb | grep mitmproxy
```

**macOS:**
```bash
security find-certificate -c mitmproxy login.keychain-db
```

**Windows:**
```powershell
Get-ChildItem Cert:\CurrentUser\Root | Where-Object {$_.Subject -like "*mitmproxy*"}
```

### Test HTTPS Interception

All platforms:
1. Start TraceTap: `./tracetap-* --listen 8080`
2. Configure proxy: `localhost:8080`
3. Visit: `https://httpbin.org/get`
4. Should load without warnings ✅

## Uninstallation

### Remove Certificate

**Linux:**
```bash
./chrome-cert-manager.sh remove
```

**macOS:**
```bash
./macos-cert-manager.sh remove
```

**Windows:**
```powershell
powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 remove
```

### Remove TraceTap Completely

All platforms:
```bash
# Remove certificate files
rm -rf ~/.mitmproxy/        # Linux/macOS
rmdir /s %USERPROFILE%\.mitmproxy\  # Windows

# Remove certificate from stores (use scripts above)

# Remove TraceTap executables
rm tracetap-*               # Linux/macOS
del tracetap-*.exe          # Windows
```

## Development Notes

### Why Different Scripts?

Each platform has different certificate management:

- **Linux:** NSS database (certutil) + optional system certs
- **macOS:** System Keychain (security command)
- **Windows:** Certificate Store (PowerShell + .NET)

### Script Features

All scripts provide:
- ✅ Install certificate
- ✅ Remove certificate  
- ✅ Show status
- ✅ Auto-generate certificate if missing
- ✅ Firefox support (optional)
- ✅ Colored output
- ✅ Error handling

### Testing the Scripts

Test in a VM or Docker container:

**Linux:**
```bash
docker run -it ubuntu:22.04 bash
# Copy script and test
```

**macOS:**
```bash
# Test on macOS VM or physical machine
```

**Windows:**
```powershell
# Test in Windows VM or physical machine
```

## Recommendations

### For End Users

**Linux users:** 
- Use the bash script (works on all distros)
- Install system-wide if you use curl/wget

**macOS users:**
- Use the bash script (simplest)
- Certificate automatically trusted system-wide

**Windows users:**
- Use PowerShell script
- Run as regular user (enough for browsers)
- Run as Admin only if you need system-wide

### For Developers

**Distributing TraceTap:**
1. Include all three scripts in releases
2. Document which script to use per platform
3. Provide troubleshooting for each platform

**Building:**
- PyInstaller creates executables for each platform
- GitHub Actions can build all three automatically
- Test on each platform before release

### For CI/CD

**Linux containers:**
```yaml
- run: |
    sudo apt-get update
    sudo apt-get install -y libnss3-tools
    ./chrome-cert-manager.sh install
```

**macOS runners:**
```yaml
- run: |
    ./macos-cert-manager.sh install
```

**Windows runners:**
```yaml
- run: |
    powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 install
```

## Summary

| Platform | Best Choice | Notes |
|----------|-------------|-------|
| **Linux** | `chrome-cert-manager.sh` | Most features, auto-installs deps |
| **macOS** | `macos-cert-manager.sh` | Simplest, uses Keychain |
| **Windows** | `windows-cert-manager.ps1` | Built-in, no deps needed |