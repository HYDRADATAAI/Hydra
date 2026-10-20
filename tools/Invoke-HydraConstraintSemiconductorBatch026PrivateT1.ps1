param(
    [ValidateSet("ContractCheck","Prep","Status","Materialize","Verify","All")]
    [string]$Mode = "ContractCheck",

    [string]$RepoRoot,
    [string]$PrivateRoot = "D:\HYDRA\_PRIVATE\constraint\raw",
    [string]$InboxRoot = "D:\HYDRA\_PRIVATE\constraint\capture_inbox\semiconductor_batch026",
    [string]$HandbackRoot = "D:\HYDRA\_PRIVATE\constraint\handback"
)

$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Host "BATCH027_WORKSTATION_LAUNCHER=FAIL"
    Write-Host ("ERROR=" + $Message)
    exit 1
}

function Require-Path([string]$PathValue, [string]$Label) {
    if (-not (Test-Path -LiteralPath $PathValue)) {
        Fail ("Missing " + $Label + ": " + $PathValue)
    }
}

if (-not $RepoRoot) {
    $RepoRoot = Join-Path $PSScriptRoot ".."
}
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)

$QueuePath = Join-Path $RepoRoot "docs\constraint\second_slice\semiconductor_advanced_packaging_critical_materials_v1\HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json"
$QuarantinePath = Join-Path $RepoRoot "docs\constraint\second_slice\semiconductor_advanced_packaging_critical_materials_v1\HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_MICRON_SOURCE_QUARANTINE_V001_20260927.json"
$Materializer = Join-Path $RepoRoot "tools\materialize_constraint_second_slice_batch026_private_t1.py"
$Verifier = Join-Path $RepoRoot "tools\verify_constraint_second_slice_batch026_private_t1.py"
$HandbackBuilder = Join-Path $RepoRoot "tools\build_constraint_second_slice_batch026_private_t1_handback.py"

Require-Path $QueuePath "Batch026 queue"
Require-Path $Materializer "Batch026 materializer"
Require-Path $Verifier "Batch026 verifier"
Require-Path $HandbackBuilder "Batch026 handback builder"

$queueDoc = Get-Content -LiteralPath $QueuePath -Raw | ConvertFrom-Json
if ($queueDoc.source_count -ne 41) { Fail "Queue source_count must be 41." }
if ($queueDoc.queue.Count -ne 41) { Fail "Queue must contain 41 capture intents." }

Require-Path $QuarantinePath "Batch030 Micron quarantine"
$quarantineDoc = Get-Content -LiteralPath $QuarantinePath -Raw | ConvertFrom-Json
if ($quarantineDoc.schema_version -ne "hydra-constraint-second-slice-source-quarantine/v1") { Fail "Batch030 quarantine schema drifted." }
if ($quarantineDoc.record_id -ne "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_MICRON_SOURCE_QUARANTINE_V001") { Fail "Batch030 quarantine record drifted." }
if ($quarantineDoc.slice_id -ne "SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1") { Fail "Batch030 quarantine slice drifted." }
if ($quarantineDoc.predecessor_artifacts_mutated -ne $false -or $quarantineDoc.retry_authorized -ne $false) { Fail "Batch030 quarantine mutation/retry policy drifted." }
$expectedQuarantineIds = @(
    "SRC-SEMI-MICRON-Q2FY25-REMARKS-2025-03-20",
    "SRC-SEMI-B021-MICRON-Q1FY26-REMARKS-2025-12-17",
    "SRC-SEMI-B021-MICRON-Q3FY24-REMARKS-2024-06-26",
    "SRC-SEMI-B021-MICRON-Q3FY25-REMARKS-2025-06-25",
    "SRC-SEMI-B021-MICRON-Q4FY25-REMARKS-2025-09-23",
    "SRC-SEMI-B022-GLOBENEWSWIRE-MICRON-HBM3E-2024-02-26",
    "SRC-SEMI-B022-MICRON-HBM3E-VOLUME-2024-02-26",
    "SRC-SEMI-B023-MICRON-Q1FY24-REMARKS-2023-12-20",
    "SRC-SEMI-B023-MICRON-Q2FY26-MARKET-OUTLOOK-2026-03-18"
)
$quarantineIds = @($quarantineDoc.quarantined)
if ($quarantineIds.Count -ne 9 -or @($quarantineIds | Sort-Object -Unique).Count -ne 9) { Fail "Batch030 quarantine must contain exactly 9 unique source IDs." }
if (@(Compare-Object -ReferenceObject $expectedQuarantineIds -DifferenceObject $quarantineIds -CaseSensitive).Count -ne 0) { Fail "Batch030 quarantine source-ID set drifted." }
$queueIds = @($queueDoc.queue | ForEach-Object { $_.source_id })
if (@($expectedQuarantineIds | Where-Object { $_ -cnotin $queueIds }).Count -ne 0) { Fail "Batch026 queue/quarantine membership drifted." }

$origin = ""
try {
    $origin = (git -C $RepoRoot remote get-url origin 2>$null)
} catch {}
if ($origin -and ($origin -notmatch "HYDRADATAAI/Hydra")) {
    Fail ("Repo origin mismatch: " + $origin)
}

if ($Mode -ne "ContractCheck") {
    Fail ("SUPERSEDED_BY_BATCH030_QUARANTINE: Batch026 " + $Mode + " is closed; quarantined source IDs=" + ($expectedQuarantineIds -join ","))
}

if ($Mode -eq "ContractCheck") {
    Write-Host "BATCH027_WORKSTATION_LAUNCHER_CONTRACT_CHECK=PASS"
    Write-Host "QUEUE_SOURCE_COUNT=41"
    Write-Host "MATERIALIZER_PRESENT=YES"
    Write-Host "VERIFIER_PRESENT=YES"
    Write-Host "HANDBACK_BUILDER_PRESENT=YES"
    Write-Host "NETWORK_ACQUISITION=NO"
    Write-Host "BATCH026_OPERATIONAL_MODES=CLOSED"
    exit 0
}

$PrivateRoot = [System.IO.Path]::GetFullPath($PrivateRoot)
$InboxRoot = [System.IO.Path]::GetFullPath($InboxRoot)
$HandbackRoot = [System.IO.Path]::GetFullPath($HandbackRoot)

if (($PrivateRoot -eq $RepoRoot) -or $PrivateRoot.StartsWith($RepoRoot + [System.IO.Path]::DirectorySeparatorChar)) {
    Fail "Private raw root must be outside public repository."
}
if (($InboxRoot -eq $RepoRoot) -or $InboxRoot.StartsWith($RepoRoot + [System.IO.Path]::DirectorySeparatorChar)) {
    Fail "Private inbox root must be outside public repository."
}
if (($HandbackRoot -eq $RepoRoot) -or $HandbackRoot.StartsWith($RepoRoot + [System.IO.Path]::DirectorySeparatorChar)) {
    Fail "Private handback root must be outside public repository."
}

if ($Mode -eq "Prep") {
    New-Item -ItemType Directory -Force -Path $InboxRoot | Out-Null
    New-Item -ItemType Directory -Force -Path $HandbackRoot | Out-Null

    $checklist = @()
    foreach ($item in $queueDoc.queue) {
        $capturePath = Join-Path $InboxRoot $item.inbox_filename
        $sidecarPath = $capturePath + ".capture.json"
        $expectedSidecarPath = $capturePath + ".expected.capture.json"

        $expected = [ordered]@{
            schema_version = "hydra-semiconductor-private-capture-sidecar/v1"
            capture_intent_id = $item.capture_intent_id
            source_id = $item.source_id
            source_version_id = $item.source_version_id
            source_locator = $item.source_locator
            capture_completed_at = "REPLACE_WITH_ACTUAL_OFFSET_AWARE_CAPTURE_TIMESTAMP"
            content_type = $item.content_type_hint
            processing_disposition = "ELIGIBLE"
            historical_backdating_authorized = $false
        }

        if (-not (Test-Path -LiteralPath $expectedSidecarPath)) {
            ($expected | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $expectedSidecarPath -Encoding UTF8
        }

        $checklist += [pscustomobject]@{
            ordinal = $item.ordinal
            capture_intent_id = $item.capture_intent_id
            source_id = $item.source_id
            source_version_id = $item.source_version_id
            publisher = $item.publisher
            title = $item.title
            source_locator = $item.source_locator
            expected_capture_path = $capturePath
            expected_sidecar_path = $sidecarPath
            expected_template_path = $expectedSidecarPath
            content_type_hint = $item.content_type_hint
            reviewed_available_at_reference_only = $item.reviewed_available_at
            capture_file_present = (Test-Path -LiteralPath $capturePath)
            capture_sidecar_present = (Test-Path -LiteralPath $sidecarPath)
        }
    }

    $checklistPath = Join-Path $InboxRoot "HYDRA_CONSTRAINT_SEMI_B026_CAPTURE_CHECKLIST_V001.csv"
    $checklist | Export-Csv -LiteralPath $checklistPath -NoTypeInformation -Encoding UTF8

    $instructions = @"
HYDRA CONSTRAINT SEMICONDUCTOR BATCH026 PRIVATE CAPTURE

1. Capture each URL in the checklist through the authorized browser/manual acquisition path.
2. Save bytes to the exact expected_capture_path.
3. Create the exact .capture.json sidecar beside each capture file.
4. Set capture_completed_at to the actual offset-aware capture timestamp.
5. Do NOT copy reviewed_available_at into the sidecar.
6. Run:
   powershell -ExecutionPolicy Bypass -File "$($MyInvocation.MyCommand.Path)" -Mode Status
7. When Status passes, run:
   powershell -ExecutionPolicy Bypass -File "$($MyInvocation.MyCommand.Path)" -Mode All

No network acquisition is performed by the T1 materializer or this launcher.
"@
    $instructionsPath = Join-Path $InboxRoot "HYDRA_CONSTRAINT_SEMI_B026_PRIVATE_CAPTURE_INSTRUCTIONS_V001.txt"
    Set-Content -LiteralPath $instructionsPath -Value $instructions -Encoding UTF8

    Write-Host "BATCH027_WORKSTATION_PREP=PASS"
    Write-Host ("INBOX_ROOT=" + $InboxRoot)
    Write-Host ("CHECKLIST=" + $checklistPath)
    Write-Host "EXPECTED_CAPTURE_INTENTS=41"
    exit 0
}

if ($Mode -eq "Status") {
    & python $Materializer --repo-root $RepoRoot --private-root $PrivateRoot --inbox-root $InboxRoot --dry-run
    exit $LASTEXITCODE
}

if ($Mode -eq "Materialize") {
    & python $Materializer --repo-root $RepoRoot --private-root $PrivateRoot --inbox-root $InboxRoot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "BATCH027_WORKSTATION_MATERIALIZE=PASS"
    exit 0
}

if ($Mode -eq "Verify") {
    & python $Verifier --repo-root $RepoRoot --private-root $PrivateRoot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    New-Item -ItemType Directory -Force -Path $HandbackRoot | Out-Null
    $handbackPath = Join-Path $HandbackRoot "HYDRA_CONSTRAINT_SEMI_B026_PRIVATE_T1_HANDBACK_V001.json"
    & python $HandbackBuilder --repo-root $RepoRoot --private-root $PrivateRoot --output-path $handbackPath
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "BATCH027_WORKSTATION_VERIFY=PASS"
    Write-Host ("HANDBACK_PATH=" + $handbackPath)
    exit 0
}

if ($Mode -eq "All") {
    & python $Materializer --repo-root $RepoRoot --private-root $PrivateRoot --inbox-root $InboxRoot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & python $Verifier --repo-root $RepoRoot --private-root $PrivateRoot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    New-Item -ItemType Directory -Force -Path $HandbackRoot | Out-Null
    $handbackPath = Join-Path $HandbackRoot "HYDRA_CONSTRAINT_SEMI_B026_PRIVATE_T1_HANDBACK_V001.json"
    & python $HandbackBuilder --repo-root $RepoRoot --private-root $PrivateRoot --output-path $handbackPath
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "BATCH027_WORKSTATION_ALL=PASS"
    Write-Host ("HANDBACK_PATH=" + $handbackPath)
    exit 0
}

Fail ("Unsupported mode: " + $Mode)
