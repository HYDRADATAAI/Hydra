# Synthetic responses only. This test never calls a public source.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$SourceRepo = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.."))
$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("hydra-capture-test-" + [guid]::NewGuid())
$FixtureRepo = Join-Path $TempRoot "repo"
$RegistryRelative = "docs\constraint\first_slice\ai_data_center_power_infrastructure_v1\HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json"

function Invoke-WebRequest {
    param($Uri, $MaximumRedirection, [switch]$UseBasicParsing)
    $mime = if ($Uri.EndsWith(".pdf")) { "application/pdf" } else { "text/html" }
    $headers = @{}
    if ($script:Mode -eq "wrong") { $headers["Content-Type"] = "application/json" }
    elseif ($script:Mode -eq "prefix") { $headers["Content-Type"] = $mime + "-invalid" }
    elseif ($script:Mode -ne "missing") { $headers["Content-Type"] = $mime + "; charset=utf-8" }
    $body = [byte[]](0, 1, 127, 128, 255, 13, 10)
    return [pscustomobject]@{
        Headers = $headers
        RawContentStream = [System.IO.MemoryStream]::new($body)
    }
}

try {
    New-Item -ItemType Directory -Path $FixtureRepo -Force | Out-Null
    Copy-Item (Join-Path $SourceRepo "constraint-t1-raw-artifact-store") $FixtureRepo -Recurse
    New-Item -ItemType Directory -Path (Join-Path $FixtureRepo "tools") -Force | Out-Null
    Copy-Item (Join-Path $SourceRepo "tools\validate_constraint_t1_first_slice_attestation.py") (Join-Path $FixtureRepo "tools")
    $registryPath = Join-Path $FixtureRepo $RegistryRelative
    New-Item -ItemType Directory -Path (Split-Path $registryPath) -Force | Out-Null
    $sources = @(1..9 | ForEach-Object {
        $extension = if ($_ % 2 -eq 0) { ".pdf" } else { ".html" }
        @{ source_id = "SYNTHETIC-$_"; url = "https://example.invalid/$_$extension" }
    })
    $json = @{ slice_id = "AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1"; sources = $sources } | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText($registryPath, $json, [System.Text.UTF8Encoding]::new($false))

    foreach ($script:Mode in @("missing", "wrong", "prefix", "valid")) {
        $caseRoot = Join-Path $TempRoot $script:Mode
        $failed = $false
        try {
            & (Join-Path $SourceRepo "tools\private\Invoke-HYDRAConstraintFirstSlicePrivateCapture_V001_20260926.ps1") -AuthorizedPublicAcquisition -RepoRoot $FixtureRepo -PrivateRawRoot (Join-Path $caseRoot "raw") -PrivateStagingRoot (Join-Path $caseRoot "staging") -PrivateMetadataRoot (Join-Path $caseRoot "metadata") | Out-Null
        }
        catch {
            $failed = $true
            if ($script:Mode -eq "valid") { throw }
            if ($_.Exception.Message -notlike "*Content-Type*") { throw }
        }
        if ($script:Mode -ne "valid") {
            if (-not $failed) { throw "Invalid response accepted: $script:Mode" }
            if (@(Get-ChildItem (Join-Path $caseRoot "metadata") -File).Count -ne 0) { throw "Rejected response produced metadata" }
            if (@(Get-ChildItem (Join-Path $caseRoot "raw") -File -Recurse).Count -ne 0) { throw "Rejected response entered custody" }
        }
        else {
            $files = @(Get-ChildItem (Join-Path $caseRoot "staging") -File -Recurse)
            if ($files.Count -ne 9) { throw "Expected nine synthetic captures" }
            foreach ($file in $files) {
                if ([Convert]::ToBase64String([System.IO.File]::ReadAllBytes($file.FullName)) -ne "AAF/gP8NCg==") { throw "Response bytes changed" }
            }
            $attestationFile = Get-ChildItem (Join-Path $caseRoot "metadata") -Filter "*ATTESTATION*.json"
            $attestation = Get-Content $attestationFile.FullName -Raw | ConvertFrom-Json
            if ($attestation.materialized_source_count -ne 9 -or $attestation.strict_historical_replay_promoted) { throw "Invalid synthetic attestation" }
        }
    }
    Write-Output "SYNTHETIC_CAPTURE_RESPONSE_TESTS=PASS"
}
finally {
    if (Test-Path $TempRoot) { Remove-Item $TempRoot -Recurse -Force }
}
