# .vscode/HighlightOutput.ps1
param(
    [Parameter(ValueFromPipeline=$true)] # Removed Mandatory=$true as it's not needed with pipeline input for this scenario
    [AllowEmptyString()]                 # *** THIS IS THE CRUCIAL ADDITION ***
    [string]$Line
)

# ANSI escape codes for colors
# Red: `e[31m`
# Green: `e[32m`
# Reset: `e[0m` (important to reset color after use)

# It's good practice to handle null or empty lines explicitly before trying to match.
if ([string]::IsNullOrEmpty($Line)) {
    Write-Host "" # If the line is empty, just print an empty line
}
elseif ($Line -match "Failed") {
    Write-Host ("`e[31m" + $Line + "`e[0m")
} elseif ($Line -match "Succeeded") {
    Write-Host ("`e[32m" + $Line + "`e[0m")
} elseif ($Line -match "ERROR") {
    Write-Host ("`e[31m" + $Line + "`e[0m")
}
# Pass through lines that don't match any condition, without coloring
else {
    Write-Host $Line
}