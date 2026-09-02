param(
    [string]$ClientDirectory = 'C:\clientnew',
    [string]$AssemblyName = 'NGT.ViewModels.dll',
    [string]$TypePattern = 'Customer(Update|Location|New)|SyncGetTour',
    [string]$ExactTypeName = '',
    [switch]$IncludeMethods
)

[System.AppDomain]::CurrentDomain.add_ReflectionOnlyAssemblyResolve({
    param($sender, $eventArgs)
    $assemblyName = ([System.Reflection.AssemblyName]$eventArgs.Name).Name + '.dll'
    $candidate = Join-Path $ClientDirectory $assemblyName
    if (Test-Path -LiteralPath $candidate) {
        return [System.Reflection.Assembly]::ReflectionOnlyLoadFrom($candidate)
    }
    try {
        return [System.Reflection.Assembly]::ReflectionOnlyLoad($eventArgs.Name)
    } catch {
        return $null
    }
})

$assembly = [System.Reflection.Assembly]::ReflectionOnlyLoadFrom((Join-Path $ClientDirectory $AssemblyName))
try {
    $types = $assembly.GetTypes()
} catch [System.Reflection.ReflectionTypeLoadException] {
    $types = $_.Exception.Types | Where-Object { $null -ne $_ }
    $_.Exception.LoaderExceptions | ForEach-Object { Write-Warning $_.Message }
}

$types |
    Where-Object { (-not $ExactTypeName -and $_.FullName -match $TypePattern) -or ($ExactTypeName -and $_.FullName -eq $ExactTypeName) } |
    Sort-Object FullName |
    ForEach-Object {
        "TYPE $($_.FullName)"
        $_.GetProperties() | ForEach-Object {
            "  $($_.PropertyType.FullName) $($_.Name)"
        }
        if ($IncludeMethods) {
            $_.GetMethods([System.Reflection.BindingFlags]'Public,NonPublic,Instance,Static,DeclaredOnly') |
                Sort-Object Name |
                ForEach-Object {
                    $parameters = ($_.GetParameters() | ForEach-Object { "$($_.ParameterType.FullName) $($_.Name)" }) -join ', '
                    "  METHOD $($_.ReturnType.FullName) $($_.Name)($parameters)"
                }
        }
    }
