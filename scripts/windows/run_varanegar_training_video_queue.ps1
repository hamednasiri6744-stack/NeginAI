param(
    [int]$ExistingFirstPid = 0,
    [int]$MaxAttemptsPerFile = 3,
    [switch]$ValidateOnly
)

$ErrorActionPreference = 'Stop'

# Keep Windows awake only while this queue process is alive.  The execution
# state is thread-scoped and Windows clears it automatically when this process
# exits, so this does not alter the user's permanent power-plan settings.
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class QueueExecutionState {
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint executionState);
}
'@

$esContinuous = [Convert]::ToUInt32('80000000', 16)
$esSystemRequired = [uint32]0x00000001
$executionStateResult = [QueueExecutionState]::SetThreadExecutionState($esContinuous -bor $esSystemRequired)
if ($executionStateResult -eq 0) {
    throw 'Windows rejected the queue keep-awake request.'
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Python = Join-Path $RepoRoot 'tools\varanegar-asr\.venv\Scripts\python.exe'
$Transcriber = Join-Path $PSScriptRoot 'transcribe_varanegar_training_video.py'
$ReviewPacker = Join-Path $PSScriptRoot 'prepare_varanegar_video_review_pack.py'
$DraftBuilder = Join-Path $PSScriptRoot 'build_varanegar_video_analysis_draft.py'
$LedgerUpdater = Join-Path $PSScriptRoot 'update_varanegar_training_knowledge_ledger.py'
$WorkbookBuilder = Join-Path $PSScriptRoot 'create_varanegar_expert_review_workbook.py'
$ReviewClipTranscriber = Join-Path $PSScriptRoot 'transcribe_varanegar_review_clips.py'
$TranscriptMerger = Join-Path $PSScriptRoot 'merge_varanegar_review_transcripts.py'
$TranscriptRepetitionAuditor = Join-Path $PSScriptRoot 'audit_varanegar_transcript_repetition.py'
$AudioQuestionEvidenceBuilder = Join-Path $PSScriptRoot 'build_varanegar_audio_question_evidence.py'
$ExpertPackAuditor = Join-Path $PSScriptRoot 'audit_varanegar_video_expert_pack.py'
$SourceRoot = 'E:\Desktop 1403.6.19\Desktop\آموزش آخرین ورژن ورانگر'
$ArtifactRoot = Join-Path $RepoRoot 'artifacts\varanegar_training_video_analysis'
$OutputDir = Join-Path $ArtifactRoot 'transcripts'
$ReportDir = Join-Path $ArtifactRoot 'reports'
$HourlyDir = Join-Path $ReportDir 'hourly'
$LogDir = Join-Path $ArtifactRoot 'logs'
$Models = Join-Path $RepoRoot 'tools\varanegar-asr\models'
$ReviewRoot = Join-Path $ArtifactRoot 'review_packs'
$StatePath = Join-Path $ArtifactRoot 'training_queue.progress.json'
$EventPath = Join-Path $ArtifactRoot 'training_queue.events.jsonl'

$Videos = @(
    @{ Index = 1;  File = 'اطلاعات پایه 1.mp4'; Stem = '01_base_information_01'; Title = 'اطلاعات پایه ۱' },
    @{ Index = 2;  File = 'اطلاعات پایه 2.mp4'; Stem = '02_base_information_02'; Title = 'اطلاعات پایه ۲' },
    @{ Index = 3;  File = 'انبار.mp4'; Stem = '03_inventory'; Title = 'انبار' },
    @{ Index = 4;  File = 'پرسش و پاسخ ورانگر.mp4'; Stem = '04_varanegar_qa'; Title = 'پرسش و پاسخ ورانگر' },
    @{ Index = 5;  File = 'تبلت پیش ویزیت.mp4'; Stem = '05_tablet_previsit'; Title = 'تبلت پیش‌ویزیت' },
    @{ Index = 6;  File = 'تبلت توزیع.mp4'; Stem = '06_tablet_distribution'; Title = 'تبلت توزیع' },
    @{ Index = 7;  File = 'تبلت سرپرست.mp4'; Stem = '07_tablet_supervisor'; Title = 'تبلت سرپرست' },
    @{ Index = 8;  File = 'تبلت گرم.mp4'; Stem = '08_tablet_hot_sale'; Title = 'تبلت گرم' },
    @{ Index = 9;  File = 'تنظیمات دستگاه تبلت.mp4'; Stem = '09_tablet_device_settings'; Title = 'تنظیمات دستگاه تبلت' },
    @{ Index = 10; File = 'تنظیمات سیستم.mp4'; Stem = '10_system_settings'; Title = 'تنظیمات سیستم' },
    @{ Index = 11; File = 'حسابداری انبار و خرید.mp4'; Stem = '11_inventory_purchase_accounting'; Title = 'حسابداری انبار و خرید' },
    @{ Index = 12; File = 'حسابداری مالی.mp4'; Stem = '12_financial_accounting'; Title = 'حسابداری مالی' },
    @{ Index = 13; File = 'خزانه 1.mp4'; Stem = '13_treasury_01'; Title = 'خزانه ۱' },
    @{ Index = 14; File = 'خزانه2.mp4'; Stem = '14_treasury_02'; Title = 'خزانه ۲' },
    @{ Index = 15; File = 'دموی تبلت فروش گرم فروش پیش ویزیت و توزیع.mp4'; Stem = '15_tablet_sales_demo'; Title = 'دموی تبلت فروش گرم، پیش‌ویزیت و توزیع' },
    @{ Index = 16; File = 'ردیابی و GRS.mp4'; Stem = '16_tracking_grs'; Title = 'ردیابی و GRS' },
    @{ Index = 17; File = 'فروش.mp4'; Stem = '17_sales'; Title = 'فروش' },
    @{ Index = 18; File = 'کنترل دسترسی 1.mp4'; Stem = '18_access_control_01'; Title = 'کنترل دسترسی ۱' },
    @{ Index = 19; File = 'کنترل دسترسی 2.mp4'; Stem = '19_access_control_02'; Title = 'کنترل دسترسی ۲' },
    @{ Index = 20; File = 'کنسول NGT ستاد 1.mp4'; Stem = '20_ngt_hq_console_01'; Title = 'کنسول NGT ستاد ۱' },
    @{ Index = 21; File = 'کنسول NGT ستاد 2.mp4'; Stem = '21_ngt_hq_console_02'; Title = 'کنسول NGT ستاد ۲' },
    @{ Index = 22; File = 'کنسول NGT شعب - گرم - سرد - توزیع.mp4'; Stem = '22_ngt_branch_console'; Title = 'کنسول NGT شعب، گرم، سرد و توزیع' },
    @{ Index = 23; File = 'گزارشات ورانگر.mp4'; Stem = '23_varanegar_reports'; Title = 'گزارشات ورانگر' }
)

$VideoDurationSeconds = @{
    1 = 8072.820; 2 = 6082.708; 3 = 9937.708; 4 = 5843.589; 5 = 4727.707
    6 = 6162.074; 7 = 2768.709; 8 = 5940.718; 9 = 1914.703; 10 = 4165.831
    11 = 4663.713; 12 = 5195.589; 13 = 10637.580; 14 = 2628.089; 15 = 7841.944
    16 = 2872.595; 17 = 13111.202; 18 = 2477.461; 19 = 511.080; 20 = 5052.206
    21 = 3266.220; 22 = 6676.326; 23 = 3166.583
}
$TotalVideoSeconds = [double](($VideoDurationSeconds.Values | Measure-Object -Sum).Sum)

function Write-JsonFile {
    param([string]$Path, [object]$Value)
    $json = $Value | ConvertTo-Json -Depth 12
    [System.IO.File]::WriteAllText($Path, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
}

function Add-QueueEvent {
    param([string]$Type, [object]$Data)
    $event = [ordered]@{
        timestamp = (Get-Date).ToString('o')
        type = $Type
        data = $Data
    }
    Add-Content -LiteralPath $EventPath -Value ($event | ConvertTo-Json -Compress -Depth 8) -Encoding utf8
}

function Get-CompletedVideos {
    $completed = @()
    foreach ($video in $Videos) {
        $resultPath = Join-Path $OutputDir ($video.Stem + '.transcript.json')
        $reviewDir = Join-Path $ReviewRoot $video.Stem
        $mediumPlan = Join-Path $reviewDir 'medium_review_plan.json'
        $mediumTranscript = Join-Path $reviewDir 'medium_review.transcript.json'
        $mediumRepetitionAudit = Join-Path $reviewDir 'medium_repetition_audit.json'
        $audioQuestionEvidence = Join-Path $reviewDir 'audio_question_evidence.json'
        $mergedTranscript = Join-Path $reviewDir 'review_merged.transcript.json'
        $expertWorkbook = Join-Path $reviewDir 'expert_review_workbook.json'
        $completionChecklist = Join-Path $reviewDir 'expert_completion_checklist.json'
        $expertPackAudit = Join-Path $reviewDir 'expert_pack_audit.json'
        $source = Join-Path $SourceRoot $video.File
        $expertJson = Join-Path (Join-Path $ReportDir 'expert') ($video.Stem + '_expert_analysis.json')
        $expertMarkdown = Join-Path (Join-Path $ReportDir 'expert') ($video.Stem + '_expert_analysis_fa.md')
        if (-not (Test-Path -LiteralPath $resultPath)) { continue }
        if (-not (Test-Path -LiteralPath $mediumRepetitionAudit) -or -not (Test-Path -LiteralPath $audioQuestionEvidence) -or -not (Test-Path -LiteralPath $mergedTranscript) -or -not (Test-Path -LiteralPath $expertWorkbook) -or -not (Test-Path -LiteralPath $completionChecklist) -or -not (Test-Path -LiteralPath $expertPackAudit)) { continue }
        if (-not (Test-Path -LiteralPath $expertJson) -or -not (Test-Path -LiteralPath $expertMarkdown)) { continue }
        try {
            $result = Get-Content -Raw -LiteralPath $resultPath | ConvertFrom-Json
            $expert = Get-Content -Raw -LiteralPath $expertJson | ConvertFrom-Json
            $workbook = Get-Content -Raw -LiteralPath $expertWorkbook | ConvertFrom-Json
            $mediumCurrent = Test-MediumReviewCurrent -Path $mediumTranscript -Plan $mediumPlan -Source $source -Model 'medium'
            $mediumRepetitionCurrent = Test-PassJsonCurrent -Path $mediumRepetitionAudit -Inputs @($mediumTranscript)
            $audioQuestionEvidenceCurrent = Test-PassJsonCurrent -Path $audioQuestionEvidence -Inputs @($mediumTranscript, (Join-Path $reviewDir 'AUDIO_REVIEW_MATRIX_FA.md'))
            $mergedCurrent = Test-PassJsonCurrent -Path $mergedTranscript -Inputs @($resultPath, $mediumTranscript)
            $checklistCurrent = Test-ExpertCompletionChecklist -Path $completionChecklist -FreshInputs @($mergedTranscript, $expertWorkbook)
            $reportCurrent = Test-ExpertReport -JsonPath $expertJson -MarkdownPath $expertMarkdown -Video $video -ChecklistPath $completionChecklist -FreshInputs @($mergedTranscript, $expertWorkbook)
            $auditCurrent = Test-ExpertPackAuditCurrent -Path $expertPackAudit -RequiredState 'FINAL_PASS'
            if ($result.validation -eq 'PASS' -and $mediumCurrent -and $mediumRepetitionCurrent -and $audioQuestionEvidenceCurrent -and $mergedCurrent -and $checklistCurrent -and $auditCurrent -and $workbook.validation -eq 'DRAFT' -and $expert.validation -eq 'PASS' -and $reportCurrent) { $completed += $video }
        } catch {
            Add-QueueEvent -Type 'INVALID_RESULT_JSON' -Data @{ index = $video.Index; path = $resultPath; error = $_.Exception.Message }
        }
    }
    return @($completed)
}

function Get-VideoProgress {
    param([hashtable]$Video)
    $path = Join-Path $OutputDir ($Video.Stem + '.progress.json')
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try { return Get-Content -Raw -LiteralPath $path | ConvertFrom-Json } catch { return $null }
}

function Write-QueueState {
    param(
        [string]$Status,
        [hashtable]$CurrentVideo,
        [int]$Attempt = 0,
        [string]$Message = ''
    )
    $completed = @(Get-CompletedVideos)
    $videoProgress = if ($null -ne $CurrentVideo) { Get-VideoProgress -Video $CurrentVideo } else { $null }
    $mediumProgressPath = if ($null -ne $CurrentVideo) { Join-Path (Join-Path $ReviewRoot $CurrentVideo.Stem) 'medium_review.progress.json' } else { $null }
    $mediumProgress = if ($null -ne $mediumProgressPath -and (Test-Path -LiteralPath $mediumProgressPath)) {
        try { Get-Content -Raw -LiteralPath $mediumProgressPath | ConvertFrom-Json } catch { $null }
    } else { $null }
    $payload = [ordered]@{
        artifact = 'varanegar_training_video_queue_progress'
        schema_version = 1
        status = $Status
        updated_at = (Get-Date).ToString('o')
        total_files = $Videos.Count
        completed_files = $completed.Count
        remaining_files = $Videos.Count - $completed.Count
        completed_indices = @($completed | ForEach-Object { $_.Index })
        current = if ($null -ne $CurrentVideo) {
            [ordered]@{
                index = $CurrentVideo.Index
                title = $CurrentVideo.Title
                source = (Join-Path $SourceRoot $CurrentVideo.File)
                output_stem = $CurrentVideo.Stem
                attempt = $Attempt
                transcription_progress = $videoProgress
                medium_review_progress = $mediumProgress
            }
        } else { $null }
        message = $Message
        reports_directory = $ReportDir
    }
    Write-JsonFile -Path $StatePath -Value $payload
    return $payload
}

function Write-HourlySnapshot {
    param([object]$State, [switch]$Force)
    $now = Get-Date
    $hourKey = $now.ToString('yyyyMMdd_HH')
    $path = Join-Path $HourlyDir ($hourKey + '_progress_fa.md')
    if ((-not $Force) -and (Test-Path -LiteralPath $path)) { return }

    $rawSeconds = 0.0
    foreach ($video in $Videos) {
        $resultPath = Join-Path $OutputDir ($video.Stem + '.transcript.json')
        $countedComplete = $false
        if (Test-Path -LiteralPath $resultPath) {
            try {
                $result = Get-Content -Raw -LiteralPath $resultPath | ConvertFrom-Json
                if ($result.validation -eq 'PASS') {
                    $rawSeconds += [double]$result.summary.duration_seconds
                    $countedComplete = $true
                }
            } catch { }
        }
        if (-not $countedComplete) {
            $progressPath = Join-Path $OutputDir ($video.Stem + '.progress.json')
            if (Test-Path -LiteralPath $progressPath) {
                try {
                    $progress = Get-Content -Raw -LiteralPath $progressPath | ConvertFrom-Json
                    if ($progress.status -eq 'RUNNING') {
                        $rawSeconds += [math]::Min([double]$progress.last_end_seconds, [double]$VideoDurationSeconds[$video.Index])
                    }
                } catch { }
            }
        }
    }
    $rawCoveragePercent = if ($TotalVideoSeconds -gt 0) { [math]::Round(100 * $rawSeconds / $TotalVideoSeconds, 3) } else { 0 }
    $totalHours = [math]::Floor($TotalVideoSeconds / 3600)
    $totalMinutes = [math]::Floor(($TotalVideoSeconds % 3600) / 60)
    $totalSeconds = [math]::Floor($TotalVideoSeconds % 60)
    $totalVideoHms = '{0:00}:{1:00}:{2:00}' -f $totalHours, $totalMinutes, $totalSeconds

    $phaseLabels = @{
        RUNNING = 'رونویسی کامل Small'
        RUNNING_EXISTING = 'رونویسی کامل Small (ادامهٔ اجرای قبلی)'
        WAITING_VISUAL_REVIEW_PLAN = 'تکمیل پوشش تصویری و برنامهٔ بازشنوی'
        RUNNING_MEDIUM_REVIEW = 'بازشنوی هدفمند با مدل Medium'
        WAITING_EXPERT_REVIEW = 'بازبینی و تثبیت گزارش کارشناسی'
        WAITING_RECOVERY = 'بازیابی همان فایل و تلاش مجدد با checkpoint'
        FILE_COMPLETE = 'فایل جاری کامل شده است'
        COMPLETE = 'کل صف کامل شده است'
        COMPLETE_WITH_FAILURES = 'صف پایان یافته و نیازمند ترمیم است'
    }
    $phase = if ($phaseLabels.ContainsKey([string]$State.status)) { $phaseLabels[[string]$State.status] } else { [string]$State.status }

    $currentText = if ($null -ne $State.current) {
        $transcription = $State.current.transcription_progress
        $transcriptionStatus = if ($null -ne $transcription) { [string]$transcription.status } else { 'UNKNOWN' }
        $transcriptionText = if ($transcriptionStatus -eq 'COMPLETE') {
            'کامل (100٪)'
        } elseif ($null -ne $transcription.percent) {
            "$($transcription.percent)٪"
        } elseif (
            $null -ne $transcription.last_end_seconds -and
            $null -ne $transcription.duration_seconds -and
            [double]$transcription.duration_seconds -gt 0
        ) {
            $derivedPercent = [math]::Round([math]::Min(100.0, [double]$transcription.last_end_seconds / [double]$transcription.duration_seconds * 100), 3)
            "$derivedPercent٪ (محاسبه‌شده)"
        } else {
            "$transcriptionStatus (درصد نامشخص)"
        }
        "فایل جاری: $($State.current.index) از $($State.total_files)، «$($State.current.title)» — رونویسی Small: $transcriptionText"
    } else { 'فایل جاری: ندارد' }

    $qualityText = 'کنترل‌های کیفیت فایل جاری: هنوز داده‌ای ثبت نشده است.'
    $mediumText = 'بازشنوی Medium: هنوز آغاز نشده است.'
    if ($null -ne $State.current) {
        $reviewDir = Join-Path $ReviewRoot $State.current.output_stem
        $visualReviewPath = Join-Path $reviewDir 'visual_review.json'
        $mediumPlanPath = Join-Path $reviewDir 'medium_review_plan.json'
        $matrixPath = Join-Path $reviewDir 'AUDIO_REVIEW_MATRIX_FA.md'
        $glossaryPath = Join-Path $reviewDir 'GLOSSARY_WORKING_FA.md'
        $deltaMatrixPath = Join-Path $reviewDir 'RECONSTRUCTION_DELTA_MATRIX_FA.md'
        $uatScenariosPath = Join-Path $reviewDir 'UAT_SCENARIOS_FA.md'
        $completionChecklistPath = Join-Path $reviewDir 'expert_completion_checklist.json'
        $expertPackAuditPath = Join-Path $reviewDir 'expert_pack_audit.json'
        $expertJsonPath = Join-Path (Join-Path $ReportDir 'expert') ($State.current.output_stem + '_expert_analysis.json')
        $visualPass = Test-PassJson -Path $visualReviewPath
        $planPass = Test-PassJson -Path $mediumPlanPath
        $matrixReady = Test-Path -LiteralPath $matrixPath
        $glossaryReady = Test-Path -LiteralPath $glossaryPath
        $deltaMatrixReady = Test-Path -LiteralPath $deltaMatrixPath
        $uatScenariosReady = Test-Path -LiteralPath $uatScenariosPath
        $checklistStatus = 'MISSING'
        $checklistPending = $null
        if (Test-Path -LiteralPath $completionChecklistPath) {
            try {
                $checklistPayload = Get-Content -Raw -LiteralPath $completionChecklistPath | ConvertFrom-Json
                $checklistStatus = [string]$checklistPayload.validation
                $checklistPending = $checklistPayload.summary.pending
            } catch { $checklistStatus = 'INVALID' }
        }
        $expertStatus = 'MISSING'
        if (Test-Path -LiteralPath $expertJsonPath) {
            try { $expertStatus = [string](Get-Content -Raw -LiteralPath $expertJsonPath | ConvertFrom-Json).validation } catch { $expertStatus = 'INVALID' }
        }
        $auditState = 'MISSING'
        if (Test-Path -LiteralPath $expertPackAuditPath) {
            try { $auditState = [string](Get-Content -Raw -LiteralPath $expertPackAuditPath | ConvertFrom-Json).pack_state } catch { $auditState = 'INVALID' }
        }
        $planClips = 0
        $planSeconds = 0.0
        if ($planPass) {
            $planPayload = Get-Content -Raw -LiteralPath $mediumPlanPath | ConvertFrom-Json
            $planClips = @($planPayload.clips).Count
            $planSeconds = [double]$planPayload.total_review_seconds
        }
        $qualityText = "کنترل‌های کیفیت فایل جاری: تصویر=$visualPass؛ برنامه Medium=$planPass ($planClips بازه، $([math]::Round($planSeconds / 60, 1)) دقیقه)؛ ماتریس پرسش‌ها=$matrixReady؛ واژه‌نامه=$glossaryReady؛ تطبیق بازسازی=$deltaMatrixReady؛ UAT=$uatScenariosReady؛ چک‌لیست=$checklistStatus (معلق=$checklistPending)؛ گزارش=$expertStatus؛ ممیزی بسته=$auditState."
        if ($null -ne $State.current.medium_review_progress) {
            $mediumText = "بازشنوی Medium: وضعیت $($State.current.medium_review_progress.status)، پیشرفت $($State.current.medium_review_progress.percent)٪، $($State.current.medium_review_progress.segment_count) قطعه."
        }
    }
    $body = @"
# گزارش ساعتی آموزش ورانگر

- زمان: $($now.ToString('yyyy-MM-dd HH:mm:ss zzz'))
- وضعیت صف: $($State.status)
- مرحلهٔ جاری: $phase
- فایل‌های کامل‌شده: $($State.completed_files) از $($State.total_files)
- فایل‌های باقی‌مانده: $($State.remaining_files)
- $currentText
- پوشش زمانی رونویسی خام کل مجموعه: $rawCoveragePercent٪ از $totalVideoHms
- $qualityText
- $mediumText
- پیام: $($State.message)

این گزارش خودکار وضعیت واقعی صف و دروازه‌های کیفیت را ثبت می‌کند. پوشش زمانی خام معادل دانش کارشناسی معتبر نیست؛ اعتبار نهایی هر فایل فقط پس از گزارش تخصصی تازه و PASS ثبت می‌شود.
"@
    [System.IO.File]::WriteAllText($path, $body, [System.Text.UTF8Encoding]::new($false))
    Add-QueueEvent -Type 'HOURLY_REPORT' -Data @{ path = $path; completed_files = $State.completed_files; current_index = $State.current.index }
}

function Write-FileCompletionReport {
    param([hashtable]$Video)
    $resultPath = Join-Path $OutputDir ($Video.Stem + '.transcript.json')
    $result = Get-Content -Raw -LiteralPath $resultPath | ConvertFrom-Json
    $reviewDir = Join-Path $ReviewRoot $Video.Stem
    $reviewPack = Join-Path $reviewDir 'review_pack.json'
    $visualReviewPath = Join-Path $reviewDir 'visual_review.json'
    $mediumPlanPath = Join-Path $reviewDir 'medium_review_plan.json'
    $mediumReviewPath = Join-Path $reviewDir 'medium_review.transcript.json'
    $mediumRepetitionAuditPath = Join-Path $reviewDir 'medium_repetition_audit.json'
    $audioQuestionEvidencePath = Join-Path $reviewDir 'audio_question_evidence.json'
    $mergedTranscriptPath = Join-Path $reviewDir 'review_merged.transcript.json'
    $analysisDraft = Join-Path $reviewDir 'analysis_draft_fa.md'
    $expertWorkbook = Join-Path $reviewDir 'expert_review_workbook_fa.md'
    $expertWorkbookJson = Join-Path $reviewDir 'expert_review_workbook.json'
    $audioMatrix = Join-Path $reviewDir 'AUDIO_REVIEW_MATRIX_FA.md'
    $glossary = Join-Path $reviewDir 'GLOSSARY_WORKING_FA.md'
    $deltaMatrix = Join-Path $reviewDir 'RECONSTRUCTION_DELTA_MATRIX_FA.md'
    $uatScenarios = Join-Path $reviewDir 'UAT_SCENARIOS_FA.md'
    $completionChecklistPath = Join-Path $reviewDir 'expert_completion_checklist.json'
    $expertPackAuditPath = Join-Path $reviewDir 'expert_pack_audit.json'
    $expertJsonPath = Join-Path (Join-Path $ReportDir 'expert') ($Video.Stem + '_expert_analysis.json')
    $expertMarkdownPath = Join-Path (Join-Path $ReportDir 'expert') ($Video.Stem + '_expert_analysis_fa.md')

    $visualReview = Get-Content -Raw -LiteralPath $visualReviewPath | ConvertFrom-Json
    $mediumPlan = Get-Content -Raw -LiteralPath $mediumPlanPath | ConvertFrom-Json
    $mediumReview = Get-Content -Raw -LiteralPath $mediumReviewPath | ConvertFrom-Json
    $mergedTranscript = Get-Content -Raw -LiteralPath $mergedTranscriptPath | ConvertFrom-Json
    $expertWorkbookPayload = Get-Content -Raw -LiteralPath $expertWorkbookJson | ConvertFrom-Json
    $completionChecklist = Get-Content -Raw -LiteralPath $completionChecklistPath | ConvertFrom-Json
    $expertPackAudit = Get-Content -Raw -LiteralPath $expertPackAuditPath | ConvertFrom-Json
    $expert = Get-Content -Raw -LiteralPath $expertJsonPath | ConvertFrom-Json
    $source = Join-Path $SourceRoot $Video.File
    $freshAfter = @($mergedTranscriptPath, $expertWorkbookJson, $completionChecklistPath) | ForEach-Object { (Get-Item -LiteralPath $_).LastWriteTimeUtc } | Sort-Object -Descending | Select-Object -First 1
    $expertFresh = (
        (Get-Item -LiteralPath $expertJsonPath).LastWriteTimeUtc -ge $freshAfter -and
        (Get-Item -LiteralPath $expertMarkdownPath).LastWriteTimeUtc -ge $freshAfter
    )
    $expertReportCurrent = Test-ExpertReport -JsonPath $expertJsonPath -MarkdownPath $expertMarkdownPath -Video $Video -ChecklistPath $completionChecklistPath -FreshInputs @($mergedTranscriptPath, $expertWorkbookJson)

    $allGatesPass = (
        $result.validation -eq 'PASS' -and
        $visualReview.validation -eq 'PASS' -and
        $mediumPlan.validation -eq 'PASS' -and
        (Test-MediumReviewCurrent -Path $mediumReviewPath -Plan $mediumPlanPath -Source $source -Model 'medium') -and
        (Test-PassJsonCurrent -Path $mediumRepetitionAuditPath -Inputs @($mediumReviewPath)) -and
        (Test-PassJsonCurrent -Path $audioQuestionEvidencePath -Inputs @($mediumReviewPath, $audioMatrix)) -and
        (Test-PassJsonCurrent -Path $mergedTranscriptPath -Inputs @($resultPath, $mediumReviewPath)) -and
        $expertWorkbookPayload.validation -eq 'DRAFT' -and
        (Test-ExpertCompletionChecklist -Path $completionChecklistPath -FreshInputs @($mergedTranscriptPath, $expertWorkbookJson)) -and
        (Test-ExpertPackAuditCurrent -Path $expertPackAuditPath -RequiredState 'FINAL_PASS') -and
        $expert.validation -eq 'PASS' -and
        $expertReportCurrent -and
        $expertFresh -and
        (Test-Path -LiteralPath $audioMatrix) -and
        (Test-Path -LiteralPath $glossary) -and
        (Test-Path -LiteralPath $deltaMatrix) -and
        (Test-Path -LiteralPath $uatScenarios)
    )
    if (-not $allGatesPass) {
        throw "Completion report gates are not all PASS for file $($Video.Index)."
    }

    $reportPath = Join-Path $ReportDir (('{0:d2}' -f $Video.Index) + '_' + $Video.Stem + '_completion_fa.md')
    $duration = [TimeSpan]::FromSeconds([double]$result.summary.duration_seconds)
    $elapsed = [TimeSpan]::FromSeconds([double]$result.summary.elapsed_seconds)
    $mediumDuration = [TimeSpan]::FromSeconds([double]$mediumReview.summary.review_seconds)
    $mediumElapsed = [TimeSpan]::FromSeconds([double]$mediumReview.summary.elapsed_seconds)
    $mediumCoverage = [math]::Round(100 * [double]$mediumReview.summary.review_seconds / [double]$result.summary.duration_seconds, 2)
    $completedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz')
    $nextStep = if ($Video.Index -lt $Videos.Count) {
        "این گزارش پایان فایل را ثبت می‌کند و صف اکنون مجاز است سراغ فایل $($Video.Index + 1) برود."
    } else {
        'این گزارش پایان آخرین فایل مجموعه را ثبت می‌کند؛ صف اکنون وارد ممیزی نهایی کل ۲۳ فایل می‌شود.'
    }
    $body = @"
# گزارش پایان فایل $($Video.Index): $($Video.Title)

- زمان تکمیل: $completedAt
- وضعیت کل چرخه: **PASS — رونویسی، بازبینی تصویری، بازشنوی Medium، ادغام و بازبینی کارشناسی کامل**
- فایل منبع: $($result.source.path)
- مدت ویدیو: $($duration.ToString('hh\:mm\:ss'))

## کنترل‌های تکمیل

| مرحله | وضعیت | شاهد |
|---|---|---|
| رونویسی کامل Small | PASS؛ $($result.summary.segment_count) قطعه، زمان پردازش $($elapsed.ToString('hh\:mm\:ss'))، زبان $($result.language.detected) با احتمال $($result.language.probability) | $resultPath |
| بازبینی تصویری | PASS؛ $($visualReview.scope.reviewed_frame_count) فریم و $(@($visualReview.verified_visual_observations).Count) مشاهدهٔ ساخت‌یافته | $visualReviewPath |
| برنامهٔ بازشنوی | PASS؛ $(@($mediumPlan.clips).Count) بازهٔ بدون هم‌پوشانی | $mediumPlanPath |
| بازشنوی هدفمند Medium | PASS؛ $($mediumDuration.ToString('hh\:mm\:ss')) معادل $mediumCoverage٪ ویدیو، $($mediumReview.summary.segment_count) قطعه، زمان پردازش $($mediumElapsed.ToString('hh\:mm\:ss')) | $mediumReviewPath |
| ممیزی تکرار Medium | PASS؛ هیچ دنبالهٔ تکراریِ مشکوک از آستانهٔ کنترل عبور نکرد | $mediumRepetitionAuditPath |
| بستهٔ شاهد پرسش‌های صوتی | PASS؛ پرسش‌ها به قطعات Medium تازه و هش‌شده متصل‌اند | $audioQuestionEvidencePath |
| ادغام Small و Medium | PASS؛ $($mergedTranscript.summary.base_segments_replaced) قطعهٔ پایه جایگزین و $($mergedTranscript.summary.merged_segment_count) قطعهٔ نهایی | $mergedTranscriptPath |
| کاربرگ بازبینی تخصصی | DRAFT تولیدشده و مصرف‌شده در بازبینی انسانی | $expertWorkbookJson |
| چک‌لیست تکمیل کارشناسی | PASS؛ $($completionChecklist.summary.total) کنترل و صفر مورد معلق/خطا | $completionChecklistPath |
| ممیزی متقابل بسته | PASS / FINAL_PASS؛ $(@($expertPackAudit.source_manifest).Count) ورودی با هش تازه | $expertPackAuditPath |
| گزارش کارشناسی | PASS و تازه‌تر از شواهد ورودی | $expertJsonPath و $expertMarkdownPath |

## خروجی‌های اصلی

- متن Small: $((Join-Path $OutputDir ($Video.Stem + '.transcript.txt')))
- زیرنویس Small: $((Join-Path $OutputDir ($Video.Stem + '.transcript.srt')))
- بستهٔ بازبینی متن و تصویر: $reviewPack
- پیش‌نویس شاهد‌محور تحلیل: $analysisDraft
- کاربرگ بازبینی تخصصی: $expertWorkbook
- ماتریس پرسش‌های صوتی: $audioMatrix
- واژه‌نامهٔ کنترل‌شده: $glossary
- ماتریس تطبیق با بازسازی قبلی: $deltaMatrix
- سناریوهای UAT طراحی‌شده: $uatScenarios
- چک‌لیست ساختاریافتهٔ تکمیل کارشناسی: $completionChecklistPath
- ممیزی متقابل بستهٔ کارشناسی: $expertPackAuditPath
- رونویسی ادغام‌شدهٔ مرجع تحلیل: $mergedTranscriptPath
- گزارش نهایی کارشناسی: $expertMarkdownPath

## وضعیت دانش

دانش شاهد‌محور این فایل تکمیل و در گزارش کارشناسی PASS تثبیت شده است. هر ادعای وابسته به مجوز، محاسبه، ثبت داده، گردش سند یا رفتار نسخهٔ نصب‌شده که در محیط واقعی آزمون نشده باشد، همچنان صریحاً «نیازمند UAT» محسوب می‌شود.

## گام بعدی

$nextStep
"@
    [System.IO.File]::WriteAllText($reportPath, $body, [System.Text.UTF8Encoding]::new($false))
    Add-QueueEvent -Type 'FILE_COMPLETE' -Data @{
        index = $Video.Index
        title = $Video.Title
        result = $resultPath
        report = $reportPath
        segment_count = $result.summary.segment_count
    }
}

function Prepare-ReviewPack {
    param([hashtable]$Video)
    $source = Join-Path $SourceRoot $Video.File
    $transcript = Join-Path $OutputDir ($Video.Stem + '.transcript.json')
    $reviewDir = Join-Path $ReviewRoot $Video.Stem
    $reviewJson = Join-Path $reviewDir 'review_pack.json'
    if (Test-Path -LiteralPath $reviewJson) {
        try {
            $existing = Get-Content -Raw -LiteralPath $reviewJson | ConvertFrom-Json
            if ($existing.validation -eq 'PASS') { return $reviewJson }
        } catch { }
    }

    New-Item -ItemType Directory -Force -Path $reviewDir | Out-Null
    $stdout = Join-Path $LogDir ($Video.Stem + '.review_pack.stdout.log')
    $stderr = Join-Path $LogDir ($Video.Stem + '.review_pack.stderr.log')
    $sourceArgument = '"' + $source + '"'
    $transcriptArgument = '"' + $transcript + '"'
    $reviewArgument = '"' + $reviewDir + '"'
    $arguments = @(
        $ReviewPacker,
        '--source', $sourceArgument,
        '--transcript', $transcriptArgument,
        '--output-dir', $reviewArgument,
        '--interval-seconds', '180'
    )
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        Add-QueueEvent -Type 'REVIEW_PACK_START' -Data @{ index = $Video.Index; title = $Video.Title; output = $reviewDir; attempt = $attempt }
        try {
            $process = Start-Process -FilePath $Python -ArgumentList $arguments -PassThru -Wait -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
            if ($process.ExitCode -eq 0 -and (Test-Path -LiteralPath $reviewJson)) {
                $payload = Get-Content -Raw -LiteralPath $reviewJson | ConvertFrom-Json
                if ($payload.validation -eq 'PASS') {
                    Add-QueueEvent -Type 'REVIEW_PACK_COMPLETE' -Data @{ index = $Video.Index; output = $reviewDir; frames = $payload.sampling.frame_count; contact_sheets = $payload.sampling.contact_sheet_count; attempt = $attempt }
                    return $reviewJson
                }
            }
            $errorTail = if (Test-Path -LiteralPath $stderr) { (Get-Content -LiteralPath $stderr -Tail 30) -join "`n" } else { '' }
            Add-QueueEvent -Type 'REVIEW_PACK_ATTEMPT_FAILED' -Data @{ index = $Video.Index; attempt = $attempt; exit_code = $process.ExitCode; stderr_tail = $errorTail }
        } catch {
            Add-QueueEvent -Type 'REVIEW_PACK_ATTEMPT_FAILED' -Data @{ index = $Video.Index; attempt = $attempt; error = $_.Exception.Message }
        }
        if ($attempt -lt 3) { Start-Sleep -Seconds 15 }
    }
    Add-QueueEvent -Type 'REVIEW_PACK_FAILED' -Data @{ index = $Video.Index; title = $Video.Title; attempts = 3; output = $reviewDir }
    return $null
}

function Test-PassJson {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    try {
        $payload = Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
        return ($payload.validation -eq 'PASS')
    } catch {
        return $false
    }
}

function Test-PassJsonCurrent {
    param(
        [string]$Path,
        [string[]]$Inputs = @()
    )
    if (-not (Test-PassJson -Path $Path)) { return $false }
    $output = Get-Item -LiteralPath $Path
    foreach ($inputPath in $Inputs) {
        if (-not (Test-Path -LiteralPath $inputPath)) { return $false }
        if ($output.LastWriteTimeUtc -lt (Get-Item -LiteralPath $inputPath).LastWriteTimeUtc) { return $false }
    }
    return $true
}

function Test-MediumReviewCurrent {
    param(
        [string]$Path,
        [string]$Plan,
        [string]$Source,
        [string]$Model = 'medium'
    )
    if (-not (Test-PassJsonCurrent -Path $Path -Inputs @($Plan, $Source))) { return $false }
    try {
        $payload = Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
        $planHash = (Get-FileHash -LiteralPath $Plan -Algorithm SHA256).Hash.ToLowerInvariant()
        $resolvedSource = (Resolve-Path -LiteralPath $Source).Path
        return (
            $payload.plan.sha256 -eq $planHash -and
            $payload.engine.model -eq $Model -and
            $payload.source.path -eq $resolvedSource -and
            [int64]$payload.source.size_bytes -eq (Get-Item -LiteralPath $Source).Length
        )
    } catch {
        return $false
    }
}

function Test-ExpertCompletionChecklist {
    param(
        [string]$Path,
        [string[]]$FreshInputs = @()
    )
    if (-not (Test-PassJsonCurrent -Path $Path -Inputs $FreshInputs)) { return $false }
    try {
        $payload = Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
        $checks = @($payload.checks)
        if ($checks.Count -eq 0) { return $false }
        $allowed = @('PASS', 'NOT_APPLICABLE_WITH_REASON')
        foreach ($check in $checks) {
            if ($allowed -notcontains [string]$check.status) { return $false }
            if ($check.status -eq 'PASS' -and @($check.evidence).Count -eq 0) { return $false }
            if ($check.status -eq 'NOT_APPLICABLE_WITH_REASON' -and [string]::IsNullOrWhiteSpace([string]$check.reason)) { return $false }
        }
        $passCount = @($checks | Where-Object { $_.status -eq 'PASS' }).Count
        $naCount = @($checks | Where-Object { $_.status -eq 'NOT_APPLICABLE_WITH_REASON' }).Count
        return (
            $payload.validation -eq 'PASS' -and
            [int]$payload.summary.total -eq $checks.Count -and
            [int]$payload.summary.pass -eq $passCount -and
            [int]$payload.summary.not_applicable_with_reason -eq $naCount -and
            [int]$payload.summary.pending -eq 0 -and
            [int]$payload.summary.fail -eq 0 -and
            [int]$payload.summary.critical_pending -eq 0 -and
            [int]$payload.summary.critical_fail -eq 0 -and
            ($passCount + $naCount) -eq $checks.Count
        )
    } catch {
        return $false
    }
}

function Test-ExpertReport {
    param(
        [string]$JsonPath,
        [string]$MarkdownPath,
        [hashtable]$Video,
        [string]$ChecklistPath,
        [string[]]$FreshInputs = @()
    )
    $allInputs = @($FreshInputs) + @($ChecklistPath)
    if (-not (Test-PassJsonCurrent -Path $JsonPath -Inputs $allInputs)) { return $false }
    if (-not (Test-Path -LiteralPath $MarkdownPath)) { return $false }
    $latestInput = @($allInputs) | ForEach-Object {
        if (-not (Test-Path -LiteralPath $_)) { throw "Missing expert report input: $_" }
        (Get-Item -LiteralPath $_).LastWriteTimeUtc
    } | Sort-Object -Descending | Select-Object -First 1
    if ((Get-Item -LiteralPath $MarkdownPath).LastWriteTimeUtc -lt $latestInput) { return $false }
    try {
        $payload = Get-Content -Raw -LiteralPath $JsonPath | ConvertFrom-Json
        $checklist = Get-Content -Raw -LiteralPath $ChecklistPath | ConvertFrom-Json
        $markdown = Get-Content -Raw -LiteralPath $MarkdownPath
        $expectedSource = (Resolve-Path -LiteralPath (Join-Path $SourceRoot $Video.File)).Path
        $claims = @($payload.accepted_claims)
        $rejected = @($payload.rejected_claims)
        $unknowns = @($payload.unknowns)
        $chapters = @($payload.chapter_status)
        $evidenceManifest = @($payload.evidence_manifest)
        if ($payload.artifact -ne 'varanegar_video_expert_analysis' -or [int]$payload.schema_version -ne 1) { return $false }
        if ([int]$payload.source.video_index -ne [int]$Video.Index -or $payload.source.output_stem -ne $Video.Stem -or $payload.source.path -ne $expectedSource) { return $false }
        if ([string]$payload.source.sha256 -notmatch '^[0-9a-fA-F]{64}$') { return $false }
        if ($claims.Count -eq 0 -or $chapters.Count -eq 0 -or $evidenceManifest.Count -eq 0) { return $false }
        foreach ($claim in $claims) {
            if ([string]::IsNullOrWhiteSpace([string]$claim.id) -or [string]::IsNullOrWhiteSpace([string]$claim.statement) -or @($claim.evidence).Count -eq 0) { return $false }
        }
        foreach ($unknown in $unknowns) {
            if (@('UNKNOWN_WITH_REASON', 'NEEDS_UAT', 'NOT_APPLICABLE_WITH_REASON') -notcontains [string]$unknown.status) { return $false }
            if ([string]::IsNullOrWhiteSpace([string]$unknown.reason) -or @($unknown.next_evidence).Count -eq 0) { return $false }
        }
        foreach ($chapter in $chapters) {
            if (@('PASS', 'UNKNOWN_WITH_REASON', 'NEEDS_UAT') -notcontains [string]$chapter.status) { return $false }
        }
        foreach ($evidence in $evidenceManifest) {
            if (@('PASS', 'PASS_DESIGN_ONLY', 'UNKNOWN_WITH_REASON', 'NOT_APPLICABLE_WITH_REASON') -notcontains [string]$evidence.status) { return $false }
        }
        if (
            [int]$payload.summary.audio_questions_total -le 0 -or
            [int]$payload.summary.audio_questions_resolved -ne [int]$payload.summary.audio_questions_total -or
            [int]$payload.summary.accepted_claim_count -ne $claims.Count -or
            [int]$payload.summary.rejected_claim_count -ne $rejected.Count -or
            [int]$payload.summary.unknown_with_reason_count -ne $unknowns.Count -or
            [int]$payload.summary.critical_pending_count -ne 0
        ) { return $false }
        if (
            $payload.completion_checklist.validation -ne 'PASS' -or
            [int]$payload.completion_checklist.total -ne [int]$checklist.summary.total -or
            [int]$payload.completion_checklist.pending -ne 0 -or
            [int]$payload.completion_checklist.critical_pending -ne 0
        ) { return $false }
        if (
            $payload.operational_mastery.procedural_knowledge_complete -ne $true -or
            $null -eq $payload.operational_mastery.uat_executed -or
            $null -eq $payload.operational_mastery.operational_execution_certified -or
            [string]::IsNullOrWhiteSpace([string]$payload.operational_mastery.safe_claim)
        ) { return $false }
        if ($markdown.Length -lt 1000 -or $markdown -match 'وضعیت:\s*\*\*DRAFT' -or $markdown -notmatch '##') { return $false }
        return $true
    } catch {
        return $false
    }
}

function Test-ExpertPackAuditCurrent {
    param(
        [string]$Path,
        [string]$RequiredState = 'FINAL_PASS'
    )
    if (-not (Test-PassJson -Path $Path)) { return $false }
    try {
        $audit = Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
        if ($audit.pack_state -ne $RequiredState) { return $false }
        if ($null -eq $script:auditHashCache) { $script:auditHashCache = @{} }
        foreach ($entry in @($audit.source_manifest)) {
            $target = [string]$entry.path
            if (-not (Test-Path -LiteralPath $target)) { return $false }
            $item = Get-Item -LiteralPath $target
            if ([int64]$entry.size_bytes -ne $item.Length) { return $false }
            $cacheKey = "$target|$($item.Length)|$($item.LastWriteTimeUtc.Ticks)"
            if (-not $script:auditHashCache.ContainsKey($cacheKey)) {
                $script:auditHashCache[$cacheKey] = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
            }
            if ($script:auditHashCache[$cacheKey] -ne ([string]$entry.sha256).ToLowerInvariant()) { return $false }
        }
        return @($audit.source_manifest).Count -gt 0
    } catch {
        return $false
    }
}

function Wait-ForVisualReviewPlan {
    param([hashtable]$Video)
    $reviewDir = Join-Path $ReviewRoot $Video.Stem
    $visualReview = Join-Path $reviewDir 'visual_review.json'
    $mediumPlan = Join-Path $reviewDir 'medium_review_plan.json'
    $audioMatrix = Join-Path $reviewDir 'AUDIO_REVIEW_MATRIX_FA.md'
    $glossary = Join-Path $reviewDir 'GLOSSARY_WORKING_FA.md'
    $deltaMatrix = Join-Path $reviewDir 'RECONSTRUCTION_DELTA_MATRIX_FA.md'
    $uatScenarios = Join-Path $reviewDir 'UAT_SCENARIOS_FA.md'
    $completionChecklist = Join-Path $reviewDir 'expert_completion_checklist.json'
    $expertJson = Join-Path (Join-Path $ReportDir 'expert') ($Video.Stem + '_expert_analysis.json')
    $expertMarkdown = Join-Path (Join-Path $ReportDir 'expert') ($Video.Stem + '_expert_analysis_fa.md')
    $workingReport = Join-Path (Join-Path $ReportDir 'expert') ($Video.Stem + '_expert_analysis_working_fa.md')
    Add-QueueEvent -Type 'VISUAL_REVIEW_PLAN_GATE_WAITING' -Data @{ index = $Video.Index; visual_review = $visualReview; medium_plan = $mediumPlan; audio_matrix = $audioMatrix; glossary = $glossary; delta_matrix = $deltaMatrix; uat_scenarios = $uatScenarios; completion_checklist = $completionChecklist; expert_json = $expertJson; expert_markdown = $expertMarkdown; working_report = $workingReport }
    while (-not (
        (Test-PassJson -Path $visualReview) -and
        (Test-PassJson -Path $mediumPlan) -and
        (Test-Path -LiteralPath $audioMatrix) -and
        (Test-Path -LiteralPath $glossary) -and
        (Test-Path -LiteralPath $deltaMatrix) -and
        (Test-Path -LiteralPath $uatScenarios) -and
        (Test-Path -LiteralPath $completionChecklist) -and
        (Test-Path -LiteralPath $expertJson) -and
        (Test-Path -LiteralPath $expertMarkdown) -and
        (Test-Path -LiteralPath $workingReport)
    )) {
        $state = Write-QueueState -Status 'WAITING_VISUAL_REVIEW_PLAN' -CurrentVideo $Video -Attempt 1 -Message 'رونویسی کامل شده است؛ پوشش تصویری، برنامهٔ Medium، ماتریس‌ها، واژه‌نامه، UAT، چک‌لیست و اسکلت گزارش کارشناسی باید آماده شوند.'
        if (((Get-Date) - $script:lastSnapshot).TotalMinutes -ge 60) {
            Write-HourlySnapshot -State $state
            $script:lastSnapshot = Get-Date
        }
        Start-Sleep -Seconds 30
    }
    Add-QueueEvent -Type 'VISUAL_REVIEW_PLAN_GATE_PASSED' -Data @{ index = $Video.Index; visual_review = $visualReview; medium_plan = $mediumPlan; audio_matrix = $audioMatrix; glossary = $glossary; delta_matrix = $deltaMatrix; uat_scenarios = $uatScenarios; completion_checklist = $completionChecklist; expert_json = $expertJson; expert_markdown = $expertMarkdown; working_report = $workingReport }
    return $mediumPlan
}

function Run-MediumReview {
    param([hashtable]$Video)
    $reviewDir = Join-Path $ReviewRoot $Video.Stem
    $result = Join-Path $reviewDir 'medium_review.transcript.json'
    $plan = Join-Path $reviewDir 'medium_review_plan.json'
    $source = Join-Path $SourceRoot $Video.File
    if (Test-MediumReviewCurrent -Path $result -Plan $plan -Source $source -Model 'medium') { return $result }
    $stdout = Join-Path $LogDir ($Video.Stem + '.medium_review.stdout.log')
    $stderr = Join-Path $LogDir ($Video.Stem + '.medium_review.stderr.log')
    $arguments = @(
        $ReviewClipTranscriber,
        '--source', ('"' + $source + '"'),
        '--plan', ('"' + $plan + '"'),
        '--output-dir', ('"' + $reviewDir + '"'),
        '--model-dir', ('"' + $Models + '"'),
        '--model', 'medium',
        '--language', 'fa'
    )
    $validationOutput = & $Python $ReviewClipTranscriber --source $source --plan $plan --output-dir $reviewDir --model-dir $Models --model medium --language fa --validate-only 2>&1
    if ($LASTEXITCODE -ne 0) {
        Add-QueueEvent -Type 'MEDIUM_REVIEW_INPUT_VALIDATION_FAILED' -Data @{ index = $Video.Index; output_tail = (@($validationOutput) | Select-Object -Last 30) -join "`n" }
        throw "Medium review input validation failed for file $($Video.Index)."
    }
    try {
        $validationPayload = (@($validationOutput) | Select-Object -Last 1) | ConvertFrom-Json
    } catch {
        Add-QueueEvent -Type 'MEDIUM_REVIEW_INPUT_VALIDATION_FAILED' -Data @{ index = $Video.Index; error = $_.Exception.Message; output_tail = (@($validationOutput) | Select-Object -Last 30) -join "`n" }
        throw "Medium review input validation returned invalid JSON for file $($Video.Index)."
    }
    if ($validationPayload.validation -ne 'PASS' -or $validationPayload.status -ne 'INPUTS_VALID') {
        Add-QueueEvent -Type 'MEDIUM_REVIEW_INPUT_VALIDATION_FAILED' -Data @{ index = $Video.Index; payload = $validationPayload }
        throw "Medium review input validation did not PASS for file $($Video.Index)."
    }
    Add-QueueEvent -Type 'MEDIUM_REVIEW_INPUT_VALIDATION_PASSED' -Data @{ index = $Video.Index; plan_sha256 = $validationPayload.plan.sha256; clips = $validationPayload.plan.clip_count; review_seconds = $validationPayload.plan.total_review_seconds; model = $validationPayload.engine.model }
    for ($attempt = 1; $attempt -le 2; $attempt++) {
        Add-QueueEvent -Type 'MEDIUM_REVIEW_START' -Data @{ index = $Video.Index; attempt = $attempt; plan = $plan }
        $existing = @(
            Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*transcribe_varanegar_review_clips.py*' -and $_.CommandLine -like ('*' + $Video.Stem + '*') } |
                Select-Object -ExpandProperty ProcessId
        )
        $process = $null
        if ($existing.Count -eq 0) {
            try {
                $process = Start-Process -FilePath $Python -ArgumentList $arguments -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
                $existing = @($process.Id)
            } catch {
                Add-QueueEvent -Type 'MEDIUM_REVIEW_ATTEMPT_FAILED' -Data @{ index = $Video.Index; attempt = $attempt; error = $_.Exception.Message }
                if ($attempt -lt 2) { Start-Sleep -Seconds 30 }
                continue
            }
        } else {
            Add-QueueEvent -Type 'MEDIUM_REVIEW_ATTACH_EXISTING' -Data @{ index = $Video.Index; pids = $existing }
        }
        while (@($existing | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue }).Count -gt 0) {
            $state = Write-QueueState -Status 'RUNNING_MEDIUM_REVIEW' -CurrentVideo $Video -Attempt $attempt -Message 'بازشنوی هدفمند بازه‌های حساس با مدل Medium در حال اجرا است.'
            if (((Get-Date) - $script:lastSnapshot).TotalMinutes -ge 60) {
                Write-HourlySnapshot -State $state
                $script:lastSnapshot = Get-Date
            }
            Start-Sleep -Seconds 30
        }
        if (Test-MediumReviewCurrent -Path $result -Plan $plan -Source $source -Model 'medium') {
            $payload = Get-Content -Raw -LiteralPath $result | ConvertFrom-Json
            Add-QueueEvent -Type 'MEDIUM_REVIEW_COMPLETE' -Data @{ index = $Video.Index; attempt = $attempt; segments = $payload.summary.segment_count; clips = $payload.summary.clips_with_segments }
            return $result
        }
        $errorTail = if (Test-Path -LiteralPath $stderr) { (Get-Content -LiteralPath $stderr -Tail 30) -join "`n" } else { '' }
        Add-QueueEvent -Type 'MEDIUM_REVIEW_ATTEMPT_FAILED' -Data @{ index = $Video.Index; attempt = $attempt; stderr_tail = $errorTail }
        if ($attempt -lt 2) { Start-Sleep -Seconds 30 }
    }
    throw "Medium review failed for file $($Video.Index) after two attempts."
}

function Run-MediumRepetitionAudit {
    param([hashtable]$Video)
    $reviewDir = Join-Path $ReviewRoot $Video.Stem
    $medium = Join-Path $reviewDir 'medium_review.transcript.json'
    $auditPath = Join-Path $reviewDir 'medium_repetition_audit.json'
    if (Test-PassJsonCurrent -Path $auditPath -Inputs @($medium)) { return $auditPath }

    $output = & $Python $TranscriptRepetitionAuditor --transcript $medium --output $auditPath 2>&1
    if ($LASTEXITCODE -ne 0 -or -not (Test-PassJsonCurrent -Path $auditPath -Inputs @($medium))) {
        $auditPayload = $null
        try { $auditPayload = Get-Content -Raw -LiteralPath $auditPath | ConvertFrom-Json } catch { }
        Add-QueueEvent -Type 'MEDIUM_REPETITION_AUDIT_FAILED' -Data @{
            index = $Video.Index
            audit = $auditPath
            suspicious_runs = if ($null -ne $auditPayload) { $auditPayload.summary.suspicious_run_count } else { $null }
            output_tail = (@($output) | Select-Object -Last 30) -join "`n"
        }
        throw "Medium repetition audit failed for file $($Video.Index); transcript is not eligible for merge."
    }
    $payload = Get-Content -Raw -LiteralPath $auditPath | ConvertFrom-Json
    Add-QueueEvent -Type 'MEDIUM_REPETITION_AUDIT_PASSED' -Data @{
        index = $Video.Index
        segments = $payload.summary.segment_count
        suspicious_runs = $payload.summary.suspicious_run_count
        audit = $auditPath
    }
    return $auditPath
}

function Build-AudioQuestionEvidence {
    param([hashtable]$Video)
    $reviewDir = Join-Path $ReviewRoot $Video.Stem
    $matrix = Join-Path $reviewDir 'AUDIO_REVIEW_MATRIX_FA.md'
    $medium = Join-Path $reviewDir 'medium_review.transcript.json'
    $bundle = Join-Path $reviewDir 'audio_question_evidence.json'
    if (Test-PassJsonCurrent -Path $bundle -Inputs @($matrix, $medium)) { return $bundle }
    $output = & $Python $AudioQuestionEvidenceBuilder --matrix $matrix --transcript $medium --output-dir $reviewDir 2>&1
    if ($LASTEXITCODE -ne 0 -or -not (Test-PassJsonCurrent -Path $bundle -Inputs @($matrix, $medium))) {
        Add-QueueEvent -Type 'AUDIO_QUESTION_EVIDENCE_FAILED' -Data @{ index = $Video.Index; output_tail = (@($output) | Select-Object -Last 30) -join "`n" }
        throw "Audio question evidence failed for file $($Video.Index)."
    }
    $payload = Get-Content -Raw -LiteralPath $bundle | ConvertFrom-Json
    Add-QueueEvent -Type 'AUDIO_QUESTION_EVIDENCE_COMPLETE' -Data @{ index = $Video.Index; questions = $payload.summary.question_count; clips = $payload.summary.clip_count; segments = $payload.summary.segment_count; bundle = $bundle }
    return $bundle
}

function Merge-ReviewTranscripts {
    param([hashtable]$Video)
    $reviewDir = Join-Path $ReviewRoot $Video.Stem
    $base = Join-Path $OutputDir ($Video.Stem + '.transcript.json')
    $medium = Join-Path $reviewDir 'medium_review.transcript.json'
    $merged = Join-Path $reviewDir 'review_merged.transcript.json'
    if (Test-PassJsonCurrent -Path $merged -Inputs @($base, $medium)) { return $merged }
    $output = & $Python $TranscriptMerger --base-transcript $base --review-transcript $medium --output-dir $reviewDir 2>&1
    if ($LASTEXITCODE -ne 0 -or -not (Test-PassJsonCurrent -Path $merged -Inputs @($base, $medium))) {
        Add-QueueEvent -Type 'TRANSCRIPT_MERGE_FAILED' -Data @{ index = $Video.Index; output_tail = (@($output) | Select-Object -Last 30) -join "`n" }
        throw "Transcript merge failed for file $($Video.Index)."
    }
    $payload = Get-Content -Raw -LiteralPath $merged | ConvertFrom-Json
    Add-QueueEvent -Type 'TRANSCRIPT_MERGE_COMPLETE' -Data @{ index = $Video.Index; base_replaced = $payload.summary.base_segments_replaced; medium_segments = $payload.summary.review_segment_count; merged_segments = $payload.summary.merged_segment_count }
    return $merged
}

function Build-AnalysisDraft {
    param([hashtable]$Video)
    $reviewDir = Join-Path $ReviewRoot $Video.Stem
    $reviewJson = Join-Path $reviewDir 'review_pack.json'
    $mergedTranscript = Join-Path $reviewDir 'review_merged.transcript.json'
    $transcript = if (Test-PassJson -Path $mergedTranscript) { $mergedTranscript } else { Join-Path $OutputDir ($Video.Stem + '.transcript.json') }
    $draftJson = Join-Path $reviewDir 'analysis_draft.json'
    if (-not (Test-Path -LiteralPath $reviewJson)) {
        Add-QueueEvent -Type 'ANALYSIS_DRAFT_SKIPPED' -Data @{ index = $Video.Index; reason = 'review_pack_missing' }
        return $null
    }
    if (Test-PassJsonCurrent -Path $draftJson -Inputs @($transcript, $reviewJson)) { return $draftJson }

    $stdout = Join-Path $LogDir ($Video.Stem + '.analysis_draft.stdout.log')
    $stderr = Join-Path $LogDir ($Video.Stem + '.analysis_draft.stderr.log')
    $arguments = @(
        $DraftBuilder,
        '--transcript', ('"' + $transcript + '"'),
        '--review-pack', ('"' + $reviewJson + '"'),
        '--output-dir', ('"' + $reviewDir + '"')
    )
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        Add-QueueEvent -Type 'ANALYSIS_DRAFT_START' -Data @{ index = $Video.Index; attempt = $attempt; output = $reviewDir }
        try {
            $process = Start-Process -FilePath $Python -ArgumentList $arguments -PassThru -Wait -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
            if ($process.ExitCode -eq 0 -and (Test-Path -LiteralPath $draftJson)) {
                $payload = Get-Content -Raw -LiteralPath $draftJson | ConvertFrom-Json
                if ($payload.validation -eq 'PASS') {
                    Add-QueueEvent -Type 'ANALYSIS_DRAFT_COMPLETE' -Data @{ index = $Video.Index; attempt = $attempt; output = $draftJson; action_candidates = $payload.summary.action_candidate_count; rule_candidates = $payload.summary.rule_candidate_count }
                    return $draftJson
                }
            }
            $errorTail = if (Test-Path -LiteralPath $stderr) { (Get-Content -LiteralPath $stderr -Tail 30) -join "`n" } else { '' }
            Add-QueueEvent -Type 'ANALYSIS_DRAFT_ATTEMPT_FAILED' -Data @{ index = $Video.Index; attempt = $attempt; exit_code = $process.ExitCode; stderr_tail = $errorTail }
        } catch {
            Add-QueueEvent -Type 'ANALYSIS_DRAFT_ATTEMPT_FAILED' -Data @{ index = $Video.Index; attempt = $attempt; error = $_.Exception.Message }
        }
        if ($attempt -lt 3) { Start-Sleep -Seconds 15 }
    }
    Add-QueueEvent -Type 'ANALYSIS_DRAFT_FAILED' -Data @{ index = $Video.Index; title = $Video.Title; attempts = 3 }
    return $null
}

function Build-ExpertWorkbook {
    param([hashtable]$Video)
    $reviewDir = Join-Path $ReviewRoot $Video.Stem
    $draftJson = Join-Path $reviewDir 'analysis_draft.json'
    $workbookJson = Join-Path $reviewDir 'expert_review_workbook.json'
    if (-not (Test-Path -LiteralPath $draftJson)) {
        Add-QueueEvent -Type 'EXPERT_WORKBOOK_SKIPPED' -Data @{ index = $Video.Index; reason = 'analysis_draft_missing' }
        return $null
    }
    if ((Test-Path -LiteralPath $workbookJson) -and
        (Get-Item -LiteralPath $workbookJson).LastWriteTimeUtc -ge (Get-Item -LiteralPath $draftJson).LastWriteTimeUtc) {
        try {
            $existing = Get-Content -Raw -LiteralPath $workbookJson | ConvertFrom-Json
            if ($existing.validation -eq 'DRAFT') { return $workbookJson }
        } catch { }
    }
    $stdout = Join-Path $LogDir ($Video.Stem + '.expert_workbook.stdout.log')
    $stderr = Join-Path $LogDir ($Video.Stem + '.expert_workbook.stderr.log')
    $arguments = @(
        $WorkbookBuilder,
        '--analysis-draft', ('"' + $draftJson + '"'),
        '--output-dir', ('"' + $reviewDir + '"')
    )
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        Add-QueueEvent -Type 'EXPERT_WORKBOOK_START' -Data @{ index = $Video.Index; attempt = $attempt }
        try {
            $process = Start-Process -FilePath $Python -ArgumentList $arguments -PassThru -Wait -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
            if ($process.ExitCode -eq 0 -and (Test-Path -LiteralPath $workbookJson)) {
                $payload = Get-Content -Raw -LiteralPath $workbookJson | ConvertFrom-Json
                if ($payload.validation -eq 'DRAFT') {
                    Add-QueueEvent -Type 'EXPERT_WORKBOOK_COMPLETE' -Data @{ index = $Video.Index; attempt = $attempt; output = $workbookJson; candidates = $payload.progress.candidate_total; entities = $payload.progress.entity_total }
                    return $workbookJson
                }
            }
            $errorTail = if (Test-Path -LiteralPath $stderr) { (Get-Content -LiteralPath $stderr -Tail 30) -join "`n" } else { '' }
            Add-QueueEvent -Type 'EXPERT_WORKBOOK_ATTEMPT_FAILED' -Data @{ index = $Video.Index; attempt = $attempt; exit_code = $process.ExitCode; stderr_tail = $errorTail }
        } catch {
            Add-QueueEvent -Type 'EXPERT_WORKBOOK_ATTEMPT_FAILED' -Data @{ index = $Video.Index; attempt = $attempt; error = $_.Exception.Message }
        }
        if ($attempt -lt 3) { Start-Sleep -Seconds 15 }
    }
    Add-QueueEvent -Type 'EXPERT_WORKBOOK_FAILED' -Data @{ index = $Video.Index; attempts = 3 }
    return $null
}

function Wait-ForExpertReview {
    param([hashtable]$Video)
    $expertJson = Join-Path (Join-Path $ReportDir 'expert') ($Video.Stem + '_expert_analysis.json')
    $expertMarkdown = Join-Path (Join-Path $ReportDir 'expert') ($Video.Stem + '_expert_analysis_fa.md')
    $reviewDir = Join-Path $ReviewRoot $Video.Stem
    $mediumPlan = Join-Path $reviewDir 'medium_review_plan.json'
    $mediumTranscript = Join-Path $reviewDir 'medium_review.transcript.json'
    $mediumRepetitionAudit = Join-Path $reviewDir 'medium_repetition_audit.json'
    $audioQuestionEvidence = Join-Path $reviewDir 'audio_question_evidence.json'
    $mergedTranscript = Join-Path $reviewDir 'review_merged.transcript.json'
    $expertWorkbook = Join-Path $reviewDir 'expert_review_workbook.json'
    $completionChecklist = Join-Path $reviewDir 'expert_completion_checklist.json'
    $baseTranscript = Join-Path $OutputDir ($Video.Stem + '.transcript.json')
    $source = Join-Path $SourceRoot $Video.File
    Add-QueueEvent -Type 'EXPERT_REVIEW_GATE_WAITING' -Data @{ index = $Video.Index; title = $Video.Title; json = $expertJson; markdown = $expertMarkdown; checklist = $completionChecklist }
    while ($true) {
        $passed = $false
        if ((Test-Path -LiteralPath $expertJson) -and (Test-Path -LiteralPath $expertMarkdown)) {
            try {
                $expertPayload = Get-Content -Raw -LiteralPath $expertJson | ConvertFrom-Json
                $checklistPayload = Get-Content -Raw -LiteralPath $completionChecklist | ConvertFrom-Json
                $workbook = Get-Content -Raw -LiteralPath $expertWorkbook | ConvertFrom-Json
                $auditFinal = $false
                if ($expertPayload.validation -eq 'PASS' -and $checklistPayload.validation -eq 'PASS') {
                    $auditPath = Run-ExpertPackAudit -Video $Video -AllowedStates @('FINAL_PASS')
                    $auditFinal = Test-ExpertPackAuditCurrent -Path $auditPath -RequiredState 'FINAL_PASS'
                }
                $passed = (
                    $auditFinal -and
                    $workbook.validation -eq 'DRAFT' -and
                    (Test-MediumReviewCurrent -Path $mediumTranscript -Plan $mediumPlan -Source $source -Model 'medium') -and
                    (Test-PassJsonCurrent -Path $mediumRepetitionAudit -Inputs @($mediumTranscript)) -and
                    (Test-PassJsonCurrent -Path $audioQuestionEvidence -Inputs @($mediumTranscript, (Join-Path $reviewDir 'AUDIO_REVIEW_MATRIX_FA.md'))) -and
                    (Test-PassJsonCurrent -Path $mergedTranscript -Inputs @($baseTranscript, $mediumTranscript)) -and
                    (Test-ExpertCompletionChecklist -Path $completionChecklist -FreshInputs @($mergedTranscript, $expertWorkbook)) -and
                    (Test-ExpertReport -JsonPath $expertJson -MarkdownPath $expertMarkdown -Video $Video -ChecklistPath $completionChecklist -FreshInputs @($mergedTranscript, $expertWorkbook))
                )
            } catch { $passed = $false }
        }
        if ($passed) {
            Add-QueueEvent -Type 'EXPERT_REVIEW_GATE_PASSED' -Data @{ index = $Video.Index; json = $expertJson; markdown = $expertMarkdown; checklist = $completionChecklist }
            return $expertJson
        }
        $state = Write-QueueState -Status 'WAITING_EXPERT_REVIEW' -CurrentVideo $Video -Attempt 1 -Message 'رونویسی و بستهٔ شواهد کامل شده‌اند؛ چک‌لیست ۱۴کنترلی و گزارش تخصصی باید PASS و تازه باشند و تا آن زمان فایل بعدی آزاد نمی‌شود.'
        if (((Get-Date) - $script:lastSnapshot).TotalMinutes -ge 60) {
            Write-HourlySnapshot -State $state
            $script:lastSnapshot = Get-Date
        }
        Start-Sleep -Seconds 30
    }
}

function Update-KnowledgeLedger {
    try {
        $output = & $Python $LedgerUpdater --repo-root $RepoRoot --video-root $SourceRoot 2>&1
        if ($LASTEXITCODE -ne 0) {
            Add-QueueEvent -Type 'KNOWLEDGE_LEDGER_FAILED' -Data @{ exit_code = $LASTEXITCODE; output_tail = (@($output) | Select-Object -Last 30) -join "`n" }
            return $false
        }
        Add-QueueEvent -Type 'KNOWLEDGE_LEDGER_UPDATED' -Data @{ path = (Join-Path $ArtifactRoot 'knowledge_ledger.json') }
        return $true
    } catch {
        Add-QueueEvent -Type 'KNOWLEDGE_LEDGER_FAILED' -Data @{ error = $_.Exception.Message }
        return $false
    }
}

function Run-ExpertPackAudit {
    param(
        [hashtable]$Video,
        [string[]]$AllowedStates = @('DRAFT_CONSISTENT', 'FINAL_PASS')
    )
    $source = Join-Path $SourceRoot $Video.File
    $output = & $Python $ExpertPackAuditor --artifact-root $ArtifactRoot --stem $Video.Stem --video-index $Video.Index --video-title $Video.Title --source $source 2>&1
    $auditPath = Join-Path (Join-Path $ReviewRoot $Video.Stem) 'expert_pack_audit.json'
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $auditPath)) {
        Add-QueueEvent -Type 'EXPERT_PACK_AUDIT_FAILED' -Data @{ index = $Video.Index; output_tail = (@($output) | Select-Object -Last 30) -join "`n" }
        throw "Expert pack audit failed for file $($Video.Index)."
    }
    try { $audit = Get-Content -Raw -LiteralPath $auditPath | ConvertFrom-Json } catch { throw "Expert pack audit JSON is invalid for file $($Video.Index)." }
    if ($audit.validation -ne 'PASS' -or $AllowedStates -notcontains [string]$audit.pack_state) {
        Add-QueueEvent -Type 'EXPERT_PACK_AUDIT_STATE_REJECTED' -Data @{ index = $Video.Index; validation = $audit.validation; pack_state = $audit.pack_state; allowed_states = $AllowedStates; errors = $audit.errors }
        throw "Expert pack audit state '$($audit.pack_state)' is not allowed for file $($Video.Index)."
    }
    Add-QueueEvent -Type 'EXPERT_PACK_AUDIT_PASSED' -Data @{ index = $Video.Index; pack_state = $audit.pack_state; counts = $audit.counts; path = $auditPath }
    return $auditPath
}

function Complete-VideoKnowledgePipeline {
    param([hashtable]$Video)
    $retryCycle = 0
    while ($true) {
        $retryCycle += 1
        try {
            if ($null -eq (Prepare-ReviewPack -Video $Video)) { throw 'Review pack did not complete.' }
            Wait-ForVisualReviewPlan -Video $Video | Out-Null
            Run-ExpertPackAudit -Video $Video -AllowedStates @('DRAFT_CONSISTENT', 'FINAL_PASS') | Out-Null
            if ($null -eq (Run-MediumReview -Video $Video)) { throw 'Medium review did not complete.' }
            if ($null -eq (Run-MediumRepetitionAudit -Video $Video)) { throw 'Medium repetition audit did not PASS.' }
            if ($null -eq (Build-AudioQuestionEvidence -Video $Video)) { throw 'Audio question evidence did not complete.' }
            if ($null -eq (Merge-ReviewTranscripts -Video $Video)) { throw 'Transcript merge did not complete.' }
            if ($null -eq (Build-AnalysisDraft -Video $Video)) { throw 'Analysis draft did not complete.' }
            if ($null -eq (Build-ExpertWorkbook -Video $Video)) { throw 'Expert workbook did not complete.' }
            Wait-ForExpertReview -Video $Video | Out-Null
            Write-FileCompletionReport -Video $Video
            Update-KnowledgeLedger | Out-Null
            Add-QueueEvent -Type 'KNOWLEDGE_PIPELINE_COMPLETE' -Data @{ index = $Video.Index; title = $Video.Title; retry_cycle = $retryCycle }
            return $true
        } catch {
            $delaySeconds = [math]::Min(900, 60 * $retryCycle)
            Add-QueueEvent -Type 'KNOWLEDGE_PIPELINE_RETRY' -Data @{ index = $Video.Index; title = $Video.Title; retry_cycle = $retryCycle; delay_seconds = $delaySeconds; error = $_.Exception.Message }
            $state = Write-QueueState -Status 'WAITING_RECOVERY' -CurrentVideo $Video -Attempt $retryCycle -Message "چرخهٔ دانش فایل جاری خطا داشت؛ همان فایل پس از وقفه دوباره تلاش می‌شود و فایل بعدی آزاد نشده است."
            if (((Get-Date) - $script:lastSnapshot).TotalMinutes -ge 60) {
                Write-HourlySnapshot -State $state
                $script:lastSnapshot = Get-Date
            }
            Start-Sleep -Seconds $delaySeconds
        }
    }
}

function Test-ExistingFirstProcess {
    param([int]$ProcessId)
    if ($ProcessId -le 0) { return $false }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if ($null -eq $process) { return $false }
    return (
        $process.CommandLine -like '*01_base_information_01*' -or
        $process.CommandLine -like '*run_varanegar_training_video_01.ps1*'
    )
}

New-Item -ItemType Directory -Force -Path $OutputDir, $ReportDir, $HourlyDir, $LogDir, $ReviewRoot | Out-Null
foreach ($required in @($Python, $Transcriber, $ReviewPacker, $DraftBuilder, $WorkbookBuilder, $ReviewClipTranscriber, $TranscriptMerger, $TranscriptRepetitionAuditor, $AudioQuestionEvidenceBuilder, $ExpertPackAuditor, $LedgerUpdater, $Models, $SourceRoot)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required path is missing: $required" }
}
foreach ($video in $Videos) {
    $source = Join-Path $SourceRoot $video.File
    if (-not (Test-Path -LiteralPath $source)) { throw "Training video is missing: $source" }
}

if ($ValidateOnly) {
    [ordered]@{
        validation = 'PASS'
        total_files = $Videos.Count
        source_root = $SourceRoot
        output_directory = $OutputDir
        state_path = $StatePath
    } | ConvertTo-Json
    exit 0
}

Add-QueueEvent -Type 'QUEUE_START' -Data @{ total_files = $Videos.Count; existing_first_pid = $ExistingFirstPid }
$latestHourlyReport = Get-ChildItem -LiteralPath $HourlyDir -File -Filter '*_progress_fa.md' -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
$script:lastSnapshot = if ($null -ne $latestHourlyReport) { $latestHourlyReport.LastWriteTime } else { Get-Date '2000-01-01' }

if (Test-ExistingFirstProcess -ProcessId $ExistingFirstPid) {
    Add-QueueEvent -Type 'ATTACH_EXISTING_PROCESS' -Data @{ index = 1; pid = $ExistingFirstPid }
    while (Test-ExistingFirstProcess -ProcessId $ExistingFirstPid) {
        $state = Write-QueueState -Status 'RUNNING_EXISTING' -CurrentVideo $Videos[0] -Attempt 1 -Message 'پردازش فایل اول از اجرای قبلی در حال ادامه است.'
        if (((Get-Date) - $script:lastSnapshot).TotalMinutes -ge 60) {
            Write-HourlySnapshot -State $state
            $script:lastSnapshot = Get-Date
        }
        Start-Sleep -Seconds 15
    }
    $firstResult = Join-Path $OutputDir ($Videos[0].Stem + '.transcript.json')
    if (Test-Path -LiteralPath $firstResult) {
        try {
            $firstPayload = Get-Content -Raw -LiteralPath $firstResult | ConvertFrom-Json
            if ($firstPayload.validation -eq 'PASS') {
                Complete-VideoKnowledgePipeline -Video $Videos[0] | Out-Null
            }
        } catch {
            Add-QueueEvent -Type 'FIRST_RESULT_READ_FAILED' -Data @{ error = $_.Exception.Message }
        }
    }
}

$failed = @()
foreach ($video in $Videos) {
    $resultPath = Join-Path $OutputDir ($video.Stem + '.transcript.json')
    $alreadyComplete = $false
    if (Test-Path -LiteralPath $resultPath) {
        try {
            $existing = Get-Content -Raw -LiteralPath $resultPath | ConvertFrom-Json
            $alreadyComplete = ($existing.validation -eq 'PASS')
        } catch { $alreadyComplete = $false }
    }
    if ($alreadyComplete) {
        Complete-VideoKnowledgePipeline -Video $video | Out-Null
        continue
    }

    $succeeded = $false
    $transcriptionRetryCycle = 0
    while (-not $succeeded) {
    $transcriptionRetryCycle += 1
    for ($attempt = 1; $attempt -le $MaxAttemptsPerFile; $attempt++) {
        $state = Write-QueueState -Status 'RUNNING' -CurrentVideo $video -Attempt $attempt -Message 'رونویسی ترتیبی در حال اجرا است.'
        Write-HourlySnapshot -State $state
        Add-QueueEvent -Type 'FILE_START' -Data @{ index = $video.Index; title = $video.Title; retry_cycle = $transcriptionRetryCycle; attempt = $attempt }

        $stdout = Join-Path $LogDir ($video.Stem + '.stdout.log')
        $stderr = Join-Path $LogDir ($video.Stem + '.stderr.log')
        $source = Join-Path $SourceRoot $video.File
        $validationOutput = & $Python $Transcriber --input $source --output-dir $OutputDir --output-stem $video.Stem --model-dir $Models --model small --language fa --validate-only 2>&1
        $validationPayload = $null
        if ($LASTEXITCODE -eq 0) {
            try { $validationPayload = (@($validationOutput) | Select-Object -Last 1) | ConvertFrom-Json } catch { $validationPayload = $null }
        }
        if ($null -eq $validationPayload -or $validationPayload.validation -ne 'PASS' -or $validationPayload.status -ne 'INPUTS_VALID') {
            Add-QueueEvent -Type 'TRANSCRIPTION_INPUT_VALIDATION_FAILED' -Data @{ index = $video.Index; retry_cycle = $transcriptionRetryCycle; attempt = $attempt; output_tail = (@($validationOutput) | Select-Object -Last 30) -join "`n" }
            if ($attempt -lt $MaxAttemptsPerFile) { Start-Sleep -Seconds 30 }
            continue
        }
        Add-QueueEvent -Type 'TRANSCRIPTION_INPUT_VALIDATION_PASSED' -Data @{
            index = $video.Index
            retry_cycle = $transcriptionRetryCycle
            attempt = $attempt
            resumed = $validationPayload.checkpoint.resumed
            resume_reason = $validationPayload.checkpoint.reason
            resume_start_seconds = $validationPayload.checkpoint.resume_start_seconds
            checkpoint_segments_reused = $validationPayload.checkpoint.reused_segment_count
        }
        $sourceArgument = '"' + $source + '"'
        $arguments = @(
            $Transcriber,
            '--input', $sourceArgument,
            '--output-dir', $OutputDir,
            '--output-stem', $video.Stem,
            '--model-dir', $Models,
            '--model', 'small',
            '--language', 'fa'
        )
        $process = Start-Process -FilePath $Python -ArgumentList $arguments -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        while (-not $process.HasExited) {
            Start-Sleep -Seconds 15
            $process.Refresh()
            $state = Write-QueueState -Status 'RUNNING' -CurrentVideo $video -Attempt $attempt -Message 'رونویسی ترتیبی در حال اجرا است.'
            if (((Get-Date) - $script:lastSnapshot).TotalMinutes -ge 60) {
                Write-HourlySnapshot -State $state
                $script:lastSnapshot = Get-Date
            }
        }

        if ($process.ExitCode -eq 0 -and (Test-Path -LiteralPath $resultPath)) {
            $result = Get-Content -Raw -LiteralPath $resultPath | ConvertFrom-Json
            if ($result.validation -eq 'PASS') {
                $succeeded = $true
                Complete-VideoKnowledgePipeline -Video $video | Out-Null
                $state = Write-QueueState -Status 'FILE_COMPLETE' -CurrentVideo $video -Attempt $attempt -Message 'فایل کامل شد؛ صف به فایل بعدی می‌رود.'
                Write-HourlySnapshot -State $state -Force
                break
            }
        }

        $errorTail = if (Test-Path -LiteralPath $stderr) { (Get-Content -LiteralPath $stderr -Tail 20) -join "`n" } else { '' }
        Add-QueueEvent -Type 'FILE_ATTEMPT_FAILED' -Data @{ index = $video.Index; retry_cycle = $transcriptionRetryCycle; attempt = $attempt; exit_code = $process.ExitCode; stderr_tail = $errorTail }
        if ($attempt -lt $MaxAttemptsPerFile) { Start-Sleep -Seconds 30 }
    }

    if (-not $succeeded) {
        $delaySeconds = [math]::Min(900, 60 * $transcriptionRetryCycle)
        Add-QueueEvent -Type 'TRANSCRIPTION_RETRY_CYCLE_EXHAUSTED' -Data @{ index = $video.Index; title = $video.Title; retry_cycle = $transcriptionRetryCycle; attempts = $MaxAttemptsPerFile; delay_seconds = $delaySeconds }
        $state = Write-QueueState -Status 'WAITING_RECOVERY' -CurrentVideo $video -Attempt $transcriptionRetryCycle -Message 'رونویسی فایل جاری پس از چند تلاش کامل نشد؛ همان فایل با checkpoint و وقفهٔ افزایشی دوباره تلاش می‌شود.'
        if (((Get-Date) - $script:lastSnapshot).TotalMinutes -ge 60) {
            Write-HourlySnapshot -State $state
            $script:lastSnapshot = Get-Date
        }
        Start-Sleep -Seconds $delaySeconds
    }
    }
}

if ($failed.Count -eq 0) {
    Update-KnowledgeLedger | Out-Null
    $state = Write-QueueState -Status 'COMPLETE' -CurrentVideo $null -Message 'رونویسی اولیهٔ همهٔ ۲۳ فایل کامل شد.'
    Write-HourlySnapshot -State $state -Force
    Add-QueueEvent -Type 'QUEUE_COMPLETE' -Data @{ completed_files = $Videos.Count }
    exit 0
}

$state = Write-QueueState -Status 'COMPLETE_WITH_FAILURES' -CurrentVideo $null -Message ("صف پایان یافت، اما فایل‌های زیر نیازمند تلاش مجدد هستند: " + ($failed -join ', '))
Update-KnowledgeLedger | Out-Null
Write-HourlySnapshot -State $state -Force
Add-QueueEvent -Type 'QUEUE_COMPLETE_WITH_FAILURES' -Data @{ failed_indices = $failed }
exit 1
