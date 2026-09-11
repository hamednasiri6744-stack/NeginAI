param(
  [string]$BaseUrl = $env:NEGINAI_UI_BASE_URL
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
  $BaseUrl = 'http://127.0.0.1:8001'
}
$BaseUrl = $BaseUrl.TrimEnd('/')
$target = "$BaseUrl/assistant"
$healthUrl = "$BaseUrl/health"

try {
  $health = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 8
} catch {
  throw "NeginAI UI target is not reachable at $healthUrl."
}
if ($health.StatusCode -lt 200 -or $health.StatusCode -ge 300) {
  throw "NeginAI UI health check returned HTTP $($health.StatusCode)."
}

$lighthouse = Join-Path $root 'node_modules\.bin\lighthouse.cmd'
if (-not (Test-Path $lighthouse)) {
  throw "Lighthouse CLI not found at $lighthouse. Run npm install in the repository."
}

$outDir = Join-Path $root 'artifacts\ui\lighthouse'
New-Item -ItemType Directory -Force $outDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$outPath = Join-Path $outDir "assistant-$stamp"

Push-Location $root
try {
  & $lighthouse $target `
    '--quiet' `
    '--chrome-flags=--headless=new --no-first-run' `
    '--output=html' `
    '--output=json' `
    "--output-path=$outPath"
  exit $LASTEXITCODE
} finally {
  Pop-Location
}
