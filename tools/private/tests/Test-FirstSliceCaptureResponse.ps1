# Synthetic responses only. This test never calls a public source.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$SourceRepo = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.."))
$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("hydra-capture-test-" + [guid]::NewGuid())
$FixtureRepo = Join-Path $TempRoot "repo"
$RegistryRelative = "docs\constraint\first_slice\ai_data_center_power_infrastructure_v1\HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json"

# Valid documents retain UTF-8/non-ASCII bytes and CR/LF; PDF includes the original binary vector.
$ResponseBodyBase64 = @{
    "text/html" = "PCFkb2N0eXBlIGh0bWw+DQo8aHRtbD48Ym9keT5TeW50aGV0aWMgY2Fmw6kgc291cmNlLjwvYm9keT48L2h0bWw+DQo="
    "application/pdf" = "JVBERi0xLjQNCiUAAX+A/w0KMSAwIG9iag0KPDwgL1R5cGUgL0NhdGFsb2cgL1BhZ2VzIDIgMCBSID4+DQplbmRvYmoNCjIgMCBvYmoNCjw8IC9UeXBlIC9QYWdlcyAvS2lkcyBbMyAwIFJdIC9Db3VudCAxID4+DQplbmRvYmoNCjMgMCBvYmoNCjw8IC9UeXBlIC9QYWdlIC9QYXJlbnQgMiAwIFIgL01lZGlhQm94IFswIDAgNzIgNzJdIC9Db250ZW50cyA0IDAgUiA+Pg0KZW5kb2JqDQo0IDAgb2JqDQo8PCAvTGVuZ3RoIDAgPj4NCnN0cmVhbQ0KDQplbmRzdHJlYW0NCmVuZG9iag0KeHJlZg0KMCA1DQowMDAwMDAwMDAwIDY1NTM1IGYNCjAwMDAwMDAwMTggMDAwMDAgbg0KMDAwMDAwMDA3MCAwMDAwMCBuDQowMDAwMDAwMTMwIDAwMDAwIG4NCjAwMDAwMDAyMTggMDAwMDAgbg0KdHJhaWxlcg0KPDwgL1NpemUgNSAvUm9vdCAxIDAgUiA+Pg0Kc3RhcnR4cmVmDQoyNzMNCiUlRU9GDQo="
}

function Invoke-WebRequest {
    param($Uri, $MaximumRedirection, [switch]$UseBasicParsing)
    $mime = if ($Uri.EndsWith(".pdf")) { "application/pdf" } else { "text/html" }
    $headers = @{}
    if ($CaptureTestMode -eq "wrong") { $headers["Content-Type"] = "application/json" }
    elseif ($CaptureTestMode -eq "prefix") { $headers["Content-Type"] = $mime + "-invalid" }
    elseif ($CaptureTestMode -ne "missing") { $headers["Content-Type"] = $mime + "; charset=utf-8" }
    [byte[]]$body = [Convert]::FromBase64String($ResponseBodyBase64[$mime])
    if (($CaptureTestMode -eq "nondocument-html" -and $mime -eq "text/html") -or
        ($CaptureTestMode -eq "nondocument-pdf" -and $mime -eq "application/pdf")) {
        $body = [Convert]::FromBase64String("AAF/gP8NCg==")
    }
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

    foreach ($CaptureTestMode in @("missing", "wrong", "prefix", "nondocument-html", "nondocument-pdf", "valid")) {
        $caseRoot = Join-Path $TempRoot $CaptureTestMode
        $failed = $false
        $captureOutput = [System.Collections.Generic.List[string]]::new()
        $isNonDocument = $CaptureTestMode.StartsWith("nondocument-")
        try {
            if ($CaptureTestMode -eq "valid" -or $isNonDocument) {
                & (Join-Path $SourceRepo "tools\private\Invoke-HYDRAConstraintFirstSlicePrivateCapture_V001_20260926.ps1") -AuthorizedPublicAcquisition -RepoRoot $FixtureRepo -PrivateRawRoot (Join-Path $caseRoot "raw") -PrivateStagingRoot (Join-Path $caseRoot "staging") -PrivateMetadataRoot (Join-Path $caseRoot "metadata") | ForEach-Object { $captureOutput.Add([string]$_); Write-Output $_ }
            }
            else {
                & (Join-Path $SourceRepo "tools\private\Invoke-HYDRAConstraintFirstSlicePrivateCapture_V001_20260926.ps1") -AuthorizedPublicAcquisition -RepoRoot $FixtureRepo -PrivateRawRoot (Join-Path $caseRoot "raw") -PrivateStagingRoot (Join-Path $caseRoot "staging") -PrivateMetadataRoot (Join-Path $caseRoot "metadata") | Out-Null
            }
        }
        catch {
            $failed = $true
            if ($CaptureTestMode -eq "valid") { throw }
            if ($isNonDocument) {
                if ($_.Exception.Message -notlike "*Private T1 first-slice materialization failed*") { throw }
                $expectedError = if ($CaptureTestMode -eq "nondocument-html") { "ERROR=SYNTHETIC-1: expected HTML source body" } else { "ERROR=SYNTHETIC-2: PDF signature is absent" }
                if (-not (($captureOutput -join "`n").Contains($expectedError))) { throw "Expected body rejection diagnostic missing: $CaptureTestMode" }
            }
            elseif ($_.Exception.Message -notlike "*Content-Type*") { throw }
        }
        if ($isNonDocument) {
            if (-not $failed) { throw "Non-document response accepted: $CaptureTestMode" }
            $metadataFiles = @(Get-ChildItem (Join-Path $caseRoot "metadata") -File)
            if ($metadataFiles.Count -ne 1 -or $metadataFiles[0].Name -notlike "*CAPTURE_PLAN_*.json") { throw "Body rejection produced unexpected metadata" }
            if (Test-Path (Join-Path $caseRoot "synthetic-public-status.json")) { throw "Rejected body produced public status" }
            if (@(Get-ChildItem (Join-Path $caseRoot "raw") -File -Recurse).Count -ne 0) { throw "Rejected body entered custody" }
            Write-Output "SYNTHETIC_NON_DOCUMENT_REJECTED=$CaptureTestMode"
        }
        elseif ($CaptureTestMode -ne "valid") {
            if (-not $failed) { throw "Invalid response accepted: $CaptureTestMode" }
            if (@(Get-ChildItem (Join-Path $caseRoot "metadata") -File).Count -ne 0) { throw "Rejected response produced metadata" }
            if (@(Get-ChildItem (Join-Path $caseRoot "raw") -File -Recurse).Count -ne 0) { throw "Rejected response entered custody" }
        }
        else {
            $files = @(Get-ChildItem (Join-Path $caseRoot "staging") -File -Recurse)
            if ($files.Count -ne 9) { throw "Expected nine synthetic captures" }
            foreach ($file in $files) {
                $mime = if ($file.Extension -eq ".pdf") { "application/pdf" } else { "text/html" }
                if ([Convert]::ToBase64String([System.IO.File]::ReadAllBytes($file.FullName)) -ne $ResponseBodyBase64[$mime]) { throw "Response bytes changed" }
            }
            $attestationFile = Get-ChildItem (Join-Path $caseRoot "metadata") -Filter "*ATTESTATION*.json"
            $attestation = Get-Content $attestationFile.FullName -Raw | ConvertFrom-Json
            if ($attestation.materialized_source_count -ne 9 -or $attestation.strict_historical_replay_promoted) { throw "Invalid synthetic attestation" }
            foreach ($file in $files) {
                $member = @($attestation.members | Where-Object { $_.source_id -eq $file.BaseName })
                if ($member.Count -ne 1) { throw "Expected one receipt-bound attestation member" }
                $receiptPath = Join-Path (Join-Path (Join-Path $caseRoot "raw/receipts") $member[0].source_id) ($member[0].source_version_id + ".json")
                $receipt = Get-Content $receiptPath -Raw | ConvertFrom-Json
                $digest = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
                if ($member[0].artifact_sha256 -ne $digest -or $receipt.artifact_sha256 -ne $digest -or $member[0].byte_length -ne $file.Length -or $receipt.byte_length -ne $file.Length) { throw "Receipt or attestation bytes drifted" }
                $rawPath = Join-Path (Join-Path $caseRoot "raw") $receipt.artifact_relpath
                $mime = if ($file.Extension -eq ".pdf") { "application/pdf" } else { "text/html" }
                if ([Convert]::ToBase64String([System.IO.File]::ReadAllBytes($rawPath)) -ne $ResponseBodyBase64[$mime]) { throw "Persisted response bytes changed" }
            }
            $statusPath = Join-Path $caseRoot "synthetic-public-status.json"
            & python (Join-Path $SourceRepo "tools/build_constraint_t1_post_capture_public_status.py") --attestation $attestationFile.FullName --registry $registryPath --output $statusPath
            if ($LASTEXITCODE -ne 0) { throw "Synthetic post-capture status failed" }
            $status = Get-Content $statusPath -Raw | ConvertFrom-Json
            if ($status.source_count -ne 9 -or $status.canonical_admission_promoted -or $status.native_signed_t5_t6_receipt_present -or $status.strict_historical_replay_promoted) { throw "Post-capture status promoted authority" }
            if ($status.still_blocked.ORDINARY_POINT_IN_TIME_REPLAY_READY -ne "NO") { throw "Post-capture status promoted replay" }

        }
    }
    Write-Output "SYNTHETIC_CAPTURE_RESPONSE_TESTS=PASS"
}
finally {
    if (Test-Path $TempRoot) { Remove-Item $TempRoot -Recurse -Force }
}
