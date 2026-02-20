param(
    [int]$Port = 8000,
    [string]$HostAddress = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendRoot = Resolve-Path (Join-Path $ScriptDir "..")

Write-Host "Backend root: $BackendRoot"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is not installed or not in PATH."
}

if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
    Write-Host @"
The 'ngrok' CLI is not installed.
Install options:
1) winget install Ngrok.Ngrok
2) choco install ngrok
"@ -ForegroundColor Red
    exit 1
}

$backendProc = $null
$ngrokProc = $null

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

    Write-Host "Starting ngrok tunnel..."
    $ngrokProc = Start-Process `
        -FilePath "ngrok" `
        -ArgumentList @("http", "$Port") `
        -PassThru `
        -WindowStyle Hidden

    Start-Sleep -Seconds 3

    try {
        $tunnels = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -Method Get
        $httpsTunnel = $tunnels.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1
        if ($httpsTunnel) {
            Write-Host "ngrok public URL: $($httpsTunnel.public_url)" -ForegroundColor Green
            Write-Host "Example Vapi webhook URL: $($httpsTunnel.public_url)/api/v1/vapi/webhook" -ForegroundColor Green
        } else {
            Write-Host "ngrok tunnel started. Open http://127.0.0.1:4040 to view tunnel URL." -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "ngrok started. Could not fetch tunnel URL from local API. Open http://127.0.0.1:4040." -ForegroundColor Yellow
    }

    Write-Host "Press Ctrl+C to stop ngrok and backend."
    Wait-Process -Id $ngrokProc.Id
}
finally {
    if ($ngrokProc -and -not $ngrokProc.HasExited) {
        Write-Host "Stopping ngrok process..."
        Stop-Process -Id $ngrokProc.Id -Force
    }
    if ($backendProc -and -not $backendProc.HasExited) {
        Write-Host "Stopping backend process..."
        Stop-Process -Id $backendProc.Id -Force
    }
}
