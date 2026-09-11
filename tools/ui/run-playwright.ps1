param(
  [string]$BaseUrl = $env:NEGINAI_UI_BASE_URL,
  [switch]$Headed,
  [switch]$CrossBrowser
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
  $BaseUrl = 'http://127.0.0.1:8001'
}
$BaseUrl = $BaseUrl.TrimEnd('/')

try {
  $uri = [Uri]$BaseUrl
} catch {
  throw "Invalid NeginAI UI base URL: $BaseUrl"
}
if ($uri.Scheme -notin @('http', 'https')) {
  throw "NeginAI UI base URL must use http or https: $BaseUrl"
}

$healthUrl = "$BaseUrl/health"
try {
  $health = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 8
} catch {
  throw "NeginAI UI target is not reachable at $healthUrl. Start the local app first or set NEGINAI_UI_BASE_URL."
}
if ($health.StatusCode -lt 200 -or $health.StatusCode -ge 300) {
  throw "NeginAI UI health check returned HTTP $($health.StatusCode) at $healthUrl."
}

$playwright = Join-Path $root 'node_modules\.bin\playwright.cmd'
if (-not (Test-Path $playwright)) {
  throw "Playwright CLI not found at $playwright. Run npm install in the repository."
}

$env:NEGINAI_UI_BASE_URL = $BaseUrl
New-Item -ItemType Directory -Force (Join-Path $root 'artifacts\ui') | Out-Null

$args = @('test')
if (-not $CrossBrowser) {
  $args += '--project=desktop-chromium'
  $args += '--project=mobile-chrome'
}
if ($Headed) {
  $args += '--headed'
}

Push-Location $root
try {
  & $playwright @args
  exit $LASTEXITCODE
} finally {
  Pop-Location
}
