import os
from libvirt import libvirtError # type: ignore
import pytest #type: ignore
from contextlib import contextmanager
import warnings
from src.api.disk_endpoints import logger
from tests.e2e.test_delete_volume import test_delete_volume
from tests.e2e.test_delete_vm import test_delete_vm

TEST_VM_NAME = "ubuntu-test-vm" 
TEST_VOLUME_NAME = f"e2e-test-vol.qcow2"
pool_name: str = os.environ.get("LIBVIRT_STORAGE_POOL", "")

@contextmanager
def silent_operations():
    """Context manager to silently ignore assertion errors and warnings"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            yield
        except (AssertionError, libvirtError) as e:
            logger.debug(f"Suppressed error during setup/teardown: {str(e)}")
        except Exception as e:
            logger.warning(f"Unexpected error suppressed: {str(e)}")

def system_cleanup(client):
    """Cleanup function to run before and after all tests"""
    logger.info("Running system cleanup...")
    test_delete_vm(client, TEST_VM_NAME)
    test_delete_volume(client, pool_name, TEST_VOLUME_NAME)
        
@pytest.fixture(scope="session", autouse=True)
def test_context(client):
    with silent_operations():
        system_cleanup(client)
    yield {
        "client": client, 
        "pool_name": pool_name,
        "volume_name": TEST_VOLUME_NAME,
        "vm_name": TEST_VM_NAME,
        "full_volume_path": ""}
    with silent_operations():
        system_cleanup(client)
        
# def test_main_process(client):
#     """
#     Tests the full lifecycle of a disk:
#     1. Create a new disk volume.
#     2. Attach the disk to a VM.
#     3. Verify the disk is listed on the VM.
#     4. Detach the disk.
#     5. Delete the disk volume.
#     """
#     assert pool_name, "LIBVIRT_STORAGE_POOL environment variable must be set for E2E tests"

#     full_volume_path: str = ""
#     vm_created: bool = False
#     vm_started: bool = False
#     target_dev = None

#     try:
#         full_volume_path: str = create_volume_test(client, pool_name, TEST_VOLUME_NAME)
#         vm_created: bool = create_vm_test(client, TEST_VM_NAME, full_volume_path)
#         vm_started: bool = start_vm_test(client, TEST_VM_NAME)

#         # logger.debug("================ 4. Attach the disk to the VM =========")
#         # logger.info(f"Attaching volume '{full_volume_path}' to VM '{TEST_VM_NAME}'...")
#         # attach_response = client.post("/api/v1/disk/attach", json={"vm_name": TEST_VM_NAME, "qcow2_path": full_volume_path})
#         # logger.debug(f"Attach response: {attach_response.status_code} {attach_response.json()}")
#         # assert attach_response.status_code == 200
#         # target_dev = attach_response.json()["target_dev"]
#         # logger.debug(f"Volume attached as '{target_dev}'")

#         # logger.debug("================ 5. Verify the disk is listed =========")
#         # logger.info(f"Verifying attachment of '{target_dev}'...")
#         # list_response = client.get(f"/api/v1/disk/list/{TEST_VM_NAME}")
#         # logger.debug(f"List response: {list_response.status_code} {list_response.json()}")
#         # assert list_response.status_code == 200
        
#         # vm_disks = list_response.json().get('disks', [])
#         # is_attached = any(
#         #     disk['source_file'] == full_volume_path and disk['target_dev'] == target_dev
#         #     for disk in vm_disks
#         # )
#         # logger.debug(f"VM disks: {vm_disks}")
#         # assert is_attached, f"Disk {full_volume_path} was not found attached as {target_dev}"

#         # logger.debug("================ 6. Detach the disk ===================")
#         # logger.info(f"Detaching volume from device '{target_dev}'...")
#         # detach_response = client.post("/api/v1/disk/detach", json={"vm_name": TEST_VM_NAME, "target_dev": target_dev})
#         # logger.debug(f"Detach response: {detach_response.status_code} {detach_response.json()}")
#         # assert detach_response.status_code == 200

#     except Exception as e:
#         logger.error(f"Unexpected error during VM operations: {repr(e)}", exc_info=True)
#         raise

#     # finally:
#         # logger.debug("================ 7. Delete the vm =====================")
#         # if vm_created:
#         #     logger.info(f"Cleaning up VM '{TEST_VM_NAME}'...")
#         #     delete_vm_response = client.delete(f"/api/v1/vm/delete/{TEST_VM_NAME}")
#         #     logger.debug(f"Delete VM response: {delete_vm_response.status_code}")
#         #     assert delete_vm_response.status_code == 200
#         # logger.debug("================ 8. Delete the disk volume ============")
#         # if full_volume_path:
#         #     vol_deleted = delete_volume_test(client, pool_name, full_volume_path)
#         #     assert vol_deleted, "Failed to delete volume"
