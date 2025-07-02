# .vscode/run_helm_tests_colored.ps1

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
helm test kvmfun --logs | ForEach-Object {
    # Here, $_ correctly represents the current line from the pipeline.
    # Call your HighlightOutput.ps1 script with the current line.
    & $highlightScriptPath -Line $_
}