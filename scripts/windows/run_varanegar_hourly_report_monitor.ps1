param(
    [string]$ArtifactRoot = 'G:\NeginAI\artifacts\varanegar_training_video_analysis',
    [int]$PollSeconds = 60,
    [switch]$Once,
    [switch]$ForceCurrentHour
)

$ErrorActionPreference = 'Stop'

$statePath = Join-Path $ArtifactRoot 'training_queue.progress.json'
$hourlyDir = Join-Path $ArtifactRoot 'reports\hourly'
$reviewRoot = Join-Path $ArtifactRoot 'review_packs'
$expertRoot = Join-Path $ArtifactRoot 'reports\expert'
$eventPath = Join-Path $ArtifactRoot 'training_queue.events.jsonl'
$monitorLog = Join-Path $ArtifactRoot 'logs\hourly_monitor.log'

New-Item -ItemType Directory -Force -Path $hourlyDir,(Split-Path $monitorLog -Parent) | Out-Null

function Read-JsonSafe {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try { return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json } catch { return $null }
}

function Get-PersianHourStem {
    param([datetime]$At)
    $calendar = [System.Globalization.PersianCalendar]::new()
    return ('{0:D4}{1:D2}{2:D2}_{3:D2}' -f $calendar.GetYear($At),$calendar.GetMonth($At),$calendar.GetDayOfMonth($At),$At.Hour)
}

function Format-Hms {
    param([double]$Seconds)
    if ($Seconds -lt 0) { $Seconds = 0 }
    $span = [TimeSpan]::FromSeconds($Seconds)
    return ('{0:D2}:{1:D2}:{2:D2}' -f [int][math]::Floor($span.TotalHours),[int]$span.Minutes,[int]$span.Seconds)
}

function Write-MonitorEvent {
    param([string]$Type,[hashtable]$Data)
    $entry = [ordered]@{
        timestamp = (Get-Date).ToString('o')
        type = $Type
        data = $Data
    } | ConvertTo-Json -Compress -Depth 8
    Add-Content -LiteralPath $eventPath -Value $entry -Encoding utf8
}

function Write-CurrentHourReport {
    param([pscustomobject]$State)

    $now = Get-Date
    $stem = Get-PersianHourStem -At $now
    $path = Join-Path $hourlyDir ($stem + '_progress_fa.md')
    if ((Test-Path -LiteralPath $path) -and -not $ForceCurrentHour) { return $path }

    $current = $State.current
    $currentLine = 'فایل جاری: ندارد'
    $qualityLine = 'کنترل‌های کیفیت فایل جاری: داده‌ای موجود نیست.'
    $processLine = 'فرایند زنده: نامشخص'
    $healthLine = 'سلامت مرحلهٔ جاری: نامشخص'
    $etaLine = 'زمان تخمینی باقی‌ماندهٔ مرحلهٔ جاری: نامشخص'

    if ($null -ne $current) {
        $reviewDir = Join-Path $reviewRoot $current.output_stem
        $needle = '*' + $current.output_stem + '*'
        $asr = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like $needle })
        $progress = $current.transcription_progress
        $medium = $current.medium_review_progress
        if ($null -ne $medium -and $medium.status -in @('RUNNING','COMPLETE')) {
            $mediumPercent = if ($medium.status -eq 'COMPLETE') { 100.0 } elseif ($null -ne $medium.percent) { [double]$medium.percent } else { 0.0 }
            $mediumSegments = if ($null -ne $medium.segment_count) { [int]$medium.segment_count } else { 0 }
            $mediumEnd = if ($null -ne $medium.last_end_seconds) { [double]$medium.last_end_seconds } elseif ($medium.status -eq 'COMPLETE') { [double]$medium.total_review_seconds } else { 0.0 }
            $mediumTotal = if ($null -ne $medium.total_review_seconds) { [double]$medium.total_review_seconds } else { 0.0 }
            $mediumClipsSeen = @($medium.clips_seen).Count
            $mediumClipCount = if ($null -ne $medium.clip_count) { [int]$medium.clip_count } else { 0 }
            $currentLine = "فایل جاری: $($current.index) از $($State.total_files)، «$($current.title)» — Medium=$([math]::Round($mediumPercent, 2))٪، $mediumSegments قطعه، $mediumClipsSeen از $mediumClipCount بخش، پوشش $(Format-Hms $mediumEnd) از $(Format-Hms $mediumTotal)."
            if ($medium.status -eq 'COMPLETE') {
                $etaLine = 'زمان تخمینی باقی‌ماندهٔ Medium: 00:00:00.'
                $healthLine = 'سلامت Medium: COMPLETE؛ checkpoint نهایی ثبت شده است.'
            } elseif ($mediumEnd -gt 0 -and $asr.Count -gt 0) {
                $mediumProcess = $asr | Sort-Object CreationDate | Select-Object -First 1
                $elapsedSeconds = ((Get-Date) - ([datetime]$mediumProcess.CreationDate)).TotalSeconds
                $runningRtf = $elapsedSeconds / $mediumEnd
                $mediumEta = [math]::Max(0.0,$mediumTotal - $mediumEnd) * $runningRtf
                $etaLine = "زمان تخمینی باقی‌ماندهٔ Medium: $(Format-Hms $mediumEta)؛ RTF فعلی=$([math]::Round($runningRtf, 2))."
                $mediumProgressPath = Join-Path $reviewDir 'medium_review.progress.json'
                $checkpointAgeSeconds = if (Test-Path -LiteralPath $mediumProgressPath) { [math]::Max(0.0,((Get-Date) - (Get-Item -LiteralPath $mediumProgressPath).LastWriteTime).TotalSeconds) } else { -1.0 }
                $liveWorkers = @(foreach ($processId in @($asr.ProcessId)) { Get-Process -Id $processId -ErrorAction SilentlyContinue })
                $cpuSeconds = [double](($liveWorkers | Measure-Object -Property CPU -Sum).Sum)
                $healthLine = "سلامت Medium: پردازشگر فعال=$($liveWorkers.Count -gt 0)؛ سن آخرین checkpoint=$(Format-Hms $checkpointAgeSeconds)؛ CPU تجمعی=$([math]::Round($cpuSeconds, 1)) ثانیه."
            }
        } else {
            $percent = if ($progress.status -eq 'COMPLETE') { 100.0 } elseif ($null -ne $progress.percent) { [double]$progress.percent } else { 0.0 }
            $segments = if ($null -ne $progress.segment_count) { [int]$progress.segment_count } else { 0 }
            $lastEnd = if ($null -ne $progress.last_end_seconds) { [double]$progress.last_end_seconds } else { 0.0 }
            $duration = if ($null -ne $progress.duration_seconds) { [double]$progress.duration_seconds } else { 0.0 }
            if ($duration -gt 0) { $lastEnd = [math]::Min($lastEnd,$duration) }
            $currentLine = "فایل جاری: $($current.index) از $($State.total_files)، «$($current.title)» — Small=$([math]::Round($percent, 2))٪، $segments قطعه، پوشش $(Format-Hms $lastEnd) از $(Format-Hms $duration)."
            if ($null -ne $progress.estimated_remaining_seconds) {
                $etaLine = "زمان تخمینی باقی‌ماندهٔ Small: $(Format-Hms ([double]$progress.estimated_remaining_seconds))."
            }
        }

        $visual = Read-JsonSafe (Join-Path $reviewDir 'visual_review.json')
        $plan = Read-JsonSafe (Join-Path $reviewDir 'medium_review_plan.json')
        $audit = Read-JsonSafe (Join-Path $reviewDir 'expert_pack_audit.json')
        $expert = Read-JsonSafe (Join-Path $expertRoot ($current.output_stem + '_expert_analysis.json'))
        $visualStatus = if ($null -ne $visual) { $visual.validation } else { 'MISSING' }
        $frameCount = if ($null -ne $visual) { [int]$visual.scope.reviewed_frame_count } else { 0 }
        $observationCount = if ($null -ne $visual) { @($visual.verified_visual_observations).Count } else { 0 }
        $planStatus = if ($null -ne $plan) { $plan.validation } else { 'MISSING' }
        $clipCount = if ($null -ne $plan) { @($plan.clips).Count } else { 0 }
        $planMinutes = if ($null -ne $plan) { [math]::Round(([double]$plan.total_review_seconds / 60), 1) } else { 0 }
        $auditState = if ($null -ne $audit) { $audit.pack_state } else { 'MISSING' }
        $expertStatus = if ($null -ne $expert) { $expert.validation } else { 'MISSING' }
        $qualityLine = "کنترل‌های کیفیت: تصویر=$visualStatus ($frameCount فریم، $observationCount مشاهده)؛ برنامهٔ Medium=$planStatus ($clipCount بخش، $planMinutes دقیقه)؛ بسته=$auditState؛ گزارش کارشناسی=$expertStatus."

        $queueProcesses = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'pwsh*' -and $_.CommandLine -like '*run_varanegar_training_video_queue.ps1*' })
        $queueAlive = ($queueProcesses.Count -gt 0)
        $processLine = "فرایند زنده: صف=$queueAlive؛ PID صف=$((@($queueProcesses.ProcessId) -join '، '))؛ پردازشگر فایل=$($asr.Count -gt 0)؛ PIDهای فایل=$((@($asr.ProcessId) -join '، '))."
    }

    $stderrFiles = @(Get-ChildItem -LiteralPath (Join-Path $ArtifactRoot 'logs') -File -Filter 'queue*.stderr.log' -ErrorAction SilentlyContinue)
    $stderrBytes = if ($stderrFiles.Count -gt 0) { [int64](($stderrFiles | Measure-Object -Property Length -Sum).Sum) } else { -1 }
    $body = @"
# گزارش ساعتی آموزش ورانگر

- زمان: $($now.ToString('yyyy-MM-dd HH:mm:ss zzz'))
- وضعیت صف: $($State.status)
- فایل‌های کامل‌شده: $($State.completed_files) از $($State.total_files)
- فایل‌های باقی‌مانده: $($State.remaining_files)
- $currentLine
- $etaLine
- $healthLine
- $qualityLine
- $processLine
- اندازهٔ stderr صف: $stderrBytes بایت
- پیام صف: $($State.message)

این گزارش از وضعیت واقعی صف و فایل‌های شواهد ساخته شده است. درصد رونویسی معادل تکمیل دانش کارشناسی نیست؛ هر فایل فقط پس از Medium، ادغام، گزارش نهایی و ممیزی FINAL_PASS کامل محسوب می‌شود.
"@
    [System.IO.File]::WriteAllText($path,$body,[System.Text.UTF8Encoding]::new($false))
    Write-MonitorEvent -Type 'HOURLY_REPORT_MONITOR' -Data @{ path=$path; completed_files=$State.completed_files; current_index=$current.index }
    return $path
}

do {
    try {
        $state = Read-JsonSafe $statePath
        if ($null -ne $state) {
            $written = Write-CurrentHourReport -State $state
            Add-Content -LiteralPath $monitorLog -Value ("{0} PASS {1}" -f (Get-Date).ToString('o'),$written) -Encoding utf8
            if ($state.status -in @('COMPLETE','COMPLETE_WITH_FAILURES')) { break }
        } else {
            Add-Content -LiteralPath $monitorLog -Value ("{0} WAIT state unavailable" -f (Get-Date).ToString('o')) -Encoding utf8
        }
    } catch {
        Add-Content -LiteralPath $monitorLog -Value ("{0} ERROR {1}" -f (Get-Date).ToString('o'),$_.Exception.Message) -Encoding utf8
    }
    if (-not $Once) { Start-Sleep -Seconds ([math]::Max(30,$PollSeconds)) }
} while (-not $Once)
