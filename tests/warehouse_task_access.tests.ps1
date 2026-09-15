$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\scripts\warehouse_task_access.ps1')
$sid = 'S-1-5-21-1-2-3-1001'
$source = 'O:SYG:SYD:(A;;FA;;;SY)(A;;FA;;;BA)'
$result = Add-WarehouseTaskOperatorAccess -Sddl $source -OperatorSid $sid
$descriptor = [Security.AccessControl.RawSecurityDescriptor]::new($result)
if ($descriptor.Owner.Value -ne 'S-1-5-18' -or $descriptor.DiscretionaryAcl.Count -ne 3) { throw 'Existing owner/ACL changed' }
$entry = $descriptor.DiscretionaryAcl[2]
if ($entry.SecurityIdentifier.Value -ne $sid -or $entry.AccessMask -ne 0x1200a9) { throw 'Wrong operator scope or rights' }
if ((Add-WarehouseTaskOperatorAccess -Sddl $result -OperatorSid $sid) -ne $result) { throw 'Not idempotent' }
if ($descriptor.DiscretionaryAcl[0].AccessMask -ne 0x1f01ff -or $descriptor.DiscretionaryAcl[1].AccessMask -ne 0x1f01ff) { throw 'Existing administrator/System access lost' }
foreach ($name in @('enable_warehouse_restart_control.ps1','request_warehouse_restart.ps1')) {
    $parseErrors=$null; $tokens=$null
    $null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot "..\scripts\$name"),[ref]$tokens,[ref]$parseErrors)
    if ($parseErrors.Count) { throw $parseErrors[0] }
}
Write-Output 'PASS: exact read/run rights; original owner/System/admin access preserved; idempotent; scripts parse.'
