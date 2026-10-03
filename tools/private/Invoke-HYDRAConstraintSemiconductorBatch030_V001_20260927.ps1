[CmdletBinding()]
param(
 [ValidateSet("Capture","Status","Materialize","Verify","All")]
 [string]$Mode="Capture",
 [switch]$AuthorizedPublicAcquisition,
 [ValidateSet("auto","chrome","msedge")][string]$Browser="auto",
 [ValidateSet("exact","same-origin")][string]$RedirectPolicy="exact",
 [string]$RepoRoot,
 [string]$PrivateRoot="D:\HYDRA_PRIVATE\constraint\raw",
 [string]$BrowserPrivateRoot="D:\HYDRA_PRIVATE\constraint",
 [string]$InboxRoot="D:\HYDRA_PRIVATE\constraint\capture_inbox\semiconductor_batch030",
 [string]$HandbackRoot="D:\HYDRA_PRIVATE\constraint\handback"
)
$ErrorActionPreference="Stop"
if(-not $RepoRoot){$RepoRoot=[System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))}else{$RepoRoot=[System.IO.Path]::GetFullPath($RepoRoot)}
$BrowserRunner=Join-Path $PSScriptRoot "HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH030_BROWSER_CAPTURE_V001_20260927.py"
$Materializer=Join-Path $RepoRoot "tools\materialize_constraint_second_slice_batch030_private_t1.py"
$Verifier=Join-Path $RepoRoot "tools\verify_constraint_second_slice_batch030_private_t1.py"
$Handback=Join-Path $RepoRoot "tools\build_constraint_second_slice_batch030_private_t1_handback.py"
$VenvPython=Join-Path $BrowserPrivateRoot "browser-runtime\playwright-venv\Scripts\python.exe"
foreach($p in @($BrowserRunner,$Materializer,$Verifier,$Handback,$VenvPython)){if(-not(Test-Path -LiteralPath $p -PathType Leaf)){throw "Required path missing: $p"}}
if($Mode -eq "Capture"){
 if(-not $AuthorizedPublicAcquisition){throw "-AuthorizedPublicAcquisition is required"}
 & $VenvPython $BrowserRunner --authorized-public-acquisition --repo-root $RepoRoot --private-root $BrowserPrivateRoot --inbox-root $InboxRoot --browser $Browser --redirect-policy $RedirectPolicy
 exit $LASTEXITCODE
}
if($Mode -eq "Status"){& python $Materializer --repo-root $RepoRoot --private-root $PrivateRoot --inbox-root $InboxRoot --dry-run; exit $LASTEXITCODE}
if($Mode -eq "Materialize"){& python $Materializer --repo-root $RepoRoot --private-root $PrivateRoot --inbox-root $InboxRoot; exit $LASTEXITCODE}
if($Mode -eq "Verify"){& python $Verifier --repo-root $RepoRoot --private-root $PrivateRoot; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}; New-Item -ItemType Directory -Force -Path $HandbackRoot|Out-Null; $out=Join-Path $HandbackRoot "HYDRA_CONSTRAINT_SEMI_B030_PRIVATE_T1_HANDBACK_V001.json"; & python $Handback --repo-root $RepoRoot --private-root $PrivateRoot --output-path $out; exit $LASTEXITCODE}
if($Mode -eq "All"){& python $Materializer --repo-root $RepoRoot --private-root $PrivateRoot --inbox-root $InboxRoot; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}; & python $Verifier --repo-root $RepoRoot --private-root $PrivateRoot; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}; New-Item -ItemType Directory -Force -Path $HandbackRoot|Out-Null; $out=Join-Path $HandbackRoot "HYDRA_CONSTRAINT_SEMI_B030_PRIVATE_T1_HANDBACK_V001.json"; & python $Handback --repo-root $RepoRoot --private-root $PrivateRoot --output-path $out; exit $LASTEXITCODE}
