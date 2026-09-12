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

function Test-DevHealth {
    param([int]$HealthPort)
    try {
        $response = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$HealthPort" -TimeoutSec 3
        return ($response.StatusCode -eq 200)
    }
    catch {
        return $false
    }
}

function Stop-OwnedPreview {
    param([int]$PreviewPort)

    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $PreviewPort -ErrorAction SilentlyContinue)
    foreach ($listener in $listeners) {
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
        $commandLine = [string]$owner.CommandLine
        if (($owner.Name -ne 'node.exe') -or ($commandLine -notlike "*$VnextPath*") -or ($commandLine -notlike '*vite*')) {
            throw "Port $PreviewPort is owned by an unrelated process (PID $($listener.OwningProcess))."
        }
        Stop-Process -Id $listener.OwningProcess -Force
    }
}

function Start-PreviewAndWait {
    param([int]$PreviewPort)

    Stop-OwnedPreview -PreviewPort $PreviewPort
    Start-Sleep -Milliseconds 700

    Write-Host "[deploy] starting preview on 127.0.0.1:$PreviewPort..."
    Start-Process -FilePath 'npm.cmd' `
        -ArgumentList @('run','preview','--','--host','127.0.0.1','--port',"$PreviewPort",'--strictPort') `
        -WorkingDirectory $VnextPath `
        -WindowStyle Hidden

    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        if (Test-DevHealth -HealthPort $PreviewPort) {
            return
        }
    }

    throw "Deployment failed health check on port $PreviewPort."
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
    $shaChanged = ($localSha -ne $remoteSha)

    if ($shaChanged) {
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
    }
    elseif (Test-DevHealth -HealthPort $Port) {
        Write-Host "[ok] already deployed and healthy: $($localSha.Substring(0,7))"
        exit 0
    }
    else {
        Write-Host "[recover] SHA unchanged but port $Port is unhealthy. Restoring preview."

        if (-not (Test-Path (Join-Path $VnextPath 'node_modules'))) {
            Write-Host '[recover] installing dependencies...'
            Invoke-Checked -FilePath 'npm.cmd' -Arguments @('ci','--no-audit','--no-fund') -WorkingDirectory $VnextPath
        }

        if (-not (Test-Path (Join-Path $VnextPath 'dist\index.html'))) {
            Write-Host '[recover] build artifact missing; rebuilding...'
            Invoke-Checked -FilePath 'npm.cmd' -Arguments @('run','build') -WorkingDirectory $VnextPath
        }
    }

    if (-not (Test-Path (Join-Path $VnextPath 'dist\index.html'))) {
        throw 'dist\index.html is missing.'
    }

    Start-PreviewAndWait -PreviewPort $Port
    $deployedSha = (git rev-parse HEAD).Trim()
    Write-Host "[deployed] $($deployedSha.Substring(0,7)) -> http://127.0.0.1:$Port"
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
