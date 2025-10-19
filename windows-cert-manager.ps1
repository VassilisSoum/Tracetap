# Windows Certificate Manager for mitmproxy
#
# This script installs or removes the mitmproxy CA certificate on Windows
# Works with Chrome, Edge, IE, and all Windows apps
#
# Usage:
#   powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 install
#   powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 remove
#   powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 status

param(
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet('install', 'remove', 'status', 'help')]
    [string]$Command
)

# Configuration
$CertName = "mitmproxy"
$CertPath = Join-Path $env:USERPROFILE ".mitmproxy\mitmproxy-ca-cert.pem"
$CertStore = "Cert:\CurrentUser\Root"

# Colors (Windows PowerShell 5.1+)
function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-ErrorMessage {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-WarningMessage {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Cyan
}

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Blue
    Write-Host $Message -ForegroundColor Blue
    Write-Host "==================================================" -ForegroundColor Blue
    Write-Host ""
}

# Check if running as Administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Check if certificate file exists
function Test-CertificateFile {
    if (-not (Test-Path $CertPath)) {
        Write-Warning-Custom "Certificate not found at $CertPath"
        Write-Info "Generating certificate by running mitmproxy briefly..."

        # Try TraceTap if available
        if (Test-Path ".\tracetap-windows-x64.exe") {
            Start-Process -FilePath ".\tracetap-windows-x64.exe" -ArgumentList "--listen", "8081" -NoNewWindow -PassThru | Out-Null
            Start-Sleep -Seconds 3
            Stop-Process -Name "tracetap-windows-x64" -Force -ErrorAction SilentlyContinue
        }

        # Try Python version
        if (-not (Test-Path $CertPath) -and (Test-Path "tracetap.py")) {
            Start-Process -FilePath "python" -ArgumentList "tracetap.py", "--listen", "8081" -NoNewWindow -PassThru | Out-Null
            Start-Sleep -Seconds 3
            Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
        }

        # Fallback to mitmdump
        if (-not (Test-Path $CertPath)) {
            try {
                Start-Process -FilePath "mitmdump" -ArgumentList "-p", "8081" -NoNewWindow -PassThru | Out-Null
                Start-Sleep -Seconds 3
                Stop-Process -Name "mitmdump" -Force -ErrorAction SilentlyContinue
            } catch {
                # Ignore errors
            }
        }

        if (-not (Test-Path $CertPath)) {
            Write-Error-Custom "Failed to generate certificate"
            Write-Info "Try running: mitmdump -p 8081"
            Write-Info "Then press Ctrl+C after a few seconds"
            exit 1
        }
    }
    Write-Success "Certificate found: $CertPath"
}

# Convert PEM to CER format
function Convert-PemToCer {
    param([string]$PemPath, [string]$CerPath)

    # Read PEM file and convert to X509Certificate2
    $pemContent = Get-Content $PemPath -Raw
    $pemBytes = [System.Text.Encoding]::ASCII.GetBytes($pemContent)

    # Remove PEM headers and decode base64
    $base64 = $pemContent -replace '-----BEGIN CERTIFICATE-----', '' `
                          -replace '-----END CERTIFICATE-----', '' `
                          -replace '\s', ''

    $certBytes = [Convert]::FromBase64String($base64)

    # Write to CER file
    [System.IO.File]::WriteAllBytes($CerPath, $certBytes)

    return $CerPath
}

# Install certificate
function Install-Certificate {
    Write-Header "Installing mitmproxy Certificate for Windows"

    # Check for admin rights
    if (-not (Test-Administrator)) {
        Write-WarningMessage "Not running as Administrator"
        Write-Info "Installing for current user only (Chrome, Edge, IE)"
        Write-Info "For system-wide installation, run as Administrator"
        Write-Host ""
    }

    Test-CertificateFile

    Write-Host ""
    Write-Info "Installing certificate in Windows Certificate Store..."

    try {
        # Convert PEM to CER
        $cerPath = Join-Path $env:TEMP "mitmproxy-ca-cert.cer"
        Convert-PemToCer -PemPath $CertPath -CerPath $cerPath

        # Load certificate
        $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($cerPath)

        # Remove old certificate if exists
        Get-ChildItem $CertStore | Where-Object { $_.Subject -like "*$CertName*" } | ForEach-Object {
            Write-Info "Removing existing certificate..."
            Remove-Item -Path "$CertStore\$($_.Thumbprint)" -Force
        }

        # Install certificate
        $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
        $store.Open("ReadWrite")
        $store.Add($cert)
        $store.Close()

        Write-Success "Certificate installed in Windows Certificate Store"

        # Clean up
        Remove-Item $cerPath -Force -ErrorAction SilentlyContinue

    } catch {
        Write-Error-Custom "Failed to install certificate: $_"
        exit 1
    }

    # Install for Firefox if it exists
    Write-Host ""
    $firefoxPath = Join-Path $env:APPDATA "Mozilla\Firefox\Profiles"
    if (Test-Path $firefoxPath) {
        $response = Read-Host "Install certificate for Firefox too? (y/N)"
        if ($response -eq 'y' -or $response -eq 'Y') {
            # Check for certutil
            $certutil = Get-Command certutil -ErrorAction SilentlyContinue
            if ($certutil) {
                Get-ChildItem $firefoxPath -Filter "*.default*" -Directory | ForEach-Object {
                    Write-Info "Installing for Firefox profile: $($_.Name)"
                    & certutil -A -d $_.FullName -t "C,," -n $CertName -i $CertPath 2>$null
                }
                Write-Success "Firefox certificate installed"
            } else {
                Write-Warning-Custom "certutil not found - skipping Firefox"
                Write-Info "Download NSS tools from: https://firefox-source-docs.mozilla.org/security/nss/tools/certutil.html"
            }
        }
    }

    # Verify installation
    Write-Host ""
    Write-Info "Verifying installation..."
    $installedCert = Get-ChildItem $CertStore | Where-Object { $_.Subject -like "*$CertName*" }

    if ($installedCert) {
        Write-Success "Certificate verified in Certificate Store"

        Write-Host ""
        Write-Host "Certificate details:" -ForegroundColor Cyan
        Write-Host "  Subject:    $($installedCert.Subject)"
        Write-Host "  Issuer:     $($installedCert.Issuer)"
        Write-Host "  Not Before: $($installedCert.NotBefore)"
        Write-Host "  Not After:  $($installedCert.NotAfter)"
        Write-Host "  Thumbprint: $($installedCert.Thumbprint)"
    } else {
        Write-Error-Custom "Certificate not found in Certificate Store"
        exit 1
    }

    Write-Header "Installation Complete!"

    Write-Host "The certificate is now trusted by:"
    Write-Host "  ✓ Chrome"
    Write-Host "  ✓ Edge"
    Write-Host "  ✓ Internet Explorer"
    Write-Host "  ✓ All Windows applications"
    if (Test-Path $firefoxPath) {
        Write-Host "  ✓ Firefox (if installed)"
    }
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  1. Close and reopen all browsers" -ForegroundColor Green
    Write-Host "  2. Start TraceTap:    tracetap-windows-x64.exe --listen 8080" -ForegroundColor Green
    Write-Host "  3. Configure proxy (use FoxyProxy extension)" -ForegroundColor Green
    Write-Host "  4. Browse HTTPS sites - no certificate warnings!" -ForegroundColor Green
    Write-Host ""
}

# Remove certificate
function Remove-Certificate {
    Write-Header "Removing mitmproxy Certificate"

    Write-Host ""
    Write-Info "Removing certificate from Windows Certificate Store..."

    try {
        $removed = $false
        Get-ChildItem $CertStore | Where-Object { $_.Subject -like "*$CertName*" } | ForEach-Object {
            Remove-Item -Path "$CertStore\$($_.Thumbprint)" -Force
            Write-Success "Certificate removed from Certificate Store"
            $removed = $true
        }

        if (-not $removed) {
            Write-Warning-Custom "Certificate not found in Certificate Store"
        }

    } catch {
        Write-Error-Custom "Failed to remove certificate: $_"
        exit 1
    }

    # Remove from Firefox
    Write-Host ""
    $firefoxPath = Join-Path $env:APPDATA "Mozilla\Firefox\Profiles"
    if (Test-Path $firefoxPath) {
        $response = Read-Host "Remove certificate from Firefox too? (y/N)"
        if ($response -eq 'y' -or $response -eq 'Y') {
            $certutil = Get-Command certutil -ErrorAction SilentlyContinue
            if ($certutil) {
                Get-ChildItem $firefoxPath -Filter "*.default*" -Directory | ForEach-Object {
                    & certutil -D -d $_.FullName -n $CertName 2>$null
                    Write-Info "Removed from Firefox profile: $($_.Name)"
                }
                Write-Success "Firefox certificate removed"
            }
        }
    }

    # Verify removal
    Write-Host ""
    Write-Info "Verifying removal..."
    $remainingCert = Get-ChildItem $CertStore | Where-Object { $_.Subject -like "*$CertName*" }

    if ($remainingCert) {
        Write-Error-Custom "Certificate still found in Certificate Store"
        exit 1
    } else {
        Write-Success "Certificate successfully removed"
    }

    Write-Header "Removal Complete!"
    Write-Host "Close and reopen all browsers for changes to take effect."
    Write-Host ""
}

# Show status
function Show-Status {
    Write-Header "Certificate Status"

    # Check certificate file
    if (Test-Path $CertPath) {
        Write-Success "Certificate file exists: $CertPath"

        # Show certificate info using OpenSSL if available
        $openssl = Get-Command openssl -ErrorAction SilentlyContinue
        if ($openssl) {
            Write-Host ""
            Write-Host "Certificate details:" -ForegroundColor Cyan
            & openssl x509 -in $CertPath -noout -subject -issuer -dates 2>$null
        }
    } else {
        Write-Error-Custom "Certificate file not found: $CertPath"
        Write-Info "Run TraceTap or mitmdump once to generate it"
    }

    # Check Windows Certificate Store
    Write-Host ""
    $installedCert = Get-ChildItem $CertStore | Where-Object { $_.Subject -like "*$CertName*" }

    if ($installedCert) {
        Write-Success "Certificate installed in Windows Certificate Store"
        Write-Info "Trusted by Chrome, Edge, IE, and all Windows apps"

        Write-Host ""
        Write-Host "Certificate Store info:" -ForegroundColor Cyan
        Write-Host "  Subject:    $($installedCert.Subject)"
        Write-Host "  Issuer:     $($installedCert.Issuer)"
        Write-Host "  Not Before: $($installedCert.NotBefore)"
        Write-Host "  Not After:  $($installedCert.NotAfter)"
        Write-Host "  Thumbprint: $($installedCert.Thumbprint)"
    } else {
        Write-Error-Custom "Certificate NOT installed in Certificate Store"
    }

    # Check Firefox
    Write-Host ""
    $firefoxPath = Join-Path $env:APPDATA "Mozilla\Firefox\Profiles"
    if (Test-Path $firefoxPath) {
        $certutil = Get-Command certutil -ErrorAction SilentlyContinue
        if ($certutil) {
            $firefoxInstalled = $false
            Get-ChildItem $firefoxPath -Filter "*.default*" -Directory | ForEach-Object {
                $result = & certutil -L -d $_.FullName 2>$null | Select-String $CertName
                if ($result) {
                    $firefoxInstalled = $true
                }
            }

            if ($firefoxInstalled) {
                Write-Success "Certificate installed in Firefox"
            } else {
                Write-Info "Certificate not installed in Firefox"
            }
        } else {
            Write-Info "certutil not found - cannot check Firefox status"
        }
    }

    # Check if proxy is running
    Write-Host ""
    $proxyRunning = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
    if ($proxyRunning) {
        Write-Success "Proxy detected on port 8080"
    } else {
        Write-Info "No proxy running on port 8080"
    }

    Write-Host ""
}

# Show usage
function Show-Usage {
    Write-Host @"
Usage: .\windows-cert-manager.ps1 [COMMAND]

Commands:
    install     Install mitmproxy certificate in Windows Certificate Store
    remove      Remove mitmproxy certificate from Certificate Store
    status      Show certificate installation status
    help        Show this help message

Examples:
    # First-time setup
    powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 install

    # Check if certificate is installed
    powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 status

    # Remove certificate
    powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 remove

Notes:
    - Works with Chrome, Edge, IE, and all Windows apps
    - Firefox support requires certutil from NSS tools
    - Certificate file: $CertPath
    - Certificate Store: $CertStore
    - Close and reopen browsers after install/remove
    - Run as Administrator for system-wide installation

"@
}

# Main script execution
switch ($Command) {
    'install' { Install-Certificate }
    'remove'  { Remove-Certificate }
    'status'  { Show-Status }
    'help'    { Show-Usage }
    default   {
        Write-Error-Custom "Invalid command: $Command"
        Write-Host ""
        Show-Usage
        exit 1
    }
}