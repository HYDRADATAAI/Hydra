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
$RuntimeRoot = Join-Path $PrivateRoot "browser-runtime"
$VenvRoot = Join-Path $RuntimeRoot "playwright-venv"
$VenvPython = Join-Path $VenvRoot "Scripts\python.exe"

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
