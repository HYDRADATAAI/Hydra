[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [switch]$AuthorizedPublicAcquisition,

    [ValidateSet("auto", "chrome", "msedge")]
    [string]$Browser = "auto",

    [ValidateSet("exact", "same-origin")]
    [string]$RedirectPolicy = "exact",

    [switch]$Headless,

    [int]$ChallengeWaitSeconds = 180,

    [int]$NavigationTimeoutSeconds = 90,

    [int]$BrowserRestartRetries = 2,

    [string]$RepoRoot,

    [string]$PrivateRoot = "D:\HYDRA_PRIVATE\constraint",

    [string]$InboxRoot = "D:\HYDRA_PRIVATE\constraint\capture_inbox\semiconductor_batch026",

    [string]$BootstrapPython = "python",

    [switch]$Fresh,

    [switch]$NoBootstrap
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $RepoRoot) {
    $RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
}
else {
    $RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
}

$Runner = Join-Path $RepoRoot "tools\private\HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE_V001_20260927.py"
$Requirements = Join-Path $RepoRoot "tools\private\HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE_REQUIREMENTS_V001_20260927.txt"
$QueuePath = Join-Path $RepoRoot "docs\constraint\second_slice\semiconductor_advanced_packaging_critical_materials_v1\HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json"
$QuarantinePath = Join-Path $RepoRoot "docs\constraint\second_slice\semiconductor_advanced_packaging_critical_materials_v1\HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_MICRON_SOURCE_QUARANTINE_V001_20260927.json"
$RuntimeRoot = Join-Path $PrivateRoot "browser-runtime"
$VenvRoot = Join-Path $RuntimeRoot "playwright-venv"
$VenvPython = Join-Path $VenvRoot "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $QueuePath -PathType Leaf)) {
    throw "Batch026 historical queue not found: $QueuePath"
}
if (-not (Test-Path -LiteralPath $QuarantinePath -PathType Leaf)) {
    throw "Batch030 Micron quarantine not found: $QuarantinePath"
}
$queueDoc = Get-Content -LiteralPath $QueuePath -Raw | ConvertFrom-Json
$quarantineDoc = Get-Content -LiteralPath $QuarantinePath -Raw | ConvertFrom-Json
if ($queueDoc.source_count -ne 41 -or $queueDoc.queue.Count -ne 41) {
    throw "Batch026 historical queue identity drifted."
}
if ($quarantineDoc.schema_version -ne "hydra-constraint-second-slice-source-quarantine/v1" -or
    $quarantineDoc.record_id -ne "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_MICRON_SOURCE_QUARANTINE_V001" -or
    $quarantineDoc.slice_id -ne "SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1" -or
    $quarantineDoc.predecessor_artifacts_mutated -ne $false -or
    $quarantineDoc.retry_authorized -ne $false) {
    throw "Batch030 Micron quarantine identity or policy drifted."
}
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
if ($quarantineIds.Count -ne 9 -or @($quarantineIds | Sort-Object -Unique).Count -ne 9) {
    throw "Batch030 Micron quarantine must contain exactly 9 unique source IDs."
}
if (@(Compare-Object -ReferenceObject $expectedQuarantineIds -DifferenceObject $quarantineIds -CaseSensitive).Count -ne 0) {
    throw "Batch030 Micron quarantine source-ID set drifted."
}
$queueIds = @($queueDoc.queue | ForEach-Object { $_.source_id })
if (@($expectedQuarantineIds | Where-Object { $_ -cnotin $queueIds }).Count -ne 0) {
    throw "Batch026 queue/quarantine membership drifted."
}

Write-Host "HYDRA_CONSTRAINT_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE=FAIL"
Write-Host "ERROR=SUPERSEDED_BY_BATCH030_QUARANTINE: Batch026 browser capture is closed."
exit 1

if (-not (Test-Path -LiteralPath $Runner -PathType Leaf)) {
    throw "Semiconductor Batch026 browser capture runner not found: $Runner"
}
if (-not (Test-Path -LiteralPath $Requirements -PathType Leaf)) {
    throw "Semiconductor Batch026 browser capture requirements not found: $Requirements"
}

New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null

if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
    if ($NoBootstrap) {
        throw "Private Playwright runtime is absent and -NoBootstrap was specified."
    }
    & $BootstrapPython -m venv $VenvRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create private Playwright virtual environment."
    }
}

$PlaywrightPackageMarker = Join-Path $VenvRoot "Lib\site-packages\playwright\__init__.py"
if (-not (Test-Path -LiteralPath $PlaywrightPackageMarker -PathType Leaf)) {
    if ($NoBootstrap) {
        throw "Playwright is absent from the private runtime and -NoBootstrap was specified."
    }

    $PreviousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $VenvPython -m pip install --disable-pip-version-check --requirement $Requirements
        $PipExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }

    if ($PipExitCode -ne 0) {
        throw "Unable to install Playwright into the private runtime (exit code $PipExitCode)."
    }
    if (-not (Test-Path -LiteralPath $PlaywrightPackageMarker -PathType Leaf)) {
        throw "Playwright installation completed but package marker is missing: $PlaywrightPackageMarker"
    }
}

$Arguments = @(
    $Runner,
    "--authorized-public-acquisition",
    "--repo-root", $RepoRoot,
    "--private-root", $PrivateRoot,
    "--inbox-root", $InboxRoot,
    "--browser", $Browser,
    "--redirect-policy", $RedirectPolicy,
    "--challenge-wait-seconds", [string]$ChallengeWaitSeconds,
    "--navigation-timeout-seconds", [string]$NavigationTimeoutSeconds,
    "--browser-restart-retries", [string]$BrowserRestartRetries
)

if ($Headless) {
    $Arguments += "--headless"
}
if ($Fresh) {
    $Arguments += "--fresh"
}

Write-Host "HYDRA_CONSTRAINT_SEMICONDUCTOR_BATCH026_BROWSER_BOOTSTRAP=READY"
Write-Host ("REPO_ROOT=" + $RepoRoot)
Write-Host ("PRIVATE_ROOT=" + $PrivateRoot)
Write-Host ("INBOX_ROOT=" + $InboxRoot)
Write-Host ("PYTHON=" + $VenvPython)
Write-Host ("BROWSER=" + $Browser)
Write-Host ("REDIRECT_POLICY=" + $RedirectPolicy)
Write-Host "STARTING_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE=YES"

& $VenvPython @Arguments
exit $LASTEXITCODE
