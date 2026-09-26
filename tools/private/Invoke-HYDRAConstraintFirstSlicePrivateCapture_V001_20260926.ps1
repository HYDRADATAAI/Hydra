[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [switch]$AuthorizedPublicAcquisition,

    [string]$RepoRoot,

    [string]$PrivateRawRoot = "D:\HYDRA_PRIVATE\constraint\raw",

    [string]$PrivateStagingRoot = "D:\HYDRA_PRIVATE\constraint\capture-staging",

    [string]$PrivateMetadataRoot = "D:\HYDRA_PRIVATE\constraint\metadata"
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
    $Response = Invoke-WebRequest `
        -Uri $Uri `
        -OutFile $Destination `
        -MaximumRedirection 10 `
        -UseBasicParsing

    if (-not (Test-Path -LiteralPath $Destination -PathType Leaf)) {
        throw "Capture did not create a file for $SourceId"
    }

    $Item = Get-Item -LiteralPath $Destination
    if ($Item.Length -le 0) {
        throw "Captured file is empty for $SourceId"
    }

    $ObservedContentType = $null
    if ($null -ne $Response.Headers -and $Response.Headers["Content-Type"]) {
        $ObservedContentType = [string]$Response.Headers["Content-Type"]
    }
    if (
        $ObservedContentType -and
        -not $ObservedContentType.StartsWith($ExpectedContentType, [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "Unexpected Content-Type for $SourceId. Expected prefix $ExpectedContentType, observed $ObservedContentType"
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

    Write-Host "CAPTURE_OK $SourceId bytes=$($Item.Length) sha256=$Hash"
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

$CapturePlan | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $PlanPath -Encoding UTF8

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
