param(
    [Parameter(Mandatory = $true)][string]$AssemblyPath,
    [Parameter(Mandatory = $true)][string]$TypePattern,
    [Parameter(Mandatory = $true)][string]$MethodName
)

$assemblyDir = Split-Path -Parent $AssemblyPath
$resolving = @{}
[System.AppDomain]::CurrentDomain.add_AssemblyResolve({
    param($sender, $eventArgs)
    $name = ([System.Reflection.AssemblyName]$eventArgs.Name).Name + '.dll'
    $candidate = Join-Path $assemblyDir $name
    if ((Test-Path -LiteralPath $candidate) -and -not $resolving.ContainsKey($candidate)) {
        $resolving[$candidate] = $true
        try {
            return [System.Reflection.Assembly]::Load([System.IO.File]::ReadAllBytes($candidate))
        } finally {
            $resolving.Remove($candidate)
        }
    }
    return $null
})

$opcodeMap = @{}
[System.Reflection.Emit.OpCodes].GetFields([System.Reflection.BindingFlags]'Public,Static') | ForEach-Object {
    $opcode = $_.GetValue($null)
    $opcodeMap[[int]$opcode.Value -band 0xffff] = $opcode
}

function Show-MethodCalls([System.Reflection.MethodBase]$method) {
    $body = $method.GetMethodBody()
    if (-not $body) { return }
    "METHOD $($method.DeclaringType.FullName).$($method.Name)"
    $bytes = $body.GetILAsByteArray()
    $position = 0
    while ($position -lt $bytes.Length) {
        $offset = $position
        $code = [int]$bytes[$position++]
        if ($code -eq 0xfe) { $code = 0xfe00 + [int]$bytes[$position++] }
        $opcode = $opcodeMap[$code]
        if (-not $opcode) { break }
        $size = 0
        $token = $null
        switch ($opcode.OperandType.ToString()) {
            'ShortInlineI' { $size = 1 }
            'ShortInlineVar' { $size = 1 }
            'ShortInlineBrTarget' { $size = 1 }
            'InlineVar' { $size = 2 }
            'InlineI' { $size = 4 }
            'InlineBrTarget' { $size = 4 }
            'ShortInlineR' { $size = 4 }
            'InlineString' { $size = 4; $token = [BitConverter]::ToInt32($bytes, $position) }
            'InlineSig' { $size = 4; $token = [BitConverter]::ToInt32($bytes, $position) }
            'InlineField' { $size = 4; $token = [BitConverter]::ToInt32($bytes, $position) }
            'InlineMethod' { $size = 4; $token = [BitConverter]::ToInt32($bytes, $position) }
            'InlineType' { $size = 4; $token = [BitConverter]::ToInt32($bytes, $position) }
            'InlineTok' { $size = 4; $token = [BitConverter]::ToInt32($bytes, $position) }
            'InlineI8' { $size = 8 }
            'InlineR' { $size = 8 }
            'InlineSwitch' {
                $count = [BitConverter]::ToInt32($bytes, $position)
                $size = 4 + (4 * $count)
            }
        }
        if ($null -ne $token) {
            try {
                if ($opcode.OperandType.ToString() -eq 'InlineString') {
                    $resolved = $method.Module.ResolveString($token)
                } else {
                    $resolved = $method.Module.ResolveMember($token)
                }
                $declaringType = if ($resolved.DeclaringType) { $resolved.DeclaringType.FullName + '::' } else { '' }
                ('  IL_{0:x4} {1} {2}{3}' -f $offset, $opcode.Name, $declaringType, $resolved)
            } catch {
                ('  IL_{0:x4} {1} token 0x{2:x8}' -f $offset, $opcode.Name, $token)
            }
        }
        $position += $size
    }
}

$assembly = [System.Reflection.Assembly]::Load([System.IO.File]::ReadAllBytes($AssemblyPath))
try {
    $allTypes = $assembly.GetTypes()
} catch [System.Reflection.ReflectionTypeLoadException] {
    $allTypes = $_.Exception.Types | Where-Object { $null -ne $_ }
    $_.Exception.LoaderExceptions | ForEach-Object {
        Write-Warning ("Loader: " + $_.Message)
    }
}
$types = $allTypes | Where-Object {
    $typeMethods = $_.GetMethods([System.Reflection.BindingFlags]'Public,NonPublic,Instance,Static')
    $hasNamedMethod = $typeMethods.Name -contains $MethodName
    $_.FullName -like $TypePattern -and ($hasNamedMethod -or $_.Name -like "*$MethodName*")
}
foreach ($type in $types) {
    $methods = $type.GetMethods([System.Reflection.BindingFlags]'Public,NonPublic,Instance,Static') | Where-Object {
        $_.Name -eq $MethodName -or ($type.Name -like "*$MethodName*" -and $_.Name -eq 'MoveNext')
    }
    foreach ($method in $methods) { Show-MethodCalls $method }
}
