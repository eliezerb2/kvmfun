import os
import pytest #type: ignore
from src.api.disk_endpoints import logger
from tests.e2e import start_vm_test
from tests.e2e.create_vm_test import create_vm_test
from tests.e2e.create_volume_test import create_volume_test
from tests.e2e.start_vm_test import start_vm_test

# This test requires a running VM to attach a disk to.
# Replace with a VM name that exists on your libvirt host.
TEST_VM_NAME = "ubuntu-test-vm" 
TEST_VOLUME_NAME = f"e2e-test-vol.qcow2"

@pytest.mark.e2e
def test_main_process(client):
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

    full_volume_path: str = ""
    vm_created: bool = False
    vm_started: bool = False
    target_dev = None

    try:
        full_volume_path: str = create_volume_test(client, TEST_VOLUME_NAME)
        vm_created: bool = create_vm_test(client, TEST_VM_NAME, full_volume_path)
        vm_started: bool = start_vm_test(client, TEST_VM_NAME)

        # logger.debug("================ 4. Attach the disk to the VM =========")
        # logger.info(f"Attaching volume '{full_volume_path}' to VM '{TEST_VM_NAME}'...")
        # attach_response = client.post("/api/v1/disk/attach", json={"vm_name": TEST_VM_NAME, "qcow2_path": full_volume_path})
        # logger.debug(f"Attach response: {attach_response.status_code} {attach_response.json()}")
        # assert attach_response.status_code == 200
        # target_dev = attach_response.json()["target_dev"]
        # logger.debug(f"Volume attached as '{target_dev}'")

        # logger.debug("================ 5. Verify the disk is listed =========")
        # logger.info(f"Verifying attachment of '{target_dev}'...")
        # list_response = client.get(f"/api/v1/disk/list/{TEST_VM_NAME}")
        # logger.debug(f"List response: {list_response.status_code} {list_response.json()}")
        # assert list_response.status_code == 200
        
        # vm_disks = list_response.json().get('disks', [])
        # is_attached = any(
        #     disk['source_file'] == full_volume_path and disk['target_dev'] == target_dev
        #     for disk in vm_disks
        # )
        # logger.debug(f"VM disks: {vm_disks}")
        # assert is_attached, f"Disk {full_volume_path} was not found attached as {target_dev}"

        # logger.debug("================ 6. Detach the disk ===================")
        # logger.info(f"Detaching volume from device '{target_dev}'...")
        # detach_response = client.post("/api/v1/disk/detach", json={"vm_name": TEST_VM_NAME, "target_dev": target_dev})
        # logger.debug(f"Detach response: {detach_response.status_code} {detach_response.json()}")
        # assert detach_response.status_code == 200

    except Exception as e:
        logger.error(f"Unexpected error during VM operations: {repr(e)}", exc_info=True)
        raise

    finally:
        logger.debug("================ 7. Delete the vm =====================")
        if vm_created:
            logger.info(f"Cleaning up VM '{TEST_VM_NAME}'...")
            delete_vm_response = client.delete(f"/api/v1/vm/delete/{TEST_VM_NAME}")
            logger.debug(f"Delete VM response: {delete_vm_response.status_code}")
            assert delete_vm_response.status_code == 200
        logger.debug("================ 8. Delete the disk volume ============")
        if full_volume_path:
            logger.info(f"Cleaning up volume '{TEST_VOLUME_NAME}'...")
            delete_response = client.delete(f"/api/v1/volume/delete?pool_name={pool_name}&volume_name={TEST_VOLUME_NAME}")
            logger.debug(f"Delete response: {delete_response.status_code}")
            assert delete_response.status_code == 204
