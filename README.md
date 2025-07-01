# KVM Disk Manager

FastAPI application for managing KVM disk operations with Docker and Helm deployment.

## Structure

```
kvmfun/
├── src/
│   ├── main.py              # FastAPI application entry point
│   ├── api/
│   │   └── disk_routes.py   # API endpoints for disk operations
│   └── services/
│       ├── disk_attach.py   # Disk attachment functionality
│       └── disk_detach.py   # Disk detachment functionality
├── helm/
│   └── kvmfun/              # Helm chart for Kubernetes deployment
├── docker/
│   └── Dockerfile           # Container configuration
├── tests/                   # Unit and integration tests
├── requirements.txt         # Python dependencies
└── .vscode/
    └── build-and-deploy.ps1 # Deployment script
```

## API Endpoints

- `POST /api/v1/disk/attach` - Attach a disk to a VM
- `POST /api/v1/disk/detach` - Detach a disk from a VM
- `GET /api/v1/disk/list/{vm_name}` - List disks attached to a VM
- `GET /health` - Health check endpoint

## API Examples

### Attach Disk

```bash
curl -X POST "http://localhost:8000/api/v1/disk/attach" \
  -H "Content-Type: application/json" \
  -d '{
    "vm_name": "my_ubuntu_vm",
    "qcow2_path": "/var/lib/libvirt/images/data.qcow2"
  }'
```

**Response:**

```json
{
  "status": "success",
  "target_dev": "vdb"
}
```

### Detach Disk

```bash
curl -X POST "http://localhost:8000/api/v1/disk/detach" \
  -H "Content-Type: application/json" \
  -d '{
    "vm_name": "my_ubuntu_vm",
    "target_dev": "vdb"
  }'
```

**Response:**

```json
{
  "status": "success"
}
```

### List Disks

```bash
curl "http://localhost:8000/api/v1/disk/list/my_ubuntu_vm"
```

**Response:**

```json
{
  "vm_name": "my_ubuntu_vm",
  "disks": [
    {
      "target_dev": "vda",
      "source_file": "/var/lib/libvirt/images/ubuntu.qcow2",
      "bus": "virtio"
    },
    {
      "target_dev": "vdb",
      "source_file": "/var/lib/libvirt/images/data.qcow2",
      "bus": "virtio"
    }
  ]
}
```

## Deployment

### Prerequisites

- Rancher Desktop with Kubernetes enabled
- Docker
- Helm
- Access to libvirt/KVM host

### Build and Deploy

```powershell
.\.vscode\build-and-deploy.ps1 -ImageTag "v1.0" -Namespace "kvmfun"
```

### Manual Steps

```powershell
# Build image
docker build -t kvmfun:latest -f docker/Dockerfile .

# Deploy with Helm
helm install kvmfun ./helm/kvmfun

# Check deployment
kubectl get pods
kubectl get svc
```

## Usage

Access the API at `http://localhost:8000` (after port-forwarding):

```powershell
kubectl port-forward svc/kvmfun 8000:80
```

API documentation available at `http://localhost:8000/docs`

## Testing

### Run Unit Tests

```powershell
python -m pytest tests/ -v
```

### Run Integration Tests

```powershell
python -m pytest tests/integration/ -v
```

### Test Coverage

```powershell
python -m pytest --cov=src tests/
```

## Environment Variables

- `DEBUG` - Enable debug mode (default: false)
- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 8000)

## Troubleshooting

### Common Issues

**1. VM Not Found (404)**

```json
{"detail": "VM 'my_vm' not found"}
```

- Verify VM name exists: `virsh list --all`
- Check libvirt connection

**2. Disk Already Attached**

```json
{"detail": "Target device 'vdb' is already in use"}
```

- List current disks: `GET /api/v1/disk/list/{vm_name}`
- Use different target device or detach existing disk

**3. Permission Denied**

```json
{"detail": "Failed to open connection to qemu:///system"}
```

- Ensure libvirt permissions
- Check if running in privileged container

**4. Container Won't Start**

- Check logs: `kubectl logs deployment/kvmfun`
- Verify libvirt dependencies in container
- Check resource limits

### Debug Commands

```powershell
# Check pod status
kubectl get pods -l app.kubernetes.io/name=kvmfun

# View logs
kubectl logs -f deployment/kvmfun

# Exec into container
kubectl exec -it deployment/kvmfun -- /bin/bash

# Test libvirt connection
virsh -c qemu:///system list
```

### Log Files

- Build logs: `build-deploy.log`
- Application logs: Available via `kubectl logs`
- Libvirt logs: `/var/log/libvirt/`

## FAQ

**Q: Can I attach multiple disks simultaneously?**
A: No, use separate API calls for each disk.

**Q: What disk formats are supported?**
A: Currently only QCOW2 format is supported.

**Q: How do I create a QCOW2 disk?**
A: Use `qemu-img create -f qcow2 disk.qcow2 10G`

**Q: Can I attach disks to stopped VMs?**
A: No, VM must be running for hot-attach operations.

**Q: How do I persist disk attachments?**
A: Attachments are automatically persisted to VM configuration.
