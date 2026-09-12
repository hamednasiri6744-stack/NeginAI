param(
    [string]$RepoPath = 'D:\Deploy\NeginAI-dev',
    [string]$Branch = 'dev/hamed',
    [int]$Port = 4182
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$VnextPath = Join-Path $RepoPath 'vnext'
$MutexName = 'NeginAI-DevDeploy-4182'
$mutex = New-Object System.Threading.Mutex($false, $MutexName)
$hasLock = $false
$pushed = $false

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory
    )

    $process = Start-Process -FilePath $FilePath `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -NoNewWindow -Wait -PassThru

    if ($process.ExitCode -ne 0) {
        throw "$FilePath failed with exit code $($process.ExitCode)."
    }
}

try {
    $hasLock = $mutex.WaitOne(0)
    if (-not $hasLock) {
        Write-Host '[skip] deployment is already running.'
        exit 0
    }

    if (-not (Test-Path (Join-Path $RepoPath '.git'))) {
        throw "Deploy clone not found: $RepoPath"
    }

    Push-Location $RepoPath
    $pushed = $true

    $dirty = @(git status --porcelain)
    if ($LASTEXITCODE -ne 0) { throw 'git status failed.' }
    if ($dirty.Count -gt 0) {
        throw 'Deploy clone is dirty. Refusing automatic deployment.'
    }

    git fetch origin $Branch
    if ($LASTEXITCODE -ne 0) { throw 'git fetch failed.' }

    $localSha = (git rev-parse HEAD).Trim()
    $remoteSha = (git rev-parse "origin/$Branch").Trim()

    if ($localSha -eq $remoteSha) {
        Write-Host "[ok] already deployed: $($localSha.Substring(0,7))"
        exit 0
    }

    git merge-base --is-ancestor $localSha $remoteSha
    if ($LASTEXITCODE -ne 0) {
        throw 'Remote branch is not a fast-forward from the deploy clone.'
    }

    $dependencyChanges = @(git diff --name-only $localSha $remoteSha -- 'vnext/package.json' 'vnext/package-lock.json')
    if ($LASTEXITCODE -ne 0) { throw 'git diff failed.' }

    git pull --ff-only origin $Branch
    if ($LASTEXITCODE -ne 0) { throw 'git pull --ff-only failed.' }

    if (($dependencyChanges.Count -gt 0) -or (-not (Test-Path (Join-Path $VnextPath 'node_modules')))) {
        Write-Host '[deploy] installing dependencies...'
        Invoke-Checked -FilePath 'npm.cmd' -Arguments @('ci','--no-audit','--no-fund') -WorkingDirectory $VnextPath
    }

    Write-Host '[deploy] building vnext...'
    Invoke-Checked -FilePath 'npm.cmd' -Arguments @('run','build') -WorkingDirectory $VnextPath

    if (-not (Test-Path (Join-Path $VnextPath 'dist\index.html'))) {
        throw 'Build completed but dist\index.html was not produced.'
    }

    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
    foreach ($listener in $listeners) {
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
        $commandLine = [string]$owner.CommandLine
        if (($owner.Name -ne 'node.exe') -or ($commandLine -notlike "*$VnextPath*") -or ($commandLine -notlike '*vite*')) {
            throw "Port $Port is owned by an unrelated process (PID $($listener.OwningProcess))."
        }
        Stop-Process -Id $listener.OwningProcess -Force
    }

    Start-Sleep -Milliseconds 700
    Write-Host "[deploy] starting preview on 127.0.0.1:$Port..."
    Start-Process -FilePath 'npm.cmd' `
        -ArgumentList @('run','preview','--','--host','127.0.0.1','--port',"$Port",'--strictPort') `
        -WorkingDirectory $VnextPath `
        -WindowStyle Hidden

    $healthy = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        try {
            $response = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port" -TimeoutSec 3
            if ($response.StatusCode -eq 200) {
                $healthy = $true
                break
            }
        } catch {
            # Retry until the health window expires.
        }
    }

    if (-not $healthy) {
        throw "New deployment failed health check on port $Port."
    }

    Write-Host "[deployed] $($remoteSha.Substring(0,7)) -> http://127.0.0.1:$Port"
}
catch {
    Write-Error "[deploy-failed] $($_.Exception.Message)"
    exit 1
}
finally {
    if ($pushed) { Pop-Location }
    if ($hasLock) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
