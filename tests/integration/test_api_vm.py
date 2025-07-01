# tests/integration/test_api_vm.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.main import app

client = TestClient(app)

# Example VM data for mocking
vm_example = {
    "name": "testvm",
    "status": "shutoff",
    "memory": 2048,
    "vcpus": 2
}

@pytest.fixture
def mock_list_vms():
    with patch("src.api.vm.list_vms", return_value=[vm_example]):
        yield

@pytest.fixture
def mock_create_vm():
    with patch("src.api.vm.create_vm", return_value=vm_example):
        yield

@pytest.fixture
def mock_delete_vm():
    with patch("src.api.vm.delete_vm", return_value=None):
        yield

@pytest.fixture
def mock_start_vm():
    with patch("src.api.vm.start_vm", return_value={"result": "started"}):
        yield

@pytest.fixture
def mock_stop_vm():
    with patch("src.api.vm.stop_vm", return_value={"result": "stopped"}):
        yield

def test_list_vms(mock_list_vms):
    response = client.get("/api/v1/vm")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json()[0]["name"] == "testvm"

def test_create_vm(mock_create_vm):
    payload = {"name": "testvm", "memory": 2048, "vcpus": 2}
    response = client.post("/api/v1/vm", json=payload)
    assert response.status_code == 200 or response.status_code == 201
    assert response.json()["name"] == "testvm"

def test_start_vm(mock_start_vm):
    response = client.post("/api/v1/vm/start/testvm")
    assert response.status_code == 200
    assert response.json()["result"] == "started"

def test_stop_vm(mock_stop_vm):
    response = client.post("/api/v1/vm/stop/testvm")
    assert response.status_code == 200
    assert response.json()["result"] == "stopped"