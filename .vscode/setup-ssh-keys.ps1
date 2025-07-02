param(
    # User for SSH connection to the libvirt host/VM
    [String]$sshUser = "osboxes",
    # Address of the libvirt host/VM. Use 127.0.0.1 to avoid IPv6 resolution issues.
    [String]$serverAddress = "127.0.0.1",
    # Port on the host that is forwarded to the VM's SSH port (22)
    [string]$serverPort = "2222",
    # Filename for the generated SSH key pair
    [String]$keyFileName = "kvmfun-ssh-vm-key",
    # SSH key type (e.g., ed25519, rsa)
    [String]$sshKeyType = "ed25519",
    # SSH key strength (bits)
    [String]$sshkeyStrength = "4096",
    # Name of the Kubernetes secret to store the key
    [String]$secretName = "libvirt-server-ssh-key-secret"
)

$keyPath = "$env:USERPROFILE\.ssh\$keyFileName"

Write-Host "Checking for existing SSH key at $keyPath"
if (-not (Test-Path $keyPath)) {
    ssh-keygen -t $sshKeyType -b $sshkeyStrength -f $keyPath -N '""'
    Write-Host "Generated new SSH key at $keyPath"
}

Write-Host "Testing connection to $serverAddress on port $serverPort..."
$connectionTest = Test-NetConnection -ComputerName $serverAddress -Port $serverPort -InformationLevel Quiet
if (-not $connectionTest) {
    Write-Host "ERROR: Cannot connect to $serverAddress on port $serverPort." -ForegroundColor Red
    Write-Host "Please ensure the VM is running and port forwarding is correctly configured (e.g., host port $serverPort -> VM port 22)." -ForegroundColor Yellow
    exit 1
}
Write-Host "Connection successful." -ForegroundColor Green

Write-Host "Checking if SSH key authentication is already working..."
ssh -i $keyPath -o "IdentitiesOnly=yes" -o "PasswordAuthentication=no" -p $serverPort $sshUser@$serverAddress "echo 'SSH key auth successful'" 2>$null
$isAuthorized = ($LASTEXITCODE -eq 0)

if (-not $isAuthorized) {
    Write-Host "SSH key not found on remote host. You will be prompted for a password to add it." -ForegroundColor Yellow
    
    # Get public key content and pipe it to ssh.
    # ssh.exe will handle the password prompt interactively.
    # The remote command ensures the .ssh directory exists with correct permissions
    # and then appends the key to authorized_keys.
    # Using -o StrictHostKeyChecking=accept-new to avoid interactive prompt for host key.
    Get-Content "$keyPath.pub" -Raw | ssh -p $serverPort -o "StrictHostKeyChecking=accept-new" "$sshUser@$serverAddress" "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"

    # Verify that the key was added correctly and key-based auth now works
    Write-Host "Verifying SSH key authentication..."
    ssh -i $keyPath -o "IdentitiesOnly=yes" -o "PasswordAuthentication=no" -p $serverPort $sshUser@$serverAddress "echo 'SSH key auth successful'" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Verification failed. SSH key authentication is not working after adding the key." -ForegroundColor Red
        Write-Host "Please check the password and ensure the user '$sshUser' has permissions to write to ~/.ssh/authorized_keys on the remote host." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Verification successful. SSH key authentication is working." -ForegroundColor Green
}

# Create Kubernetes secret
Write-Host "Creating Kubernetes secret '$secretName' with SSH key..."
kubectl create secret generic $secretName `
    --from-file=id_$sshKeyType=$keyPath `
    --dry-run=client -o yaml | kubectl apply -f -

Write-Host "Secret '$secretName' created/updated successfully." -ForegroundColor Green