param(
    [Parameter(Mandatory = $true)]
    [string]$SourceVideo,
    [string]$Model = 'medium'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$ToolRoot = Join-Path $RepoRoot 'tools\varanegar-asr'
$Venv = Join-Path $ToolRoot '.venv'
$Python = Join-Path $Venv 'Scripts\python.exe'
$ModelRoot = Join-Path $ToolRoot 'models'
$AnalysisRoot = Join-Path $RepoRoot 'artifacts\varanegar_training_video_analysis'
$SmokeAudio = Join-Path $AnalysisRoot 'asr_smoke_input_120s.wav'
$SmokeResult = Join-Path $AnalysisRoot "asr_smoke_${Model}_fa.json"
$SmokeScript = Join-Path $PSScriptRoot 'varanegar_asr_smoke.py'

if (-not (Test-Path -LiteralPath $SourceVideo -PathType Leaf)) {
    throw "Source video not found: $SourceVideo"
}
New-Item -ItemType Directory -Force -Path $ToolRoot, $ModelRoot, $AnalysisRoot | Out-Null

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    & py -3.11 -m venv $Venv
    if ($LASTEXITCODE -ne 0) { throw 'Unable to create the isolated ASR virtual environment.' }
}

& $Python -m pip install --disable-pip-version-check --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'Unable to upgrade pip in the isolated ASR environment.' }
& $Python -m pip install --disable-pip-version-check 'faster-whisper==1.2.1'
if ($LASTEXITCODE -ne 0) { throw 'Unable to install faster-whisper 1.2.1.' }

& ffmpeg -hide_banner -loglevel error -y -ss '00:10:00' -t '00:02:00' -i $SourceVideo -vn -ac 1 -ar 16000 $SmokeAudio
if ($LASTEXITCODE -ne 0) { throw 'Unable to extract the read-only ASR smoke sample.' }

& $Python $SmokeScript --input $SmokeAudio --output $SmokeResult --model $Model --model-dir $ModelRoot
if ($LASTEXITCODE -ne 0) { throw 'The Persian ASR smoke transcription failed.' }

$PackageVersion = (& $Python -c "import importlib.metadata; print(importlib.metadata.version('faster-whisper'))").Trim()
$ModelBytes = (Get-ChildItem -LiteralPath $ModelRoot -Recurse -File | Measure-Object Length -Sum).Sum
$VenvBytes = (Get-ChildItem -LiteralPath $Venv -Recurse -File | Measure-Object Length -Sum).Sum
[pscustomobject]@{
    Validation = 'PASS'
    Engine = 'faster-whisper'
    EngineVersion = $PackageVersion
    Model = $Model
    Device = 'cpu'
    ComputeType = 'int8'
    VenvPath = $Venv
    ModelPath = $ModelRoot
    VenvBytes = $VenvBytes
    ModelBytes = $ModelBytes
    SmokeResult = $SmokeResult
    SourceVideoModified = $false
} | ConvertTo-Json -Depth 3
