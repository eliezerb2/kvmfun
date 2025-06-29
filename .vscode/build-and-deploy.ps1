# Build and Deploy Script for Rancher Desktop
# This script builds the Docker image and deploys it using Helm

param(
    [string]$ImageTag = "latest",     # Docker image tag
    [string]$Namespace = "default",   # Kubernetes namespace
    [string]$LogFile = "build-deploy.log"  # Log file path
)

# Function to log messages to both console and file
function Write-Log {
    param([string]$Message, [string]$Color = "White")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Write-Host $Message -ForegroundColor $Color
    Add-Content -Path $LogFile -Value $logMessage
}

# Initialize log file
"Build and Deploy Log - $(Get-Date)" | Out-File -FilePath $LogFile

Write-Log "Starting build and deployment process" "Green"
Write-Log "Image Tag: $ImageTag, Namespace: $Namespace" "Yellow"

# Step 1: Build Docker image
Write-Log "Building Docker image kvmfun:$ImageTag..." "Green"
docker build -t kvmfun:$ImageTag -f docker/Dockerfile . 2>&1 | Tee-Object -FilePath $LogFile -Append

if ($LASTEXITCODE -ne 0) {
    Write-Log "Docker build failed! Check $LogFile for details" "Red"
    exit 1
}
Write-Log "Docker build completed successfully" "Green"

# Step 2: Deploy with Helm
Write-Log "Deploying with Helm to namespace '$Namespace'..." "Green"
helm upgrade --install kvmfun ./helm/kvmfun --namespace $Namespace --set image.tag=$ImageTag 2>&1 | Tee-Object -FilePath $LogFile -Append

if ($LASTEXITCODE -eq 0) {
    Write-Log "Deployment successful!" "Green"
    
    # Step 3: Display service information
    Write-Log "Getting service information..." "Yellow"
    kubectl get svc kvmfun -n $Namespace 2>&1 | Tee-Object -FilePath $LogFile -Append
    
    Write-Log "Deployment completed. Check $LogFile for full details" "Green"
} else {
    Write-Log "Deployment failed! Check $LogFile for details" "Red"
    exit 1
}