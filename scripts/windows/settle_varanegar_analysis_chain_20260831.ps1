param(
    [switch]$SkipOfficialTests
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$Analysis = Join-Path $RepoRoot 'artifacts\varanegar_analysis'
$AuditBuilder = Join-Path $RepoRoot 'scripts\windows\build_varanegar_24h_continuation_consolidated_audit_20260829.py'
$AuditOutput = Join-Path $Analysis 'varanegar_24h_continuation_consolidated_audit_20260829.json'
$CheckpointBuilder = Join-Path $RepoRoot 'scripts\windows\build_varanegar_24h_continuation_consolidated_checkpoint_20260829.py'
$CheckpointOutput = Join-Path $Analysis 'varanegar_24h_continuation_consolidated_checkpoint_20260829.json'
$OfficialRunner = Join-Path $RepoRoot 'scripts\windows\run_varanegar_25h_final_tests.py'
$OfficialResult = Join-Path $Analysis 'varanegar_25h_final_test_result_20260829.json'

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python virtual environment not found: $Python"
}

Push-Location $RepoRoot
try {
    $Exclude = & $Python -c "import importlib.util; p=r'scripts/windows/build_varanegar_24h_continuation_consolidated_audit_20260829.py'; s=importlib.util.spec_from_file_location('m',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(*sorted(m.EXCLUDE),sep='\n')"
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to read the consolidated-audit exclusion set.'
    }

    function Invoke-BuilderPhase([bool]$PostPhase) {
        $Nodes = @{}
        Get-ChildItem -LiteralPath $Analysis -Recurse -File -Filter '*.json' | ForEach-Object {
            $Builder = $null
            foreach ($Candidate in @(
                "scripts/windows/build_$($_.BaseName).py",
                "scripts/windows/build_varanegar_$($_.BaseName).py"
            )) {
                if (Test-Path -LiteralPath $Candidate) {
                    $Builder = $Candidate
                    break
                }
            }
            $Wanted = if ($PostPhase) {
                $_.Name -in $Exclude -and $_.Name -notin @(
                    'varanegar_24h_continuation_consolidated_audit_20260829.json',
                    'varanegar_24h_continuation_consolidated_checkpoint_20260829.json'
                )
            } else {
                $_.Name -notin $Exclude
            }
            if ($Builder -and $Wanted) {
                $Relative = (Resolve-Path -LiteralPath $_.FullName -Relative).Replace('\', '/')
                if ($Relative.StartsWith('./')) {
                    $Relative = $Relative.Substring(2)
                }
                $Nodes[$Relative] = [pscustomobject]@{
                    Relative = $Relative
                    Builder = $Builder
                    SpecialPriority = 0
                    Dependencies = @()
                }
            }
        }

        if (-not $PostPhase) {
            $SpecialNodes = @(
                @{ Relative = 'artifacts/varanegar_analysis/varanegar_15h_final_baseline_bundle_20260829.json'; Builder = 'scripts/windows/build_varanegar_15h_final_bundle_20260829.py'; Priority = 1 },
                @{ Relative = 'artifacts/varanegar_analysis/varanegar_25h_opening_gap_map_20260829.json'; Builder = 'scripts/windows/build_varanegar_25h_gap_map_20260829.py'; Priority = 2 },
                @{ Relative = 'artifacts/varanegar_analysis/varanegar_25h_final_baseline_bundle_20260829.json'; Builder = 'scripts/windows/build_varanegar_25h_final_bundle_20260829.py'; Priority = 3 },
                @{ Relative = 'artifacts/varanegar_analysis/varanegar_24h_continuation_wave01_bundle_20260829.json'; Builder = 'scripts/windows/build_varanegar_24h_continuation_wave01_bundle_20260829.py'; Priority = 4 }
            )
            foreach ($Special in $SpecialNodes) {
                $Nodes[$Special.Relative] = [pscustomobject]@{
                    Relative = $Special.Relative
                    Builder = $Special.Builder
                    SpecialPriority = $Special.Priority
                    Dependencies = @()
                }
            }
        }

        foreach ($Key in @($Nodes.Keys)) {
            $Document = Get-Content -LiteralPath $Key -Raw -Encoding utf8 | ConvertFrom-Json
            $Dependencies = @()
            foreach ($Entry in @($Document.source_manifest) + @($Document.manifest)) {
                if ($Entry -and $Entry.path) {
                    $Dependency = ([string]$Entry.path).Replace('\', '/')
                    if ($Nodes.ContainsKey($Dependency)) {
                        $Dependencies += $Dependency
                    }
                }
            }
            $Nodes[$Key].Dependencies = @($Dependencies | Sort-Object -Unique)
        }

        $Completed = [Collections.Generic.HashSet[string]]::new()
        while ($Completed.Count -lt $Nodes.Count) {
            $Ready = @(
                $Nodes.Values |
                    Where-Object {
                        -not $Completed.Contains($_.Relative) -and
                        @($_.Dependencies | Where-Object { -not $Completed.Contains($_) }).Count -eq 0
                    } |
                    Sort-Object @{ Expression = { $_.SpecialPriority -ne 0 } }, @{ Expression = { $_.SpecialPriority } }, Relative
            )
            if ($Ready.Count -eq 0) {
                $Unresolved = @(
                    $Nodes.Values |
                        Where-Object { -not $Completed.Contains($_.Relative) } |
                        Select-Object -First 12 @{ Name = 'node'; Expression = { $_.Relative } },
                            @{ Name = 'waiting_on'; Expression = { @($_.Dependencies | Where-Object { -not $Completed.Contains($_) }) } }
                )
                throw "Dependency cycle among $($Nodes.Count - $Completed.Count) analysis builders: $($Unresolved | ConvertTo-Json -Compress -Depth 3)"
            }
            $Node = $Ready[0]
            $Arguments = @($Node.Builder)
            if ($Node.Relative -match '15h_final_baseline') {
                $Arguments += @('--test-result', 'artifacts/varanegar_analysis/varanegar_15h_final_test_result_20260829.json')
            }
            if ($Node.Relative -match '25h_final_baseline|24h_continuation_wave01_bundle') {
                $Arguments += @('--test-result', 'artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json')
            }
            $Arguments += @('--output', $Node.Relative)
            $BuilderOutput = & $Python @Arguments 2>&1
            if ($LASTEXITCODE -ne 0) {
                $BuilderOutput
                throw "Builder failed: $($Node.Builder) -> $($Node.Relative)"
            }
            [void]$Completed.Add($Node.Relative)
        }
        return $Completed.Count
    }

    function Invoke-SettlementPass {
        $BaseCount = Invoke-BuilderPhase $false
        $AuditLog = & $Python $AuditBuilder --output $AuditOutput 2>&1
        if ($LASTEXITCODE -ne 0) {
            $AuditLog
            throw 'Consolidated audit builder failed.'
        }
        $CheckpointLog = & $Python $CheckpointBuilder --output $CheckpointOutput 2>&1
        if ($LASTEXITCODE -ne 0) {
            $CheckpointLog
            throw 'Consolidated checkpoint builder failed.'
        }
        $PostCount = Invoke-BuilderPhase $true
        return [pscustomobject]@{ BaseBuilderCount = $BaseCount; PostBuilderCount = $PostCount }
    }

    $First = Invoke-SettlementPass
    $Official = $null
    $Second = $null
    if (-not $SkipOfficialTests) {
        $RunnerLog = & $Python $OfficialRunner --output $OfficialResult 2>&1
        if ($LASTEXITCODE -ne 0) {
            $RunnerLog
            throw 'Official Varanegar test runner failed.'
        }
        $Official = Get-Content -LiteralPath $OfficialResult -Raw -Encoding utf8 | ConvertFrom-Json
        $Second = Invoke-SettlementPass
    }
    [pscustomobject]@{
        Validation = 'PASS'
        FirstPass = $First
        OfficialTestsExecuted = -not $SkipOfficialTests
        OfficialTestFileCount = if ($Official) { $Official.runner.test_file_count } else { $null }
        OfficialPassedTestCount = if ($Official) { $Official.runner.passed_test_count } else { $null }
        OfficialBootstrapExclusionCount = if ($Official) { $Official.runner.bootstrap_excluded_test_file_count } else { $null }
        SecondPass = $Second
    } | ConvertTo-Json -Depth 4
} finally {
    Pop-Location
}
