$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$ArtifactRoot = Join-Path $RepoRoot 'artifacts\varanegar_training_video_analysis'
$StatePath = Join-Path $ArtifactRoot 'training_queue.progress.json'
$EventPath = Join-Path $ArtifactRoot 'training_queue.events.jsonl'
$ReportDir = Join-Path $ArtifactRoot 'reports'
$TranscriptDir = Join-Path $ArtifactRoot 'transcripts'
$ReviewRoot = Join-Path $ArtifactRoot 'review_packs'

$queueProcesses = @(
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like '*run_varanegar_training_video_queue.ps1*' } |
        Select-Object ProcessId, ParentProcessId, Name, CreationDate, CommandLine
)
$workerProcesses = @(
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like '*transcribe_varanegar_training_video.py*' } |
        Select-Object ProcessId, ParentProcessId, Name, CreationDate, CommandLine
)

$state = if (Test-Path -LiteralPath $StatePath) {
    Get-Content -Raw -LiteralPath $StatePath | ConvertFrom-Json
} else { $null }

$recentEvents = if (Test-Path -LiteralPath $EventPath) {
    @(Get-Content -LiteralPath $EventPath -Tail 20 | ForEach-Object { $_ | ConvertFrom-Json })
} else { @() }

$completionReports = if (Test-Path -LiteralPath $ReportDir) {
    @(Get-ChildItem -LiteralPath $ReportDir -File -Filter '*_completion_fa.md' | Sort-Object Name | Select-Object Name, FullName, LastWriteTime)
} else { @() }

$transcripts = if (Test-Path -LiteralPath $TranscriptDir) {
    @(Get-ChildItem -LiteralPath $TranscriptDir -File -Filter '*.transcript.json' | Sort-Object Name | Select-Object Name, FullName, Length, LastWriteTime)
} else { @() }

$partialTranscripts = if (Test-Path -LiteralPath $TranscriptDir) {
    @(Get-ChildItem -LiteralPath $TranscriptDir -File -Filter '*.transcript.partial.json' | Sort-Object Name | Select-Object Name, FullName, Length, LastWriteTime)
} else { @() }

$reviewPacks = if (Test-Path -LiteralPath $ReviewRoot) {
    @(Get-ChildItem -LiteralPath $ReviewRoot -File -Filter 'review_pack.json' -Recurse | Sort-Object FullName | Select-Object FullName, Length, LastWriteTime)
} else { @() }

$analysisDrafts = if (Test-Path -LiteralPath $ReviewRoot) {
    @(Get-ChildItem -LiteralPath $ReviewRoot -File -Filter 'analysis_draft.json' -Recurse | Sort-Object FullName | Select-Object FullName, Length, LastWriteTime)
} else { @() }

[ordered]@{
    checked_at = (Get-Date).ToString('o')
    queue_running = ($queueProcesses.Count -gt 0)
    queue_processes = $queueProcesses
    transcription_worker_count = $workerProcesses.Count
    transcription_workers = $workerProcesses
    state = $state
    transcript_count = $transcripts.Count
    transcripts = $transcripts
    partial_transcript_count = $partialTranscripts.Count
    partial_transcripts = $partialTranscripts
    review_pack_count = $reviewPacks.Count
    review_packs = $reviewPacks
    analysis_draft_count = $analysisDrafts.Count
    analysis_drafts = $analysisDrafts
    completion_report_count = $completionReports.Count
    completion_reports = $completionReports
    recent_events = $recentEvents
} | ConvertTo-Json -Depth 12
