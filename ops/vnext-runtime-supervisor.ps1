$ErrorActionPreference='SilentlyContinue'
$root='D:\Projects\NeginAI'
$front=Join-Path $root 'vnext'
$py=Join-Path $root '.vent\Scripts\python.exe'
$node='C:\Program Files\nodejs\node.exe'
$vite=Join-Path $front 'node_modules\vite\bin\vite.js'
$log=Join-Path $root 'logs\vnext-runtime'
New-Item -ItemType Directory -Force $log | Out-Null

function Listening($port){
  return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}
function BackendProcesses{
  @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -eq 'python.exe' -and
    $_.CommandLine -match 'uvicorn app\.main:app' -and
    $_.CommandLine -match '--port 8007'
  })
}
function BackendHealthy{
  if(!(Listening 8007)){ return $false }
  try {
    $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 4 'http://127.0.0.1:8007/health'
    return $r.StatusCode -eq 200
  } catch {
    return $false
  }
}
function StartBackend{
  if(Listening 8007){ return }
  $existing=@(BackendProcesses)
  if($existing.Count -gt 0){ return }
  Start-Process $py -WorkingDirectory $root -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8007' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $log 'backend.out.log') -RedirectStandardError (Join-Path $log 'backend.err.log')
}
function StartFrontend{
  if(!(Listening 4183) -and (Test-Path (Join-Path $front 'dist\index.html'))){
    Start-Process $node -WorkingDirectory $front -ArgumentList $vite,'preview','--host','0.0.0.0','--port','4183','--strictPort' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $log 'frontend.out.log') -RedirectStandardError (Join-Path $log 'frontend.err.log')
  }
}

$backendFailures=0
while($true){
  $svc=Get-Service cloudflared -ErrorAction SilentlyContinue
  if($svc -and $svc.Status -ne 'Running'){ Start-Service cloudflared }

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
