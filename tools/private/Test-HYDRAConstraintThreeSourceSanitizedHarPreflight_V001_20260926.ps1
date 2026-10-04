[CmdletBinding()]
param(
    [string]$RepoRoot,

    [string]$LbnlHar = "D:\HYDRA_PRIVATE\constraint\metadata\lbnl-queued-up-sanitized.har",

    [string]$FercHar = "D:\HYDRA_PRIVATE\constraint\metadata\ferc-order-2023-sanitized.har",

    [string]$PjmHar = "D:\HYDRA_PRIVATE\constraint\metadata\pjm-2025-year-review-sanitized.har",

    [string]$SummaryOutput = "D:\HYDRA_PRIVATE\constraint\metadata\three-source-har-preflight-summary.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $RepoRoot) {
    $RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
} else {
    $RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
}

$Tool = Join-Path $RepoRoot "tools\private\Test-HYDRAConstraintThreeSourceSanitizedHarPreflight_V001_20260926.py"
if (-not (Test-Path -LiteralPath $Tool -PathType Leaf)) {
    throw "Three-HAR preflight tool not found: $Tool"
}

$paths = @(
    @{ Label = "LBNL HAR"; Path = $LbnlHar },
    @{ Label = "FERC HAR"; Path = $FercHar },
    @{ Label = "PJM HAR"; Path = $PjmHar }
)

foreach ($entry in $paths) {
    if (-not (Test-Path -LiteralPath $entry.Path -PathType Leaf)) {
        throw "$($entry.Label) not found: $($entry.Path)"
    }
}

& python $Tool `
    --lbnl-har $LbnlHar `
    --ferc-har $FercHar `
    --pjm-har $PjmHar `
    --public-repo-root $RepoRoot `
    --summary-output $SummaryOutput

if ($LASTEXITCODE -ne 0) {
    throw "Three-source sanitized HAR preflight failed with exit code $LASTEXITCODE"
}

Write-Host "HYDRA_THREE_SOURCE_HAR_PREFLIGHT_WRAPPER=PASS"
Write-Host "SUMMARY_OUTPUT=$SummaryOutput"
Write-Host "CAPTURE_PLAN_CREATED=NO"
Write-Host "T1_OBJECTS_CREATED=NO"
Write-Host "T1_RELEASE_CREATED=NO"
