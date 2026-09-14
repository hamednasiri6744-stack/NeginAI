param(
  [string]$Repo = 'D:\Projects\NeginAI',
  [int]$StableSeconds = 10,
  [int]$IdleSeconds = 5,
  [switch]$Once,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$LogDir = Join-Path $env:LOCALAPPDATA 'NeginAI'
$LogFile = Join-Path $LogDir 'git-autosync.log'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

function Write-Log([string]$Message) {
  $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
  Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
}

function Test-BlockedPath([string]$Path) {
  $normalized = $Path.Replace('\', '/')
  $leaf = Split-Path -Leaf $normalized

  if ($leaf -match '^\.env($|\.)') { return $true }
  if ($leaf -match '\.(pem|key|pfx|p12|jks|keystore)$') { return $true }
  if ($leaf -match '^(credentials?|secrets?|tokens?)(\.|$)') { return $true }
  if ($leaf -match '^(\.npmrc|\.pypirc|\.netrc)$') { return $true }
  if ($normalized -match '(^|/)\.cloudflared/') { return $true }
  if ($normalized -match '(^|/)data/.*\.(db|db-sh]|db-wal)$') { return $true }
  if ($normalized -match 'localhost-run-key') { return $true }

  return $false
}

$mutex = New-Object System.Threading.Mutex($false, 'Local\NeginAI-GitAutoSync')
if (-not $mutex.WaitOne(0)) {
  Write-Log 'Another autosync instance is already running.'
  exit 0
}

try {
  if (-not (Test-Path (Join-Path $Repo '.git'))) {
    Write-Log "Repository not found: $Repo"
    exit 2
  }

  Set-Location $Repo
  $originUrl = (& git remote get-url origin 2>$null | Out-String).Trim()
  if ($LASTEXITCODE -ne 0 -or $originUrl -notmatch 'github\.com') {
    Write-Log "Origin is not a GitHub remote. Sync disabled. origin=$originUrl"
    exit 3
  }

  Write-Log "Autosync started. repo=$Repo origin=$originUrl dryRun=$DryRun"

  while ($true) {
    try {
      Set-Location $Repo
      $branch = (& git branch --show-current | Out-String).Trim()
      if (-not $branch) {
        Write-Log 'Detached HEAD detected; skipping.'
        if ($Once) { break }
        Start-Sleep -Seconds $IdleSeconds
        continue
      }

      $dirty = @(& git status --porcelain=v1 --untracked-files=all)
      if (-not $dirty) {
        if ($Once) { break }
        Start-Sleep -Seconds $IdleSeconds
        continue
      }

      $signature = $dirty -join "`n"
      Start-Sleep -Seconds $StableSeconds
      $dirtyAfter = @(& git status --porcelain=v1 --untracked-files=all)
      if (($dirtyAfter -join "`n") -ne $signature) {
        if ($Once) { Write-Log 'Changes are still moving; dry cycle ended.'; break }
        continue
      }

      if ($DryRun) {
        Write-Log "Dry run: stable changes detected on branch=$branch count=$($dirtyAfter.Count)"
        if ($Once) { break }
        Start-Sleep -Seconds $IdleSeconds
        continue
      }

      & git add -A -- .
      if ($LASTEXITCODE -ne 0) {
        Write-Log 'git add failed.'
        if ($Once) { break }
        Start-Sleep -Seconds 15
        continue
      }

      $staged = @(& git diff --cached --name-only --diff-filter=ACMR)
      $blocked = @($staged | Where-Object { Test-BlockedPath $_ })
      if ($blocked.Count -gt 0) {
        & git reset --quiet HEAD -- . 2>$null
        Write-Log ("BLOCKED sensitive path(s): " + ($blocked -join ', '))
        if ($Once) { break }
        Start-Sleep -Seconds 30
        continue
      }

      if ($staged.Count -eq 0) {
        if ($Once) { break }
        Start-Sleep -Seconds $IdleSeconds
        continue
      }

      $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
      & git commit -m "chore(autosync): $stamp"
      if ($LASTEXITCODE -ne 0) {
        Write-Log 'git commit failed.'
        if ($Once) { break }
        Start-Sleep -Seconds 15
        continue
      }

      & git fetch origin $branch 2>$null
      if ($LASTEXITCODE -eq 0) {
        & git show-ref --verify --quiet "refs/remotes/origin/$branch"
        if ($LASTEXITCODE -eq 0) {
          $counts = ((& git rev-list --left-right --count "origin/$branch...HEAD") | Out-String).Trim() -split '\s+h'
          if ($counts.Count -ge 2) {
            $behind = [int]$counts[0]
            if ($behind -gt 0) {
              & git pull --rebase origin $branch
              if ($LASTEXITCODE -ne 0) {
                & git rebase --abort 2>$null
                Write-Log "Rebase conflict on branch=$branch; push skipped."
                if ($Once) { break }
                Start-Sleep -Seconds 30
                continue
              }
            }
          }
        }
      }

      & git push -u origin "HEAD:$branch"
      if ($LASTEXITCODE -eq 0) {
        $head = ((& git rev-parse --short HEAD) | Out-String).Trim()
        Write-Log "Synced branch=$branch head=$head files=$($staged.Count)"
      } else {
        Write-Log "Push failed on branch=$branch; will retry."
      }
    }
    catch {
      Write-Log ("ERROR: " + $_.Exception.Message)
    }

    if ($Once) { break }
   Start-Sleep -Seconds $IdleSeconds
  }
}
finally {
  try { $mutex.ReleaseMutex() } catch {}
  $mutex.Dispose()
}
