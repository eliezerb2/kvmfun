# Generic script to uninstall a service and clean up all related resources
# Usage: .\uninstall-service.ps1 -ServiceName <service-name>
param(
    [Parameter(Mandatory=$true)]
    [string]$ServiceName
)

# Function to delete resources by type with service name prefix
function Remove-Resources {
    param(
        [string]$ResourceType
    )
    
    Write-Host "Deleting ${ResourceType}s..."
    
    # Delete exact match first
    kubectl delete $ResourceType $ServiceName --ignore-not-found
    
    # Find and delete resources with prefix
    $resources = kubectl get $ResourceType -o jsonpath="{.items[*].metadata.name}" | 
                 ForEach-Object { $_ -split ' ' } | 
                 Where-Object { $_ -like "$ServiceName*" }
    
    foreach ($resource in $resources) {
        if ($resource) {
            Write-Host "Deleting $ResourceType`: $resource"
            kubectl delete $ResourceType $resource --ignore-not-found
        }
    }
}

Write-Host "Uninstalling $ServiceName..."

# Uninstall the Helm release
helm uninstall $ServiceName

Write-Host "Deleting all resources with prefix: $ServiceName"

# Delete resources by type
Remove-Resources -ResourceType "pod"
Remove-Resources -ResourceType "job"
Remove-Resources -ResourceType "deployment"
Remove-Resources -ResourceType "service"
Remove-Resources -ResourceType "secret"
Remove-Resources -ResourceType "serviceaccount"
Remove-Resources -ResourceType "role"
Remove-Resources -ResourceType "rolebinding"
Remove-Resources -ResourceType "configmap"
Remove-Resources -ResourceType "pvc"

Write-Host "$ServiceName release and all related resources uninstalled."