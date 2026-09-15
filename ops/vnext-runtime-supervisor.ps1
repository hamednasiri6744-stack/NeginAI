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
function StartBackend{
  if(!(Listening 8007)){
    Start-Process $py -WorkingDirectory $root -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8007' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $log 'backend.out.log') -RedirectStandardError (Join-Path $log 'backend.err.log')
  }
}
function StartFrontend{
  if(!(Listening 4183) -and (Test-Path (Join-Path $front 'dist\index.html'))){
    Start-Process $node -WorkingDirectory $front -ArgumentList $vite,'preview','--host','0.0.0.0','--port','4183','--strictPort' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $log 'frontend.out.log') -RedirectStandardError (Join-Path $log 'frontend.err.log')
  }
}
while($true){
  $svc=Get-Service cloudflared -ErrorAction SilentlyContinue
  if($svc -and $svc.Status -ne 'Running'){ Start-Service cloudflared }
  StartBackend
  StartFrontend
  Start-Sleep 20
}
