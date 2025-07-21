<#
.SYNOPSIS
    Cleans the .logs directory in the project root.

.DESCRIPTION
    This script removes all files and subdirectories within the .logs folder
    located at the root of the project. It is useful for clearing out old
    log files before a new build or deployment.
#>

# Get the project root directory (assuming this script is in a subdirectory like .vscode)
$projectRoot = Resolve-Path -Path (Join-Path $PSScriptRoot "..")
$logsDir = Join-Path -Path $projectRoot -ChildPath ".logs"

Write-Host "Checking for logs directory: $logsDir" -ForegroundColor Cyan

if (Test-Path -Path $logsDir -PathType Container) {
    Write-Host "Found '.logs' directory. Removing contents..." -ForegroundColor Yellow
    
    # Get child items to check if the directory is empty
    $childItems = Get-ChildItem -Path $logsDir -Force
    
    if ($null -ne $childItems) {
        # Remove all files and folders inside .logs
        Remove-Item -Path (Join-Path $logsDir "*") -Recurse -Force
        Write-Host "Successfully cleaned the '.logs' directory." -ForegroundColor Green
    } else {
        Write-Host "The '.logs' directory is already empty. No action needed." -ForegroundColor Green
    }
} else {
    Write-Host "The '.logs' directory was not found. Nothing to clean." -ForegroundColor Green
}