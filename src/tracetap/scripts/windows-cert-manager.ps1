# Windows Certificate Manager for mitmproxy (Wrapper Script)
#
# This is a thin wrapper around the new Python-based certificate installer.
# Maintains backwards compatibility with the old script interface.
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

# Find the Python certificate manager
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CertManager = Join-Path $ScriptDir "cert_manager.py"

# Check if Python 3 is available
$pythonCmd = $null
foreach ($cmd in @('python3', 'python', 'py')) {
    try {
        $version = & $cmd --version 2>&1
        if ($version -match 'Python 3') {
            $pythonCmd = $cmd
            break
        }
    } catch {
        # Command not found, try next
    }
}

if (-not $pythonCmd) {
    Write-Host "❌ Python 3 is required but not found" -ForegroundColor Red
    Write-Host "   Install Python 3 from https://www.python.org and try again"
    exit 1
}

# Check if cert_manager.py exists
if (-not (Test-Path $CertManager)) {
    Write-Host "❌ Certificate manager not found: $CertManager" -ForegroundColor Red
    Write-Host "   Please ensure TraceTap is properly installed"
    exit 1
}

function Show-Usage {
    @"

Usage: .\windows-cert-manager.ps1 [COMMAND]

Commands:
    install     Install mitmproxy certificate to Windows trust store
    remove      Remove mitmproxy certificate from trust store
    status      Show certificate installation status
    help        Show this help message

Examples:
    # First-time setup (run in elevated PowerShell if needed)
    powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 install

    # Check if certificate is installed
    powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 status

    # Remove certificate
    powershell -ExecutionPolicy Bypass .\windows-cert-manager.ps1 remove

Notes:
    - Installs to Current User trust store (no admin required)
    - For system-wide trust, run PowerShell as Administrator
    - Certificate file: %USERPROFILE%\.mitmproxy\mitmproxy-ca-cert.pem
    - Close and reopen browsers after install/remove

For detailed documentation:
    docs\CERTIFICATE_INSTALLATION.md
    docs\TROUBLESHOOTING.md

"@
}

switch ($Command) {
    'install' {
        & $pythonCmd $CertManager install
        exit $LASTEXITCODE
    }
    'remove' {
        & $pythonCmd $CertManager uninstall
        exit $LASTEXITCODE
    }
    'status' {
        Write-Host "Certificate Installation Status" -ForegroundColor Cyan
        Write-Host "================================" -ForegroundColor Cyan
        Write-Host ""
        & $pythonCmd $CertManager info
        Write-Host ""
        Write-Host "Verification:" -ForegroundColor Cyan
        & $pythonCmd $CertManager verify
        exit $LASTEXITCODE
    }
    'help' {
        Show-Usage
        exit 0
    }
}
