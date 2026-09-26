[CmdletBinding()]
param(
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

& $VenvPython -c "import playwright" 2>$null
if ($LASTEXITCODE -ne 0) {
    if ($NoBootstrap) {
        throw "Playwright is absent from the private runtime and -NoBootstrap was specified."
    }
    & $VenvPython -m pip install --disable-pip-version-check --requirement $Requirements
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to install Playwright into the private runtime."
    }
}

$Arguments = @(
    $Runner,
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
