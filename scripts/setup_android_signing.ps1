param(
    [string]$ProjectDir = (Join-Path $PSScriptRoot "..\android\SellerNavigator")
)

$ErrorActionPreference = "Stop"
$propertiesPath = Join-Path $ProjectDir "keystore.properties"
$signingDir = Join-Path $ProjectDir "signing"
$keystorePath = Join-Path $signingDir "neginai-release.jks"

if ((Test-Path -LiteralPath $propertiesPath) -and (Test-Path -LiteralPath $keystorePath)) {
    Write-Host "Android release signing key already exists."
    exit 0
}

New-Item -ItemType Directory -Path $signingDir -Force | Out-Null
$passwordBytes = [byte[]]::new(32)
$random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try { $random.GetBytes($passwordBytes) } finally { $random.Dispose() }
$password = ([BitConverter]::ToString($passwordBytes)).Replace("-", "")
$keytool = (Get-Command keytool.exe -ErrorAction Stop).Source

$keytoolArguments = @(
    "-genkeypair", "-v", "-keystore", $keystorePath,
    "-alias", "neginai", "-keyalg", "RSA", "-keysize", "4096",
    "-validity", "10000", "-storepass", $password, "-keypass", $password,
    "-dname", "CN=Negin Pakhsh, OU=Software, O=Negin Pakhsh, L=Tehran, C=IR"
)
& $keytool @keytoolArguments | Out-Null
if ($LASTEXITCODE -ne 0) { throw "keytool failed with exit code $LASTEXITCODE" }

$relativeStore = "signing/neginai-release.jks"
$properties = @(
    "storeFile=$relativeStore",
    "storePassword=$password",
    "keyAlias=neginai",
    "keyPassword=$password"
) -join [Environment]::NewLine
[System.IO.File]::WriteAllText($propertiesPath, $properties + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
Write-Host "Android release signing key created. Back up the signing directory and keystore.properties securely."
