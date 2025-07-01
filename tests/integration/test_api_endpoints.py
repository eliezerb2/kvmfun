import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import libvirt

from src.main import app
from src.utils.libvirt_utils import get_connection_dependency
from src.utils.exceptions import DiskNotFound

# Ensure libvirt.VIR_DOMAIN_XML_LIVE exists for tests using mocks
if not hasattr(libvirt, "VIR_DOMAIN_XML_LIVE"):
    libvirt.VIR_DOMAIN_XML_LIVE = 1

@pytest.fixture
def mock_libvirt_connection():
    """Fixture to provide mocked libvirt connection and domain."""
    mock_conn = Mock(spec=libvirt.virConnect)
    mock_dom = Mock(spec=libvirt.virDomain)
    mock_conn.lookupByName.return_value = mock_dom
    # Provide a minimal valid XML for the domain
    mock_dom.XMLDesc.return_value = "<domain><devices></devices></domain>"
    return mock_conn, mock_dom

@pytest.fixture
def override_libvirt_dependency(mock_libvirt_connection):
    """Fixture to override the get_connection_dependency with the mock."""
    mock_conn, _ = mock_libvirt_connection

    def override_get_connection():
        yield mock_conn

    app.dependency_overrides[get_connection_dependency] = override_get_connection
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def client():
    """Fixture to provide a FastAPI TestClient."""
    return TestClient(app)

@pytest.fixture
def client_with_mocks(client, mock_libvirt_connection, override_libvirt_dependency):
    """Fixture to provide a test client with mocked dependencies."""
    mock_conn, mock_dom = mock_libvirt_connection
    yield client, mock_conn, mock_dom

def test_health_endpoint(client_with_mocks):
    """Test health check endpoint."""
    client, _, _ = client_with_mocks
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "version" in response.json()

@patch('src.api.disk.attach_disk')
@patch('src.api.disk.get_next_available_virtio_dev')
def test_attach_disk_success(mock_get_dev, mock_attach, client_with_mocks):
    """Test successful disk attachment with auto-assigned device."""
    client, mock_conn, mock_dom = client_with_mocks
    mock_get_dev.return_value = 'vdb'
    mock_attach.return_value = True

    response = client.post("/api/v1/disk/attach", json={
        "vm_name": "test_vm",
        "qcow2_path": "/path/to/disk.qcow2"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "success", "target_dev": "vdb"}
    mock_conn.lookupByName.assert_called_once_with("test_vm")
    mock_attach.assert_called_once_with(mock_dom, "/path/to/disk.qcow2", "vdb")

def test_attach_disk_vm_not_found(client_with_mocks):
    """Test VM not found scenario during attachment."""
    client, mock_conn, _ = client_with_mocks
    
    # Configure the mock to raise the error that the global handler expects
    mock_conn.lookupByName.side_effect = libvirt.libvirtError("Domain not found: nonexistent_vm")
    
    response = client.post("/api/v1/disk/attach", json={
        "vm_name": "nonexistent_vm",
        "qcow2_path": "/path/to/disk.qcow2"
    })
    assert response.status_code == 404
    assert "The specified VM was not found" in response.json()["detail"]

def test_attach_disk_invalid_vm_name_format(client_with_mocks):
    """Test API response for an invalid VM name format which should trigger Pydantic validation."""
    client, _, _ = client_with_mocks
    response = client.post("/api/v1/disk/attach", json={
        "vm_name": "invalid vm name with spaces",
        "qcow2_path": "/path/to/disk.qcow2"
    })
    assert response.status_code == 422  # Unprocessable Entity for validation errors
    details = response.json()["detail"]
    assert isinstance(details, list) and len(details) > 0
    assert "VM name must contain only alphanumeric characters" in details[0]["msg"]

@patch('src.api.disk.detach_disk')
def test_detach_disk_success(mock_detach, client_with_mocks):
    """Test successful disk detachment."""
    client, mock_conn, _ = client_with_mocks
    mock_detach.return_value = True
    
    response = client.post("/api/v1/disk/detach", json={
        "vm_name": "test_vm",
        "target_dev": "vdb"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    mock_detach.assert_called_once_with(mock_conn, "test_vm", "vdb")

@patch('src.api.disk.detach_disk')
def test_detach_disk_disk_not_found(mock_detach, client_with_mocks):
    """Test disk not found scenario during detachment."""
    client, mock_conn, _ = client_with_mocks
    # Configure the mock to raise the custom exception that the API route catches.
    mock_detach.side_effect = DiskNotFound("Disk 'vdc' not found on vm 'test_vm'")

    response = client.post("/api/v1/disk/detach", json={
        "vm_name": "test_vm",
        "target_dev": "vdc"
    })
    assert response.status_code == 404
    assert "Disk 'vdc' not found" in response.json()["detail"]
    mock_detach.assert_called_once_with(mock_conn, "test_vm", "vdc")

def test_detach_disk_vm_not_found(client_with_mocks):
    """Test VM not found scenario during detachment, handled by the global handler."""
    client, mock_conn, _ = client_with_mocks
    # Configure the mock to raise the libvirt error. The global handler will catch this.
    mock_conn.lookupByName.side_effect = libvirt.libvirtError("Domain not found: nonexistent_vm")

    response = client.post("/api/v1/disk/detach", json={
        "vm_name": "nonexistent_vm",
        "target_dev": "vdb"
    })
    assert response.status_code == 404
    assert "The specified VM was not found" in response.json()["detail"]