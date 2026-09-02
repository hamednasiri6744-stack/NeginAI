$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$monitorScript = Join-Path $PSScriptRoot 'start_public_service.ps1'
$taskName = 'NeginAI Public Service Monitor'

if (-not (Test-Path -LiteralPath $monitorScript)) {
    throw "Public service monitor script was not found: $monitorScript"
}

$powerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$action = New-ScheduledTaskAction `
    -Execute $powerShell `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$monitorScript`"" `
    -WorkingDirectory $projectRoot

$startupTrigger = New-ScheduledTaskTrigger -AtStartup
$periodicTrigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$taskSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger @($startupTrigger, $periodicTrigger) `
    -Settings $taskSettings `
    -User 'SYSTEM' `
    -RunLevel Highest `
    -Force | Out-Null

Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 2

$task = Get-ScheduledTask -TaskName $taskName
$info = Get-ScheduledTaskInfo -TaskName $taskName
$status = [pscustomobject]@{
    TaskName = $task.TaskName
    State = [string]$task.State
    RunAs = $task.Principal.UserId
    RunLevel = [string]$task.Principal.RunLevel
    LastRunTime = $info.LastRunTime
    LastTaskResult = $info.LastTaskResult
    NextRunTime = $info.NextRunTime
    TriggerCount = $task.Triggers.Count
}
$statusJson = $status | ConvertTo-Json -Compress
$statusJson | Set-Content -LiteralPath (Join-Path $env:TEMP 'neginai-public-service-task-status.json') -Encoding utf8
$statusJson
