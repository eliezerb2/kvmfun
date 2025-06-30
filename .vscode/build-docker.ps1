# PowerShell script to build the Docker image using environment variables from the .env file

# Parameters
param(
    [string]$envFilePath,     # Path to the .env file
    [string]$Dockerfile,      # Full path to the Dockerfile
    [string]$imageTag,  # Docker image tag
    [switch]$NoCache  # Optional: build with --no-cache
)

# Read the .env file and construct --build-arg parameters if envFilePath is provided
$buildArgs = @()
if ($envFilePath) {
    $buildArgs = Get-Content $envFilePath |
        Where-Object { $_.Trim() -ne '' -and $_ -match '=' -and $_ -notmatch '^#' } |
        ForEach-Object {
            $name, $value = $_ -split '=', 2
            "--build-arg $name=$value"
        }
}
$buildArgsStr = $buildArgs -join ' '

# Build the Docker image
# Use repository root as build context and specify Dockerfile with -f
$noCacheArg = if ($NoCache) { '--no-cache' } else { '' }
# Resolve the repository root relative to the script's location. This is more robust.
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$modulePath = Split-Path -Leaf (Split-Path -Parent $Dockerfile)

Write-Host "Building Docker image with tag: $imageTag"
Write-Host "Using Dockerfile: $Dockerfile"
Write-Host "Build arguments: $buildArgsStr"
Write-Host "Using .env file: $envFilePath"
Write-Host "Build context: $repoRoot"
Write-Host "Module path: $modulePath"
Write-Host "Cache: $(if ($NoCache) { 'disabled' } else { 'enabled' })"

$buildCommand = "docker build $noCacheArg $buildArgsStr --build-arg MODULE_PATH=$modulePath -t $imageTag -f `"$Dockerfile`" `"$repoRoot`""
Write-Host "Executing: $buildCommand"
Invoke-Expression $buildCommand