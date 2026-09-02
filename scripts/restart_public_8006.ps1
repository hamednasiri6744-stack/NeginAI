$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$logDirectory = Join-Path $projectRoot 'logs'

# Never let an inherited pytest/scratch database override reach the public API.
# With the override removed, application settings resolve the primary database
# from the project's normal environment configuration.
Remove-Item Env:NEGINAI_SQLITE_PATH -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

$listener = Get-NetTCPConnection -LocalPort 8006 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($listener) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
    if (-not $process -or $process.Name -ne 'python.exe') {
        throw "Port 8006 is not owned by the expected Python API process."
    }
    Stop-Process -Id $listener.OwningProcess -Force
    Start-Sleep -Seconds 2
}

# A supervising parent may already have recreated the worker. Start one only
# when the verified public API port is still free.
$replacement = Get-NetTCPConnection -LocalPort 8006 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $replacement) {
    $env:METADATA_SYNC_ENABLED = 'false'
    Start-Process -FilePath $python `
        -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8006' `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDirectory 'uvicorn-8006-stdout.log') `
        -RedirectStandardError (Join-Path $logDirectory 'uvicorn-8006-stderr.log')
}

$ready = $false
for ($attempt = 0; $attempt -lt 40; $attempt += 1) {
    Start-Sleep -Milliseconds 500
    try {
        $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8006/health' -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        # Keep waiting until the bounded readiness deadline.
    }
}
if (-not $ready) {
    throw 'The public API did not become healthy on port 8006.'
}
