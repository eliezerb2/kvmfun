# .vscode/run_helm_tests_colored.ps1

param(
    # Make the release name a parameter for reusability. Default to 'kvmfun'.
    [string]$ReleaseName,
    [string]$TestPodName
)

# 1. Set execution policy for THIS PROCESS only.
# This ensures that HighlightOutput.ps1 can be executed.
Set-ExecutionPolicy -Scope Process Bypass -Force

# Get the directory of this script (run_helm_tests_colored.ps1)
# to reliably find HighlightOutput.ps1 (assuming it's in the same folder).
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$highlightScriptPath = Join-Path $scriptDir "HighlightOutput.ps1"

# Basic check to ensure the highlighting script exists
if (-not (Test-Path $highlightScriptPath)) {
    Write-Error "Error: Highlighting script not found at $highlightScriptPath. Please ensure it's in the same .vscode folder."
    exit 1
}

# 2. Execute 'helm test' and directly pipe its output to ForEach-Object.
# This avoids Invoke-Expression for the pipeline, ensuring $_ is correctly populated.
helm test $ReleaseName 

# Get the name of the test pod
$testPodName = "$($ReleaseName)-$($TestPodName)"

# Retrieve the logs
Write-Host "`n--- Full Raw Log for Pod: $testPodName ---" -ForegroundColor Cyan

# Check if the pod exists before trying to fetch logs. This avoids errors if the pod was deleted.
$podCheck = kubectl get pod $testPodName -o name --ignore-not-found
if ($podCheck) {
    kubectl logs $testPodName | ForEach-Object {& $highlightScriptPath -Line $_}
} else {
    Write-Warning "Could not find the test pod '$testPodName' after the test run. It might have been deleted by its 'hook-delete-policy'."
}
