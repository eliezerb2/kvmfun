# Build and Deploy Script for Rancher Desktop
param(
    [string]$ImageTag = "latest",
    [string]$Namespace = "default"
)

Write-Host "Building Docker image..." -ForegroundColor Green
docker build -t kvmfun:$ImageTag -f docker/Dockerfile .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Deploying with Helm..." -ForegroundColor Green
helm upgrade --install kvmfun ./helm/kvmfun --namespace $Namespace --set image.tag=$ImageTag

if ($LASTEXITCODE -eq 0) {
    Write-Host "Deployment successful!" -ForegroundColor Green
    Write-Host "Getting service info..." -ForegroundColor Yellow
    kubectl get svc kvmfun -n $Namespace
} else {
    Write-Host "Deployment failed!" -ForegroundColor Red
    exit 1
}