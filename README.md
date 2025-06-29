# KVM Disk Manager

FastAPI application for managing KVM disk operations with Docker and Helm deployment.

## Structure

```
kvmfun/
├── src/
│   ├── main.py              # FastAPI application entry point
│   ├── api/
│   │   └── disk_routes.py   # API endpoints for disk operations
│   └── modules/
│       ├── disk_attach.py   # Disk attachment functionality
│       └── disk_detach.py   # Disk detachment functionality
├── helm/
│   └── kvmfun/              # Helm chart for Kubernetes deployment
├── Dockerfile               # Container configuration
├── requirements.txt         # Python dependencies
└── build-and-deploy.ps1     # Deployment script
```

## API Endpoints

- `POST /api/v1/disk/attach` - Attach a disk to a VM
- `POST /api/v1/disk/detach` - Detach a disk from a VM
- `GET /api/v1/disk/list/{vm_name}` - List disks attached to a VM
- `GET /health` - Health check endpoint

## Deployment

### Prerequisites
- Rancher Desktop with Kubernetes enabled
- Docker
- Helm

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