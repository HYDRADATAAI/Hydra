param(
    [Parameter(Mandatory=$false)]
    [string]$SiteRoot = ""
)

$ErrorActionPreference = "Stop"
$Zip = Get-ChildItem "$HOME\Downloads\HYDRA_W6_W7_RETEST_READY*.zip" -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $Zip) { throw "HYDRA_W6_W7_RETEST_READY ZIP not found in Downloads." }

$Hash = (Get-FileHash -LiteralPath $Zip.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "ZIP_FOUND=$($Zip.FullName)" -ForegroundColor Green
Write-Host "ZIP_SHA256=$Hash"

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$RunRoot = "D:\HYDRA\WEBSITE_TESTS\W6_W7_RETEST_PACKAGE_$Stamp"
New-Item -ItemType Directory -Path $RunRoot -Force | Out-Null
Expand-Archive -LiteralPath $Zip.FullName -DestinationPath $RunRoot -Force

$Runner = Get-ChildItem -LiteralPath $RunRoot -Recurse -File -Filter "RUN_W6_W7_RETEST_ON_SITE.ps1" |
    Select-Object -First 1
if (-not $Runner) { throw "RUN_W6_W7_RETEST_ON_SITE.ps1 not found after extraction." }

Write-Host "EXTRACTED_TO=$RunRoot"
Write-Host "RUNNER=$($Runner.FullName)"

$Args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $Runner.FullName)
if ($SiteRoot) { $Args += @("-SiteRoot", $SiteRoot) }
& powershell.exe @Args
exit $LASTEXITCODE
