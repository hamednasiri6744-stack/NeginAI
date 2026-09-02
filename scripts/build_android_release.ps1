param(
    [string]$ProjectDir = (Join-Path $PSScriptRoot "..\android\SellerNavigator"),
    [string]$OutputDir = (Join-Path $PSScriptRoot "..\dist\android")
)

$ErrorActionPreference = "Stop"
$propertiesPath = Join-Path $ProjectDir "keystore.properties"
if (-not (Test-Path -LiteralPath $propertiesPath)) {
    & (Join-Path $PSScriptRoot "setup_android_signing.ps1") -ProjectDir $ProjectDir
}

Push-Location $ProjectDir
try {
    & .\gradlew.bat assembleRelease
    if ($LASTEXITCODE -ne 0) { throw "Android release build failed." }
} finally {
    Pop-Location
}

$sourceApk = Join-Path $ProjectDir "app\build\outputs\apk\release\app-release.apk"
$outputMetadata = Join-Path $ProjectDir "app\build\outputs\apk\release\output-metadata.json"
if (-not (Test-Path -LiteralPath $sourceApk)) { throw "Signed release APK was not produced." }

$buildMetadata = Get-Content -LiteralPath $outputMetadata -Raw | ConvertFrom-Json
$versionCode = [int]$buildMetadata.elements[0].versionCode
$versionName = [string]$buildMetadata.elements[0].versionName
$releaseNotesPath = Join-Path $PSScriptRoot "android_release_notes_fa.txt"
$releaseNotes = (Get-Content -LiteralPath $releaseNotesPath -Raw -Encoding UTF8).Trim()
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$fileName = "NeginAI-$versionName.apk"
$targetApk = Join-Path $OutputDir $fileName
Copy-Item -LiteralPath $sourceApk -Destination $targetApk -Force

$file = Get-Item -LiteralPath $targetApk
$hash = (Get-FileHash -LiteralPath $targetApk -Algorithm SHA256).Hash.ToLowerInvariant()
$releaseMetadata = [ordered]@{
    version_code = $versionCode
    version_name = $versionName
    file_name = $fileName
    sha256 = $hash
    size_bytes = $file.Length
    mandatory = $false
    release_notes = $releaseNotes
}
$json = $releaseMetadata | ConvertTo-Json
[System.IO.File]::WriteAllText((Join-Path $OutputDir "version.json"), $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
Write-Host "Release ready: $targetApk"
