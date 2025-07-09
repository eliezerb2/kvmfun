# .vscode/run_helm_tests_colored.ps1

param(
    # Make the release name a parameter for reusability. Default to 'kvmfun'.
    [string]$ReleaseName,
    [string]$TestPodName,
    [string]$LogFolderName = ".logs",
    [string]$LogFileNamePrefix = "tests",
    [string]$LogFileExtenstion = "log"
)

# 1. Set execution policy for THIS PROCESS only.
# This ensures that HighlightOutput.ps1 can be executed.
Set-ExecutionPolicy -Scope Process Bypass -Force

# Get the directory of this script and the workspace root to create a .logs folder
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$workspaceRoot = (Resolve-Path (Join-Path $scriptDir '..')).Path
$highlightScriptPath = Join-Path $scriptDir "HighlightOutput.ps1"

# Basic check to ensure the highlighting script exists
if (-not (Test-Path $highlightScriptPath)) {
    Write-Error "Error: Highlighting script not found at $highlightScriptPath. Please ensure it's in the same .vscode folder."
    exit 1
}

# 2. Set up logging to a file in a .logs directory
$logsDir = Join-Path $workspaceRoot $LogFolderName
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}
$timestamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$logFileName = "$LogFileNamePrefix-$timestamp.$LogFileExtenstion"
$logFilePath = Join-Path $logsDir $logFileName
Write-Host "Logging test output to: $logFilePath" -ForegroundColor Cyan

# 3. Execute 'helm test' with the --logs flag to stream test pod logs directly.
# This is more robust than finding the pod and running 'kubectl logs' separately.
Write-Host "Running Helm tests for release: '$ReleaseName' and streaming logs..." -ForegroundColor Cyan
# The output is processed line-by-line to provide real-time colored feedback in the
# console while simultaneously building a complete, colorized log file.

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
    kubectl logs $testPodName | Out-File -FilePath $logFilePath
} else {
    Write-Warning "Could not find the test pod '$testPodName' after the test run. It might have been deleted by its 'hook-delete-policy'."
    "No test pod found: $testPodName" | Out-File -FilePath $logFilePath
}

# Open the log file in VS Code
code $logFilePath
