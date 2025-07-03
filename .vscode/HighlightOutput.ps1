# .vscode/HighlightOutput.ps1
param(
    [Parameter(ValueFromPipeline=$true)]
    [AllowEmptyString()]
    [string]$Line
)

enum Color {
    Red = 31
    Green = 32
    Yellow = 33
    Blue = 34
    Reset = 0
}

# Ensure the most critical/specific matches come first
switch -Regex ($Line) {
    "ERROR" {
        $selectedColor = [Color]::Red
        Break
    }
    "Failed" { # This will only be hit if "ERROR" wasn't present and "Failed" is
        $selectedColor = [Color]::Red
        Break
    }
    "WARNING" {
        $selectedColor = [Color]::Yellow
        Break
    }
    "Succeeded" {
        $selectedColor = [Color]::Green
        Break
    }
    "======="{ # This regex specifically matches "======="
        $selectedColor = [Color]::Blue
        Break
    }
    Default {
        $selectedColor = [Color]::Reset
        # No need for break here, as it's the last block
    }
}

Write-Host "$([char]27)[$([int]$selectedColor)m$($Line)$([char]27)[0m"