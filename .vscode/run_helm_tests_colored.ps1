# .vscode/run_helm_tests_colored.ps1

param(
    # Make the release name a parameter for reusability. Default to 'kvmfun'.
    [string]$ReleaseName,
    [string]$TestPodName,
    [string]$LogFolderName = ".logs",
    [string]$LogFileNamePrefix = "tests",
    [string]$LogFileExtenstion = "log"
)

# Set execution policy for THIS PROCESS only.
Set-ExecutionPolicy -Scope Process Bypass -Force

# Get the directory of this script and the workspace root to create a .logs folder
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$workspaceRoot = (Resolve-Path (Join-Path $scriptDir '..')).Path

# Set up logging to a file in a .logs directory
$logsDir = Join-Path $workspaceRoot $LogFolderName
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}
$timestamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$logFileName = "$LogFileNamePrefix-$timestamp.$LogFileExtenstion"
$logFilePath = Join-Path $logsDir $logFileName
Write-Host "Logging test output to: $logFilePath" -ForegroundColor Cyan

Write-Host "Running Helm tests for release: '$ReleaseName' and streaming logs..." -ForegroundColor Cyan
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
