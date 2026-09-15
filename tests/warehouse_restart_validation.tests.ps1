$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\scripts\warehouse_restart_validation.ps1')
$serviceSid = 'S-1-5-21-1-2-3-1007'
$project = 'G:\IsolatedFixture'
$shellPath = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
function New-TestDefinition {
    $action = [pscustomobject]@{Path=$shellPath; WorkingDirectory=$project; Arguments=('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+(Join-Path $project 'scripts\start_public_service.ps1')+'"')}
    $actions = [pscustomobject]@{Count=1; Action=$action}
    $actions | Add-Member ScriptMethod Item { param($index) $this.Action }
    return [pscustomobject]@{Principal=[pscustomobject]@{UserId=$serviceSid;RunLevel=0;LogonType=1};Actions=$actions}
}
function Check-Definition($definition, $admins=@()) {
    Assert-WarehouseRestartTask -Definition $definition -ServiceSid $serviceSid -AdministratorSids $admins `
        -ComputerName 'TEST-PC' -ProjectRoot $project -PowerShellPath $shellPath
}
foreach ($user in @($serviceSid,'NeginAIService','TEST-PC\NeginAIService')) {
    $definition=New-TestDefinition; $definition.Principal.UserId=$user; Check-Definition $definition
}
foreach ($case in @('system','elevated','logon','admin-member','wrong-executable','wrong-arguments','wrong-directory','extra-action')) {
    $definition=New-TestDefinition; $admins=@()
    switch ($case) {
        'system' {$definition.Principal.UserId='S-1-5-18'}
        'elevated' {$definition.Principal.RunLevel=1}
        'logon' {$definition.Principal.LogonType=2}
        'admin-member' {$admins=@($serviceSid)}
        'wrong-executable' {$definition.Actions.Action.Path='other.exe'}
        'wrong-arguments' {$definition.Actions.Action.Arguments+=' -Unexpected'}
        'wrong-directory' {$definition.Actions.Action.WorkingDirectory='G:\Other'}
        'extra-action' {$definition.Actions.Count=2}
    }
    $rejected=$false
    try { Check-Definition $definition $admins } catch { $rejected=$true }
    if (-not $rejected) { throw "Unsafe definition accepted: $case" }
}
# Exercise access denial without touching Task Scheduler, service state or real data.
function New-Object { param($ComObject) throw [UnauthorizedAccessException]::new('Fixture access denied') }
$denied=$false
try { & (Join-Path $PSScriptRoot '..\scripts\request_warehouse_restart.ps1') -Restart }
catch { $denied=$_.Exception.Message -like '*No restart request was written*Fixture access denied*' }
finally { Remove-Item Function:\New-Object }
if (-not $denied) { throw 'Access denial did not stop the request with a clear diagnostic.' }
Write-Output 'PASS: 3 allowed identities, 8 rejected definitions, and denied access stops before restart.'
