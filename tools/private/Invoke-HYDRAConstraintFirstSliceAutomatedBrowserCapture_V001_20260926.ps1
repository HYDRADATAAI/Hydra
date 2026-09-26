[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [switch]$AuthorizedPublicAcquisition,

    [ValidateSet("auto", "chrome", "msedge")]
    [string]$Browser = "auto",

    [switch]$Headless,

    [int]$ChallengeWaitSeconds = 180,

    [int]$NavigationTimeoutSeconds = 90,

    [string]$RepoRoot,

    [string]$PrivateRoot = "D:\HYDRA\_PRIVATE\constraint",

    [string]$BootstrapPython = "python",

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

$Runner = Join-Path $PSScriptRoot "HYDRA_CONSTRAINT_T1_AUTOMATED_BROWSER_FIRST_SLICE_CAPTURE_V001_20260926.py"
$Requirements = Join-Path $PSScriptRoot "HYDRA_CONSTRAINT_T1_AUTOMATED_BROWSER_CAPTURE_REQUIREMENTS_V001_20260926.txt"
$RuntimeRoot = Join-Path $PrivateRoot "browser-runtime"
$VenvRoot = Join-Path $RuntimeRoot "playwright-venv"
$VenvPython = Join-Path $VenvRoot "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Runner -PathType Leaf)) {
    throw "Automated browser capture runner not found: $Runner"
}
if (-not (Test-Path -LiteralPath $Requirements -PathType Leaf)) {
    throw "Automated browser capture requirements not found: $Requirements"
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
        # Windows PowerShell 5 converts native stderr into ErrorRecord objects.
        # Temporarily prevent ordinary pip stderr/progress from becoming a terminating
        # NativeCommandError while still enforcing the process exit code below.
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
        throw "Playwright package installation completed but the expected private-runtime package marker is missing: $PlaywrightPackageMarker"
    }
}

$Arguments = @(
    $Runner,
    "--authorized-public-acquisition",
    "--repo-root", $RepoRoot,
    "--private-root", $PrivateRoot,
    "--browser", $Browser,
    "--challenge-wait-seconds", [string]$ChallengeWaitSeconds,
    "--navigation-timeout-seconds", [string]$NavigationTimeoutSeconds
)

if ($Headless) {
    $Arguments += "--headless"
}

& $VenvPython @Arguments
exit $LASTEXITCODE
