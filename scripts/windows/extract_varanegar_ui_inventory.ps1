[CmdletBinding()]
param(
    [string]$ProcessName = "VN.SDS.Container",
    [string]$SafeLabelsPath = "",
    [Parameter(Mandatory = $true)]
    [string]$Output
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$windowReaderSource = @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public static class VaranegarReadOnlyWindowTree
{
    public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumChildWindows(IntPtr hWnd, EnumProc callback, IntPtr lParam);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int max);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetClassName(IntPtr hWnd, StringBuilder text, int max);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool IsWindowEnabled(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern IntPtr GetParent(IntPtr hWnd);

    public static List<string[]> Read(IntPtr root)
    {
        var rows = new List<string[]>();
        EnumChildWindows(root, (handle, ignored) =>
        {
            var title = new StringBuilder(1024);
            var className = new StringBuilder(512);
            GetWindowText(handle, title, title.Capacity);
            GetClassName(handle, className, className.Capacity);
            rows.Add(new[]
            {
                handle.ToInt64().ToString(),
                GetParent(handle).ToInt64().ToString(),
                className.ToString(),
                title.ToString(),
                IsWindowVisible(handle).ToString(),
                IsWindowEnabled(handle).ToString()
            });
            return true;
        }, IntPtr.Zero);
        return rows;
    }
}
'@
Add-Type -TypeDefinition $windowReaderSource

if ([string]::IsNullOrWhiteSpace($SafeLabelsPath)) {
    $SafeLabelsPath = Join-Path $PSScriptRoot "varanegar_ui_safe_labels.json"
}
$parsedSafeLabels = Get-Content -Raw -Encoding UTF8 -LiteralPath $SafeLabelsPath |
    ConvertFrom-Json
$script:SafeUiLabels = [System.Collections.Generic.List[string]]::new()
foreach ($parsedSafeLabel in $parsedSafeLabels) {
    $script:SafeUiLabels.Add([string]$parsedSafeLabel)
}

function Get-Sha256Text {
    param([string]$InputText)

    if ($null -eq $InputText) {
        $InputText = ""
    }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($InputText)
        return ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
}

$script:SafeUiLabelByHash = @{}
foreach ($approvedLabel in $script:SafeUiLabels) {
    $script:SafeUiLabelByHash[(Get-Sha256Text -InputText $approvedLabel)] = $approvedLabel
}

function Get-SafeUiLabel {
    param(
        [string]$Name,
        [string]$ControlType
    )

    if ([string]::IsNullOrWhiteSpace($Name)) {
        return $null
    }
    if ($Name.Length -gt 160 -or $Name -match '[0-9\u06F0-\u06F9]' -or $Name -match '[@\\/]') {
        return $null
    }

    $nameHash = Get-Sha256Text -InputText $Name
    if ($script:SafeUiLabelByHash.ContainsKey($nameHash)) {
        return $script:SafeUiLabelByHash[$nameHash].Trim()
    }
    return $null
}

function Read-Element {
    param([System.Windows.Automation.AutomationElement]$Element)

    try {
        $controlType = $Element.Current.ControlType.ProgrammaticName
        $name = $Element.Current.Name
        $supportedPatterns = @(
            $Element.GetSupportedPatterns() |
                ForEach-Object { $_.ProgrammaticName } |
                Sort-Object -Unique
        )
        return [ordered]@{
            control_type = $controlType
            automation_id = $Element.Current.AutomationId
            class_name = $Element.Current.ClassName
            framework_id = $Element.Current.FrameworkId
            is_enabled = [bool]$Element.Current.IsEnabled
            is_offscreen = [bool]$Element.Current.IsOffscreen
            name_sha256 = Get-Sha256Text -InputText $name
            name_length = if ($null -eq $name) { 0 } else { $name.Length }
            safe_label = Get-SafeUiLabel -Name $name -ControlType $controlType
            supported_patterns = $supportedPatterns
        }
    }
    catch [System.Windows.Automation.ElementNotAvailableException] {
        return $null
    }
    catch [System.InvalidOperationException] {
        return $null
    }
}

function Get-ReadOnlyDescendants {
    param(
        [System.Windows.Automation.AutomationElement]$Element,
        [int]$MaximumElements = 5000
    )

    $result = [System.Collections.Generic.List[System.Windows.Automation.AutomationElement]]::new()
    $queue = [System.Collections.Generic.Queue[System.Windows.Automation.AutomationElement]]::new()
    $children = $Element.FindAll(
        [System.Windows.Automation.TreeScope]::Children,
        [System.Windows.Automation.Condition]::TrueCondition
    )
    for ($index = 0; $index -lt $children.Count; $index++) {
        $queue.Enqueue($children.Item($index))
    }

    while ($queue.Count -gt 0) {
        if ($result.Count -ge $MaximumElements) {
            throw "UI Automation tree exceeded the read-only safety ceiling of $MaximumElements elements."
        }
        $current = $queue.Dequeue()
        $result.Add($current)
        try {
            $children = $current.FindAll(
                [System.Windows.Automation.TreeScope]::Children,
                [System.Windows.Automation.Condition]::TrueCondition
            )
            for ($index = 0; $index -lt $children.Count; $index++) {
                $queue.Enqueue($children.Item($index))
            }
        }
        catch [System.Windows.Automation.ElementNotAvailableException] {
            continue
        }
        catch [System.InvalidOperationException] {
            continue
        }
    }
    return $result.ToArray()
}

$process = @(
    Get-Process -Name $ProcessName -ErrorAction Stop |
        Where-Object { $_.MainWindowHandle -ne 0 }
) | Select-Object -First 1

if ($null -eq $process) {
    throw "No visible $ProcessName process was found. Open and sign in to Varanegar first."
}

$root = [System.Windows.Automation.AutomationElement]::RootElement
$processCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ProcessIdProperty,
    $process.Id
)
$windows = $root.FindAll(
    [System.Windows.Automation.TreeScope]::Children,
    $processCondition
)
Write-Verbose "Discovered $($windows.Count) top-level UI Automation window(s)."

$controls = [System.Collections.Generic.List[object]]::new()
$windowRows = [System.Collections.Generic.List[object]]::new()
$typeCounts = @{}

for ($windowIndex = 0; $windowIndex -lt $windows.Count; $windowIndex++) {
    Write-Verbose "Reading top-level window $($windowIndex + 1) of $($windows.Count)."
    $window = $windows.Item($windowIndex)
    $windowRow = Read-Element -Element $window
    if ($null -ne $windowRow) {
        $controls.Add($windowRow)
    }

    $descendants = @(Get-ReadOnlyDescendants -Element $window)
    Write-Verbose "Window $($windowIndex + 1) exposes $($descendants.Count) descendant(s)."
    $readableDescendants = 0
    for ($index = 0; $index -lt $descendants.Count; $index++) {
        Write-Verbose "Reading descendant $($index + 1) of $($descendants.Count)."
        $row = Read-Element -Element $descendants[$index]
        Write-Verbose "Read descendant $($index + 1) of $($descendants.Count)."
        if ($null -eq $row) {
            continue
        }
        $readableDescendants++
        $controls.Add($row)
        if (-not $typeCounts.ContainsKey($row.control_type)) {
            $typeCounts[$row.control_type] = 0
        }
        $typeCounts[$row.control_type]++
    }

    $windowRows.Add([ordered]@{
        title_sha256 = $windowRow.name_sha256
        title_length = $windowRow.name_length
        safe_title = $windowRow.safe_label
        automation_id = $windowRow.automation_id
        descendant_count = $descendants.Count
        readable_descendant_count = $readableDescendants
    })
}

foreach ($control in $controls) {
    if ($script:SafeUiLabelByHash.ContainsKey($control.name_sha256)) {
        $control.safe_label = $script:SafeUiLabelByHash[$control.name_sha256]
    }
}

$safeLabels = [System.Collections.Generic.List[object]]::new()
foreach ($control in $controls) {
    if ($null -eq $control.safe_label) {
        continue
    }
    $safeLabels.Add([ordered]@{
        control_type = $control.control_type
        safe_label = $control.safe_label
        automation_id = $control.automation_id
        class_name = $control.class_name
        is_enabled = $control.is_enabled
        is_offscreen = $control.is_offscreen
    })
}
$patternCounts = @{}
foreach ($control in $controls) {
    foreach ($pattern in $control.supported_patterns) {
        if (-not $patternCounts.ContainsKey($pattern)) {
            $patternCounts[$pattern] = 0
        }
        $patternCounts[$pattern]++
    }
}

$win32Rows = [System.Collections.Generic.List[object]]::new()
$win32ClassCounts = @{}
$rawWin32Rows = @([VaranegarReadOnlyWindowTree]::Read($process.MainWindowHandle))
$rawWin32ByHandle = @{}
foreach ($rawWindow in $rawWin32Rows) {
    $rawWin32ByHandle[$rawWindow[0]] = $rawWindow
}
foreach ($rawWindow in $rawWin32Rows) {
    $className = $rawWindow[2]
    $title = $rawWindow[3]
    if (-not $win32ClassCounts.ContainsKey($className)) {
        $win32ClassCounts[$className] = 0
    }
    $win32ClassCounts[$className]++
    $titleHash = Get-Sha256Text -InputText $title
    $safeTitle = $null
    if ($script:SafeUiLabelByHash.ContainsKey($titleHash)) {
        $safeTitle = $script:SafeUiLabelByHash[$titleHash]
    }
    $nearestSafeAncestorTitle = $null
    $parentHandle = $rawWindow[1]
    $ancestorDepth = 0
    while ($rawWin32ByHandle.ContainsKey($parentHandle) -and $ancestorDepth -lt 32) {
        $parentRow = $rawWin32ByHandle[$parentHandle]
        $parentTitleHash = Get-Sha256Text -InputText $parentRow[3]
        if ($script:SafeUiLabelByHash.ContainsKey($parentTitleHash)) {
            $nearestSafeAncestorTitle = $script:SafeUiLabelByHash[$parentTitleHash]
            break
        }
        $parentHandle = $parentRow[1]
        $ancestorDepth++
    }
    $win32Rows.Add([ordered]@{
        class_name = $className
        title_sha256 = $titleHash
        title_length = $title.Length
        safe_title = $safeTitle
        nearest_safe_ancestor_title = $nearestSafeAncestorTitle
        is_visible = [System.Convert]::ToBoolean($rawWindow[4])
        is_enabled = [System.Convert]::ToBoolean($rawWindow[5])
    })
}

$artifact = [ordered]@{
    artifact = "varanegar_windows_ui_inventory"
    schema_version = 1
    generated_at = [DateTimeOffset]::Now.ToString("o")
    source = [ordered]@{
        machine_ipv4 = "192.168.1.184"
        process_name = $process.ProcessName
        process_id = $process.Id
        executable_path = $process.Path
        main_window_title_sha256 = Get-Sha256Text -InputText $process.MainWindowTitle
        ui_automation_traversal = "BOUNDED_BREADTH_FIRST_CHILDREN"
        ui_automation_maximum_elements_per_window = 5000
    }
    safety = [ordered]@{
        mode = "READ_ONLY_UI_OBSERVATION"
        invoked_controls = 0
        input_events_sent = 0
        values_set = 0
        win32_messages_sent = 0
        screenshots_persisted = 0
        raw_data_bound_names_persisted = 0
        safe_label_policy = "exact reviewed UTF-8 allowlist; all other names are fingerprint-only"
    }
    summary = [ordered]@{
        top_level_window_count = $windows.Count
        observed_control_count = $controls.Count
        safe_named_control_count = $safeLabels.Count
        win32_child_window_count = $win32Rows.Count
        win32_safe_title_count = @($win32Rows | Where-Object { $null -ne $_.safe_title }).Count
        approved_label_hash_count = $script:SafeUiLabelByHash.Count
        approved_label_hashes = @($script:SafeUiLabelByHash.Keys | Sort-Object)
        control_type_counts = $typeCounts
        supported_pattern_counts = $patternCounts
        win32_class_counts = $win32ClassCounts
    }
    windows = $windowRows
    win32_window_tree = $win32Rows
    safe_named_controls = $safeLabels
}

$outputPath = [System.IO.Path]::GetFullPath($Output)
$outputDirectory = [System.IO.Path]::GetDirectoryName($outputPath)
[System.IO.Directory]::CreateDirectory($outputDirectory) | Out-Null
$json = $artifact | ConvertTo-Json -Depth 12
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outputPath, $json, $utf8NoBom)
Write-Output $outputPath
