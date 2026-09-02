$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Python = Join-Path $RepoRoot 'tools\varanegar-asr\.venv\Scripts\python.exe'
$Transcriber = Join-Path $PSScriptRoot 'transcribe_varanegar_training_video.py'
$Source = 'E:\Desktop 1403.6.19\Desktop\آموزش آخرین ورژن ورانگر\اطلاعات پایه 1.mp4'
$Output = Join-Path $RepoRoot 'artifacts\varanegar_training_video_analysis\transcripts'
$Models = Join-Path $RepoRoot 'tools\varanegar-asr\models'

& $Python $Transcriber `
    --input $Source `
    --output-dir $Output `
    --output-stem '01_base_information_01' `
    --model-dir $Models `
    --model 'small' `
    --language 'fa'
exit $LASTEXITCODE
