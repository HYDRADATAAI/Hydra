[CmdletBinding()]
param(
    [string]$RepoRoot = "D:\HYDRA_GITHUB\Hydra",

    [string]$RemoteName = "origin",

    [string]$CaptureBranch = "constraint/t1-private-capture-execution-packet-20260926",

    [ValidateSet("auto", "chrome", "msedge")]
    [string]$Browser = "auto",

    [switch]$Headless,

    [int]$ChallengeWaitSeconds = 180,

    [int]$NavigationTimeoutSeconds = 90
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & git -C $RepoRoot @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git -C '$RepoRoot' $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)

if (-not (Test-Path -LiteralPath $RepoRoot -PathType Container)) {
    throw "HYDRA repository directory not found: $RepoRoot"
}

$GitDir = Join-Path $RepoRoot ".git"
if (-not (Test-Path -LiteralPath $GitDir)) {
    throw "HYDRA repository .git metadata not found: $RepoRoot"
}

$TopLevel = (& git -C $RepoRoot rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $TopLevel) {
    throw "Path is not a readable Git repository: $RepoRoot"
}

$TopLevel = [System.IO.Path]::GetFullPath([string]$TopLevel)
if (-not $TopLevel.Equals($RepoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Unexpected Git top-level path. Expected '$RepoRoot', observed '$TopLevel'"
}

$RemoteUrl = (& git -C $RepoRoot remote get-url $RemoteName 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $RemoteUrl) {
    throw "Git remote '$RemoteName' is unavailable in $RepoRoot"
}

$RemoteUrlText = [string]$RemoteUrl
if (
    $RemoteUrlText -notmatch "(?i)(^|[:/])HYDRADATAAI/Hydra(?:\.git)?$"
) {
    throw "Unexpected '$RemoteName' remote for HYDRA repository: $RemoteUrlText"
}

$StatusBefore = @(& git -C $RepoRoot status --porcelain=v1 --untracked-files=no)
if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect HYDRA working-tree state."
}
if ($StatusBefore.Count -gt 0) {
    throw "HYDRA tracked working tree is not clean. Commit/revert local tracked changes before switching capture branches."
}

Write-Host "HYDRA_REPO=$RepoRoot"
Write-Host "HYDRA_REMOTE=$RemoteUrlText"

$RemoteRef = "refs/remotes/$RemoteName/$CaptureBranch"
$FetchRefspec = "+refs/heads/${CaptureBranch}:$RemoteRef"
Invoke-Git -Arguments @("fetch", "--prune", $RemoteName, $FetchRefspec)

$LocalBranchExists = $false
& git -C $RepoRoot show-ref --verify --quiet "refs/heads/$CaptureBranch"
if ($LASTEXITCODE -eq 0) {
    $LocalBranchExists = $true
}

if ($LocalBranchExists) {
    Invoke-Git -Arguments @("checkout", $CaptureBranch)
}
else {
    Invoke-Git -Arguments @("checkout", "-b", $CaptureBranch, "--track", "$RemoteName/$CaptureBranch")
}

Invoke-Git -Arguments @("merge", "--ff-only", "$RemoteName/$CaptureBranch")

$CurrentBranch = (& git -C $RepoRoot branch --show-current)
if ($LASTEXITCODE -ne 0 -or [string]$CurrentBranch -ne $CaptureBranch) {
    throw "Capture branch checkout failed. Expected '$CaptureBranch', observed '$CurrentBranch'"
}

$StatusAfter = @(& git -C $RepoRoot status --porcelain=v1 --untracked-files=no)
if ($LASTEXITCODE -ne 0) {
    throw "Unable to verify HYDRA working-tree state after checkout."
}
if ($StatusAfter.Count -gt 0) {
    throw "HYDRA tracked working tree changed unexpectedly during bootstrap."
}

$CaptureScript = Join-Path $RepoRoot "tools\private\Invoke-HYDRAConstraintFirstSliceAutomatedBrowserCapture_V001_20260926.ps1"
if (-not (Test-Path -LiteralPath $CaptureScript -PathType Leaf)) {
    throw "Canonical automated browser capture script not found on '$CaptureBranch': $CaptureScript"
}

Write-Host "HYDRA_CAPTURE_BRANCH=$CaptureBranch"
Write-Host "HYDRA_CAPTURE_SCRIPT=$CaptureScript"
Write-Host "HYDRA_WORKSTATION_BOOTSTRAP=PASS"

$CaptureArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $CaptureScript,
    "-AuthorizedPublicAcquisition",
    "-Browser", $Browser,
    "-ChallengeWaitSeconds", [string]$ChallengeWaitSeconds,
    "-NavigationTimeoutSeconds", [string]$NavigationTimeoutSeconds
)

if ($Headless) {
    $CaptureArgs += "-Headless"
}

& powershell.exe @CaptureArgs
if ($LASTEXITCODE -ne 0) {
    throw "Canonical automated browser capture failed with exit code $LASTEXITCODE"
}

Write-Host "HYDRA_WORKSTATION_CAPTURE=PASS"
