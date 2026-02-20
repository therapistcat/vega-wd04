param(
    [int]$Port = 8000,
    [string]$HostAddress = "127.0.0.1",
    [switch]$AllowAnonymous = $true
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendRoot = Resolve-Path (Join-Path $ScriptDir "..")

Write-Host "Backend root: $BackendRoot"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is not installed or not in PATH."
}

if (-not (Get-Command devtunnel -ErrorAction SilentlyContinue)) {
    Write-Host @"
The 'devtunnel' CLI is not installed.
Install options:
1) winget install Microsoft.devtunnel
2) dotnet tool install -g Microsoft.DevTunnels.Cli
"@ -ForegroundColor Red
    exit 1
}

$backendProc = $null

try {
    $backendArgs = @(
        "-m", "uvicorn", "app.main:app",
        "--host", $HostAddress,
        "--port", "$Port",
        "--reload"
    )

    Write-Host "Starting FastAPI backend on http://$HostAddress`:$Port ..."
    $backendProc = Start-Process `
        -FilePath "python" `
        -ArgumentList $backendArgs `
        -WorkingDirectory "$BackendRoot" `
        -PassThru `
        -NoNewWindow

    Start-Sleep -Seconds 2
    if ($backendProc.HasExited) {
        throw "Backend process exited early. Check Python/FastAPI errors."
    }

    $devTunnelArgs = @("host", "-p", "$Port")
    if ($AllowAnonymous) {
        $devTunnelArgs += "--allow-anonymous"
    }

    Write-Host "Starting Dev Tunnel (this will print your public URL)..."
    Write-Host "Press Ctrl+C to stop tunnel and backend."
    & devtunnel @devTunnelArgs
}
finally {
    if ($backendProc -and -not $backendProc.HasExited) {
        Write-Host "Stopping backend process..."
        Stop-Process -Id $backendProc.Id -Force
    }
}
