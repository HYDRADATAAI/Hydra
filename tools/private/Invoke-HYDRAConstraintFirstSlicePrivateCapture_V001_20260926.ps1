[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [switch]$AuthorizedPublicAcquisition,

    [string]$RepoRoot,

    [string]$PrivateRawRoot = "D:\HYDRA_PRIVATE\constraint\raw",

    [string]$PrivateStagingRoot = "D:\HYDRA_PRIVATE\constraint\capture-staging",

    [string]$PrivateMetadataRoot = "D:\HYDRA_PRIVATE\constraint\metadata",

    [string]$LbnlQueuedUpSanitizedHarPath,

    [string]$FercOrder2023SanitizedHarPath,

    [string]$Pjm2025YearInReviewSanitizedHarPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-UtcTimestamp {
    return (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ")
}

function Get-SafeTimestamp {
    return (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
}

function Assert-OutsideRepo {
    param(
        [Parameter(Mandatory = $true)][string]$CandidatePath,
        [Parameter(Mandatory = $true)][string]$RepositoryPath,
        [Parameter(Mandatory = $true)][string]$Label
    )

    $candidate = [System.IO.Path]::GetFullPath($CandidatePath)
    $repo = [System.IO.Path]::GetFullPath($RepositoryPath)

    if (
        $candidate.Equals($repo, [System.StringComparison]::OrdinalIgnoreCase) -or
        $candidate.StartsWith($repo.TrimEnd("\") + "\", [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "$Label must remain outside the public repository: $candidate"
    }
}

if (-not $AuthorizedPublicAcquisition) {
    throw "Explicit -AuthorizedPublicAcquisition is required. This helper performs operator-invoked public network acquisition."
}

if (-not $RepoRoot) {
    $RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
} else {
    $RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
}

$RegistryPath = Join-Path $RepoRoot "docs\constraint\first_slice\ai_data_center_power_infrastructure_v1\HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json"
$MaterializerSrc = Join-Path $RepoRoot "constraint-t1-raw-artifact-store\src"
$AttestationValidator = Join-Path $RepoRoot "tools\validate_constraint_t1_first_slice_attestation.py"

if (-not (Test-Path -LiteralPath $RegistryPath -PathType Leaf)) {
    throw "Authoritative source registry not found: $RegistryPath"
}
if (-not (Test-Path -LiteralPath $MaterializerSrc -PathType Container)) {
    throw "T1 materializer source directory not found: $MaterializerSrc"
}
if (-not (Test-Path -LiteralPath $AttestationValidator -PathType Leaf)) {
    throw "Sanitized attestation validator not found: $AttestationValidator"
}

Assert-OutsideRepo -CandidatePath $PrivateRawRoot -RepositoryPath $RepoRoot -Label "PrivateRawRoot"
Assert-OutsideRepo -CandidatePath $PrivateStagingRoot -RepositoryPath $RepoRoot -Label "PrivateStagingRoot"
Assert-OutsideRepo -CandidatePath $PrivateMetadataRoot -RepositoryPath $RepoRoot -Label "PrivateMetadataRoot"

New-Item -ItemType Directory -Path $PrivateRawRoot -Force | Out-Null
New-Item -ItemType Directory -Path $PrivateStagingRoot -Force | Out-Null
New-Item -ItemType Directory -Path $PrivateMetadataRoot -Force | Out-Null

$Registry = Get-Content -LiteralPath $RegistryPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Registry.slice_id -ne "AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1") {
    throw "Unexpected registry slice_id: $($Registry.slice_id)"
}
if ($null -eq $Registry.sources -or @($Registry.sources).Count -ne 9) {
    throw "Expected exactly nine registered first-slice sources."
}

$SourceIds = @($Registry.sources | ForEach-Object { $_.source_id })
if (($SourceIds | Sort-Object -Unique).Count -ne 9) {
    throw "Registered source IDs are not unique."
}

$RunStamp = Get-SafeTimestamp
$CaptureDir = Join-Path $PrivateStagingRoot $RunStamp
New-Item -ItemType Directory -Path $CaptureDir -Force | Out-Null

$BrowserHarFallbacks = @{
    "SRC-LBNL-QUEUED-UP-2025" = @{
        HarPath = $LbnlQueuedUpSanitizedHarPath
        ExpectedText = "Queued Up: 2025 Edition"
        MetadataStem = "LBNL_QUEUED_UP"
        HarParameter = "-LbnlQueuedUpSanitizedHarPath"
    }
    "SRC-FERC-ORDER-2023-FACT-SHEET" = @{
        HarPath = $FercOrder2023SanitizedHarPath
        ExpectedText = "Fact Sheet | Improvements to Generator Interconnection Procedures and Agreements"
        MetadataStem = "FERC_ORDER_2023_FACT_SHEET"
        HarParameter = "-FercOrder2023SanitizedHarPath"
    }
    "SRC-PJM-2025-YEAR-IN-REVIEW-2026-01-08" = @{
        HarPath = $Pjm2025YearInReviewSanitizedHarPath
        ExpectedText = "2025 Year in Review: Planning Prepares for Burgeoning Electricity Demand"
        MetadataStem = "PJM_2025_YEAR_IN_REVIEW"
        HarParameter = "-Pjm2025YearInReviewSanitizedHarPath"
    }
}

$Captures = @()

foreach ($Source in $Registry.sources) {
    $SourceId = [string]$Source.source_id
    $Uri = [string]$Source.url

    if (-not $Uri.StartsWith("https://", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Registered locator is not HTTPS for $SourceId"
    }

    $IsPdf = $Uri.ToLowerInvariant().EndsWith(".pdf")
    $Extension = if ($IsPdf) { ".pdf" } else { ".html" }
    $ExpectedContentType = if ($IsPdf) { "application/pdf" } else { "text/html" }
    $Destination = Join-Path $CaptureDir ($SourceId + $Extension)

    Write-Host "CAPTURE_START $SourceId"
    $Response = $null
    $UsedBrowserHar = $false

    try {
        $Response = Invoke-WebRequest `
            -Uri $Uri `
            -MaximumRedirection 10 `
            -UseBasicParsing

        if ($null -eq $Response -or $null -eq $Response.Headers) {
            throw "Missing response metadata for $SourceId"
        }
        $ObservedContentType = [string]$Response.Headers["Content-Type"]
        $ObservedMediaType = ($ObservedContentType.Split(";")[0]).Trim()
        if (-not $ObservedMediaType.Equals($ExpectedContentType, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Unexpected or missing Content-Type for $SourceId"
        }
        if ($null -eq $Response.RawContentStream) {
            throw "Missing response body stream for $SourceId"
        }
        $Response.RawContentStream.Position = 0
        $OutputStream = [System.IO.File]::Create($Destination)
        try {
            $Response.RawContentStream.CopyTo($OutputStream)
        }
        finally {
            $OutputStream.Dispose()
        }
    }
    catch {
        if (Test-Path -LiteralPath $Destination -PathType Leaf) {
            Remove-Item -LiteralPath $Destination -Force
        }

        $Fallback = $BrowserHarFallbacks[$SourceId]
        if ($null -ne $Fallback -and $Fallback.HarPath) {
            $HarPath = [string]$Fallback.HarPath
            $HarParameter = [string]$Fallback.HarParameter
            $ExpectedText = [string]$Fallback.ExpectedText
            $MetadataStem = [string]$Fallback.MetadataStem

            Assert-OutsideRepo -CandidatePath $HarPath -RepositoryPath $RepoRoot -Label ($HarParameter.TrimStart("-"))
            if (-not (Test-Path -LiteralPath $HarPath -PathType Leaf)) {
                throw "Sanitized HAR file not found for ${SourceId}: $HarPath"
            }

            $BrowserCaptureMetadata = Join-Path $PrivateMetadataRoot ("HYDRA_CONSTRAINT_BROWSER_RESPONSE_CAPTURE_" + $MetadataStem + "_" + $RunStamp + ".json")
            $PreviousHarPythonPath = $env:PYTHONPATH
            try {
                $env:PYTHONPATH = $MaterializerSrc
                & python -m hydra_constraint_t1_raw.browser_response_capture `
                    --har $HarPath `
                    --output $Destination `
                    --metadata-output $BrowserCaptureMetadata `
                    --exact-url $Uri `
                    --expected-mime-prefix "text/html" `
                    --expected-text $ExpectedText `
                    --public-repo-root $RepoRoot

                if ($LASTEXITCODE -ne 0) {
                    throw "Reviewed browser-response extraction failed for $SourceId with exit code $LASTEXITCODE"
                }
            }
            finally {
                $env:PYTHONPATH = $PreviousHarPythonPath
            }

            $UsedBrowserHar = $true
            Write-Host "CAPTURE_BROWSER_HAR_OK $SourceId metadata=$BrowserCaptureMetadata"
        }
        else {
            if ($null -ne $Fallback) {
                $HarParameter = [string]$Fallback.HarParameter
                throw "Direct capture failed for $SourceId. Do not bypass the site challenge, replay browser credentials, substitute another source, or use rendered DOM. Export a sanitized browser HAR containing the exact registered document response and rerun with $HarParameter <private-har-path>."
            }
            throw
        }
    }

    if (-not (Test-Path -LiteralPath $Destination -PathType Leaf)) {
        throw "Capture did not create a file for $SourceId"
    }

    $Item = Get-Item -LiteralPath $Destination
    if ($Item.Length -le 0) {
        throw "Captured file is empty for $SourceId"
    }

    $Hash = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Hash.Length -ne 64) {
        throw "SHA-256 capture failed for $SourceId"
    }

    $AcquiredAt = Get-UtcTimestamp
    $VersionStamp = Get-SafeTimestamp
    $SourceVersionId = "SV-$SourceId-$VersionStamp-$($Hash.Substring(0, 12))"

    $Captures += [ordered]@{
        source_id = $SourceId
        source_version_id = $SourceVersionId
        input_file = $Destination
        content_type = $ExpectedContentType
        source_locator = $Uri
        acquired_at = $AcquiredAt
        processing_disposition = "ELIGIBLE"
    }

    $CaptureMethod = if ($UsedBrowserHar) { "SANITIZED_BROWSER_HAR_EXACT_RESPONSE_BODY" } else { "DIRECT_REGISTERED_LOCATOR" }
    Write-Host "CAPTURE_OK $SourceId method=$CaptureMethod bytes=$($Item.Length) sha256=$Hash"
}

if ($Captures.Count -ne 9) {
    throw "Capture count drifted from the authoritative nine-source registry."
}

$ReleaseStamp = Get-SafeTimestamp
$ReleaseCreatedAt = Get-UtcTimestamp
$ReleaseId = "REL-AIDC-FIRST-SLICE-$ReleaseStamp"

$CapturePlan = [ordered]@{
    schema_version = "hydra-constraint-first-slice-local-capture-plan/v1"
    slice_id = "AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1"
    availability_mode = "ACQUISITION_TIME_CONSERVATIVE"
    release_id = $ReleaseId
    release_created_at = $ReleaseCreatedAt
    captures = $Captures
}

$PlanPath = Join-Path $PrivateMetadataRoot ("HYDRA_CONSTRAINT_FIRST_SLICE_PRIVATE_CAPTURE_PLAN_" + $RunStamp + ".json")
$AttestationPath = Join-Path $PrivateMetadataRoot ("HYDRA_CONSTRAINT_FIRST_SLICE_PRIVATE_MATERIALIZATION_ATTESTATION_" + $RunStamp + ".json")

$PlanJson = $CapturePlan | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($PlanPath, $PlanJson, [System.Text.UTF8Encoding]::new($false))

$PreviousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $MaterializerSrc

    & python -m hydra_constraint_t1_raw.first_slice_cli `
        --registry $RegistryPath `
        --capture-plan $PlanPath `
        --private-root $PrivateRawRoot `
        --public-repo-root $RepoRoot `
        --attestation-output $AttestationPath

    if ($LASTEXITCODE -ne 0) {
        throw "Private T1 first-slice materialization failed with exit code $LASTEXITCODE"
    }

    & python $AttestationValidator `
        --attestation $AttestationPath `
        --registry $RegistryPath

    if ($LASTEXITCODE -ne 0) {
        throw "Sanitized attestation validation failed with exit code $LASTEXITCODE"
    }
}
finally {
    $env:PYTHONPATH = $PreviousPythonPath
}

Write-Host "HYDRA_FIRST_SLICE_PRIVATE_CAPTURE=PASS"
Write-Host "PRIVATE_RAW_ROOT=$PrivateRawRoot"
Write-Host "PRIVATE_CAPTURE_PLAN=$PlanPath"
Write-Host "PRIVATE_ATTESTATION=$AttestationPath"
Write-Host "RAW_BODIES_PUBLISHED_TO_GIT=NO"
Write-Host "HISTORICAL_BACKDATING=NO"
Write-Host "ORDINARY_REPLAY_PROMOTED=NO"
Write-Host "CANONICAL_ADMISSION_PROMOTED=NO"
Write-Host "CLOUDFLARE_BYPASS_ATTEMPTED=NO"
Write-Host "LINKED_REPORT_SUBSTITUTED=NO"
Write-Host "RENDERED_DOM_USED=NO"
