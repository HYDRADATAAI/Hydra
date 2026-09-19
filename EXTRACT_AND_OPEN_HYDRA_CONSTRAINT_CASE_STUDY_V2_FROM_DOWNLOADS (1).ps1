$ErrorActionPreference = 'Stop'
$downloads = Join-Path $HOME 'Downloads'
$zip = Get-ChildItem $downloads -File -Filter 'HYDRA_CONSTRAINT_CASE_STUDY_V2_READY*.zip' |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $zip) { throw 'HYDRA_CONSTRAINT_CASE_STUDY_V2_READY ZIP not found in Downloads.' }
$dest = Join-Path 'D:\' ('HYDRA_CONSTRAINT_CASE_STUDY_V2_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $dest -Force | Out-Null
Expand-Archive -LiteralPath $zip.FullName -DestinationPath $dest -Force
$index = Get-ChildItem $dest -File -Filter 'index.html' -Recurse | Select-Object -First 1
if (-not $index) { throw 'index.html not found after extraction.' }
Write-Host "ZIP=$($zip.FullName)" -ForegroundColor Cyan
Write-Host "EXTRACTED_TO=$dest" -ForegroundColor Green
Write-Host "PREVIEW=$($index.FullName)" -ForegroundColor Green
Start-Process $index.FullName
