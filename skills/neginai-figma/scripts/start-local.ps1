$ErrorActionPreference = "Stop"
$root = "C:\code-x\agents\figma-x"
$health = "http://127.0.0.1:8784/health"

try {
  $r = Invoke-WebRequest -UseBasicParsing $health -TimeoutSec 2
  if ([int]$r.StatusCode -eq 200) {
    Write-Output "FIGMA_X_ALREADY_UP"
    exit 0
  }
} catch {}

$node = (Get-Command node.exe -ErrorAction Stop).Source
$logDir = Join-Path $root "runtime"
New-Item -ItemType Directory -Force $logDir | Out-Null

Start-Process `
  -FilePath $node `
  -ArgumentList "server/index.js" `
  -WorkingDirectory $root `
  -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $logDir "server.out.log") `
  -RedirectStandardError (Join-Path $logDir "server.err.log")

Start-Sleep -Seconds 3

try {
  $r = Invoke-WebRequest -UseBasicParsing $health -TimeoutSec 4
  Write-Output ("FIGMA_X_HTTP=" + [int]$r.StatusCode)
} catch {
  Write-Output "FIGMA_X_HTTP=DOWN"
  exit 2
}
