$ErrorActionPreference = "Stop"
$Downloads = Join-Path $HOME "Downloads"
$Zip = Join-Path $Downloads "HYDRA_WEBSITE_V8_W2_W3_PROOF_CASE_STUDY_READY.zip"
$Expected = "eb419d57601fcc6462ae5ea34817ce6ebc045decac3708daec4f0b98bfeb218f"
if (-not (Test-Path -LiteralPath $Zip)) { throw "ZIP not found: $Zip" }
$Actual = (Get-FileHash -LiteralPath $Zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($Actual -ne $Expected) { throw "SHA256 mismatch. Expected=$Expected Actual=$Actual" }
$Target = "D:\HYDRA_SITE\V8_W2_W3"
if (Test-Path -LiteralPath $Target) { Remove-Item -LiteralPath $Target -Recurse -Force }
New-Item -ItemType Directory -Path $Target -Force | Out-Null
Expand-Archive -LiteralPath $Zip -DestinationPath $Target -Force
$Index = Get-ChildItem -LiteralPath $Target -Filter index.html -File -Recurse | Select-Object -First 1
if (-not $Index) { throw "index.html not found after extraction" }
Write-Host "HYDRA W2/W3 package verified and extracted." -ForegroundColor Green
Write-Host "ZIP_SHA256=$Actual"
Write-Host "INDEX=$($Index.FullName)"
Start-Process $Index.FullName
