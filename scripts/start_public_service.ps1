$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$caddy = Join-Path $projectRoot 'tools\caddy.exe'
$logDirectory = Join-Path $projectRoot 'logs'

New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

function Test-ListeningPort([int]$Port) {
    return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -First 1)
}

if (-not (Test-ListeningPort 8006)) {
    # Port 8006 is the active blue/green worker. Older privileged workers may
    # remain alive until Windows restarts, so only one process may own sync.
    $env:METADATA_SYNC_ENABLED = if ((Test-ListeningPort 8000) -or (Test-ListeningPort 8001) -or (Test-ListeningPort 8002) -or (Test-ListeningPort 8003) -or (Test-ListeningPort 8004) -or (Test-ListeningPort 8005)) { 'false' } else { 'true' }
    Start-Process -FilePath $python `
        -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8006' `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDirectory 'uvicorn-8006-stdout.log') `
        -RedirectStandardError (Join-Path $logDirectory 'uvicorn-8006-stderr.log')
}

if (-not (Test-ListeningPort 443)) {
    Start-Process -FilePath $caddy `
        -ArgumentList 'run', '--config', 'Caddyfile', '--adapter', 'caddyfile' `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDirectory 'caddy-stdout.log') `
        -RedirectStandardError (Join-Path $logDirectory 'caddy-stderr.log')
}
