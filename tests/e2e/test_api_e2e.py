import os
from urllib import response
import uuid
import pytest

# This test requires a running VM to attach a disk to.
# Replace with a VM name that exists on your libvirt host.
TEST_VM_NAME = "ubuntu-test-vm" 

@pytest.mark.e2e
def test_disk_lifecycle(client):
    """
    Tests the full lifecycle of a disk:
    1. Create a new disk volume.
    2. Attach the disk to a VM.
    3. Verify the disk is listed on the VM.
    4. Detach the disk.
    5. Delete the disk volume.
    """
    pool_name = os.environ.get("LIBVIRT_STORAGE_POOL")
    assert pool_name, "LIBVIRT_STORAGE_POOL environment variable must be set for E2E tests"

    volume_name = f"e2e-test-vol-{uuid.uuid4()}.qcow2"
    volume_path = None
    target_dev = None

    try:
        # 1. Create a new disk volume
        print(f"\nCreating volume '{volume_name}' in pool '{pool_name}'...")
        create_response = client.post(
            "/api/v1/disk/create", 
            json={
                "pool_name": pool_name, 
                "volume_name": volume_name, 
                "size_gb": 1
            }
        )
        assert create_response.status_code == 201
        volume_path = create_response.json()["volume_path"]
        print(f"Volume created at: {volume_path}")

        # 2. Attach the disk
        print(f"Attaching volume to VM '{TEST_VM_NAME}'...")
        attach_response = client.post("/api/v1/disk/attach", json={"vm_name": TEST_VM_NAME, "qcow2_path": volume_path})
        print(attach_response.status_code, attach_response.json())
        assert attach_response.status_code == 200
        target_dev = attach_response.json()["target_dev"]
        print(f"Volume attached as '{target_dev}'")

        # 3. Verify the disk is listed
        print("Verifying attachment...")
        list_response = client.get(f"/api/v1/vm/list/{TEST_VM_NAME}")
        print(list_response.status_code, list_response.json())
        assert list_response.status_code == 200
        attached_disks = [disk['source_file'] for disk in list_response.json().get('disks', [])]
        assert volume_path in attached_disks

        # 4. Detach the disk
        print("Detaching volume...")
        detach_response = client.post("/api/v1/disk/detach", json={"vm_name": TEST_VM_NAME, "target_dev": target_dev})
        print(detach_response.status_code, detach_response.json())
        assert detach_response.status_code == 200

    finally:
        # 5. Clean up and delete the disk volume
        if volume_path:
            print(f"Cleaning up volume '{volume_name}'...")
            delete_response = client.delete(f"/api/v1/disk/delete?pool_name={pool_name}&volume_name={volume_name}")
            print(delete_response.status_code, delete_response.json())
            assert delete_response.status_code == 204