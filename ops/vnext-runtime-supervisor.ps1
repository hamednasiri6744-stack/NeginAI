$ErrorActionPreference='SilentlyContinue'
$root='D:\Projects\NeginAI'
$front=Join-Path $root 'vnext'
$py=Join-Path $root '.venv\Scripts\python.exe'
$node='C:\Program Files\nodejs\node.exe'
$vite=Join-Path $front 'node_modules\vite\bin\vite.js'
$backendPort=8011
$tunnelConfig='C:\Users\Sys\.cloudflared\neginai-vnext.yml'
$cloudflared=Join-Path $env:LOCALAPPDATA 'NeginAI\cloudflared\cloudflared.exe'
$tunnelPattern=[regex]::Escape($tunnelConfig)
$log=Join-Path $root 'logs\vnext-runtime'
New-Item -ItemType Directory -Force $log | Out-Null

function Listening($port){
  return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}
function BackendProcesses{
  @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -eq 'python.exe' -and
    $_.CommandLine -match 'uvicorn app\.main:app' -and
    $_.CommandLine -match '--port 8011'
  })
}
function VnextTunnelProcesses{
  @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -eq 'cloudflared.exe' -and
    $_.CommandLine -match $tunnelPattern
  })
}
function BackendHealthy{
  if(!(Listening $backendPort)){ return $false }
  try {
    $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 4 "http://127.0.0.1:$backendPort/health"
    return $r.StatusCode -eq 200
  } catch {
    return $false
  }
}
function StartBackend{
  if(Listening $backendPort){ return }
  $existing=@(BackendProcesses)
  if($existing.Count -gt 0){ return }
  Start-Process $py -WorkingDirectory $root -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$backendPort",'--log-level','warning' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $log 'backend.out.log') -RedirectStandardError (Join-Path $log 'backend.err.log')
}
function StartFrontend{
  if(!(Listening 4183) -and (Test-Path (Join-Path $front 'dist\index.html'))){
    Start-Process $node -WorkingDirectory $front -ArgumentList $vite,'preview','--host','0.0.0.0','--port','4183','--strictPort' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $log 'frontend.out.log') -RedirectStandardError (Join-Path $log 'frontend.err.log')
  }
}
function StartVnextTunnel{
  if(!(Test-Path $cloudflared)){ return }
  if(@(VnextTunnelProcesses).Count -gt 0){ return }
  Start-Process $cloudflared -ArgumentList '--config',$tunnelConfig,'tunnel','run' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $log 'tunnel.out.log') -RedirectStandardError (Join-Path $log 'tunnel.err.log')
}

$backendFailures=0
while($true){
  # Keep the separate Cloudflared Windows service alive for the other HAgents tunnel.
  $svc=Get-Service cloudflared -ErrorAction SilentlyContinue
  if($svc -and $svc.Status -ne 'Running'){ Start-Service cloudflared }

  StartVnextTunnel

  if(BackendHealthy){
    $backendFailures=0
  } else {
    $backendFailures++
    if($backendFailures -ge 3){
      @(BackendProcesses) | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
      $backendFailures=0
      Start-Sleep 1
    }
    StartBackend
  }

  StartFrontend
  Start-Sleep 20
}
