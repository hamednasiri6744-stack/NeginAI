[CmdletBinding()]
param(
    [string]$SourceDirectory = "\\192.168.1.171\exe\VN.SDS.Container",
    [Parameter(Mandatory = $true)]
    [string]$Output
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $SourceDirectory -PathType Container)) {
    throw "Varanegar binary directory was not found."
}

$candidateFiles = @(
    Get-ChildItem -LiteralPath $SourceDirectory -File |
        Where-Object {
            $_.Extension -in @(".dll", ".exe") -and
            $_.Name -notlike "*.disable" -and
            (
                $_.Name -like "VN.SDS.*" -or
                $_.Name -like "Application.*" -or
                $_.Name -like "TreasuryOld.*" -or
                $_.Name -in @(
                    "BaseClasses.dll",
                    "VNMembers.dll",
                    "VNQueryInterface.dll",
                    "VNReportInterface.dll"
                )
            )
        } |
        Sort-Object Name
)

$files = [System.Collections.Generic.List[object]]::new()
foreach ($file in $candidateFiles) {
    $family = $file.BaseName
    $layer = "Standalone"
    if ($file.BaseName -match '^(.*)\.(Business|DataAccess|IBusiness|UI|UIComponent|Forms)(?:\.XmlSerializers)?$') {
        $family = $matches[1]
        $layer = $matches[2]
    }
    elseif ($file.BaseName -match '^(.*)\.XmlSerializers$') {
        $family = $matches[1]
        $layer = "XmlSerializers"
    }

    $version = $file.VersionInfo
    $files.Add([pscustomobject][ordered]@{
        name = $file.Name
        family = $family
        layer = $layer
        bytes = $file.Length
        last_write_time = $file.LastWriteTime.ToString("o")
        file_version = $version.FileVersion
        product_version = $version.ProductVersion
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
        disabled_pair_present = Test-Path -LiteralPath ($file.FullName + ".disable") -PathType Leaf
    })
}

$families = [System.Collections.Generic.List[object]]::new()
foreach ($group in ($files | Group-Object family | Sort-Object Name)) {
    $families.Add([pscustomobject][ordered]@{
        family = $group.Name
        file_count = $group.Count
        bytes = ($group.Group | Measure-Object bytes -Sum).Sum
        layers = @($group.Group.layer | Sort-Object -Unique)
        all_have_disabled_pair = @($group.Group | Where-Object { -not $_.disabled_pair_present }).Count -eq 0
    })
}

$artifact = [ordered]@{
    artifact = "varanegar_binary_module_inventory"
    schema_version = 1
    generated_at = [DateTimeOffset]::Now.ToString("o")
    source = [ordered]@{
        directory = $SourceDirectory
        machine_ipv4 = "192.168.1.184"
    }
    safety = [ordered]@{
        mode = "READ_ONLY_FILE_METADATA"
        config_files_read = 0
        executable_code_invoked = 0
        assemblies_loaded = 0
        credentials_persisted = 0
    }
    summary = [ordered]@{
        file_count = $files.Count
        family_count = $families.Count
        total_bytes = ($files | Measure-Object bytes -Sum).Sum
        ui_file_count = @($files | Where-Object { $_.layer -in @("UI", "Forms") }).Count
        data_access_file_count = @($files | Where-Object { $_.layer -eq "DataAccess" }).Count
        business_file_count = @($files | Where-Object { $_.layer -eq "Business" }).Count
    }
    families = $families
    files = $files
}

$outputPath = [System.IO.Path]::GetFullPath($Output)
$outputDirectory = [System.IO.Path]::GetDirectoryName($outputPath)
[System.IO.Directory]::CreateDirectory($outputDirectory) | Out-Null
$json = $artifact | ConvertTo-Json -Depth 12
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outputPath, $json, $utf8NoBom)
Write-Output $outputPath
