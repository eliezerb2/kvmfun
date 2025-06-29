import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from src.main import app

client = TestClient(app)

def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "1.0.0"}

@patch('src.api.disk_routes.get_libvirt_domain')
@patch('src.api.disk_routes.get_next_available_virtio_dev')
@patch('src.api.disk_routes.attach_qcow2_disk')
def test_attach_disk_success(mock_attach, mock_get_dev, mock_get_domain):
    """Test successful disk attachment."""
    mock_conn = Mock()
    mock_dom = Mock()
    mock_get_domain.return_value = (mock_conn, mock_dom)
    mock_get_dev.return_value = 'vdb'
    mock_attach.return_value = True
    
    response = client.post("/api/v1/disk/attach", json={
        "vm_name": "test_vm",
        "qcow2_path": "/path/to/disk.qcow2"
    })
    
    assert response.status_code == 200
    assert response.json() == {"status": "success", "target_dev": "vdb"}

@patch('src.api.disk_routes.get_libvirt_domain')
def test_attach_disk_vm_not_found(mock_get_domain):
    """Test VM not found scenario."""
    import libvirt
    mock_get_domain.side_effect = libvirt.libvirtError("Domain not found")
    
    response = client.post("/api/v1/disk/attach", json={
        "vm_name": "nonexistent_vm",
        "qcow2_path": "/path/to/disk.qcow2"
    })
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

@patch('src.api.disk_routes.libvirt.open')
@patch('src.api.disk_routes.detach_disk')
def test_detach_disk_success(mock_detach, mock_open):
    """Test successful disk detachment."""
    mock_conn = Mock()
    mock_open.return_value = mock_conn
    mock_detach.return_value = True
    
    response = client.post("/api/v1/disk/detach", json={
        "vm_name": "test_vm",
        "target_dev": "vdb"
    })
    
    assert response.status_code == 200
    assert response.json() == {"status": "success"}