$ErrorActionPreference='SilentlyContinue'
Start-Sleep -Seconds 15

$root='D:\Projects\NeginAI'
$tunnelConfig='C:\Users\Sys\.cloudflared\neginai-vnext.yml'
$cloudflared=Join-Path $env:LOCALAPPDATA 'NeginAI\cloudflared\cloudflared.exe'
$tunnelPattern=[regex]::Escape($tunnelConfig)
$log=Join-Path $root 'logs\vnext-runtime'
New-Item -ItemType Directory -Force $log | Out-Null

$existing=@(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
  $_.Name -eq 'cloudflared.exe' -and
  $_.CommandLine -match $tunnelPattern
})
if($existing.Count -eq 0 -and (Test-Path $cloudflared)){
  Start-Process $cloudflared -ArgumentList '--config',$tunnelConfig,'tunnel','run' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $log 'tunnel-fallback.out.log') -RedirectStandardError (Join-Path $log 'tunnel-fallback.err.log')
}
