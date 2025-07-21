import pytest  # type: ignore
import logging
import json
from tests.e2e.utils import vm_exists
from tests.config import config
from tests.e2e.test_get_vm_info import test_get_vm_info


logger = logging.getLogger(__name__)

@pytest.mark.e2e
@pytest.mark.dependency(name="create_vm")
@pytest.mark.dependency(depends=["create_volumes"])
def test_create_vm(test_context) -> None:
    """
    Test the real create_vm function.
    This function is intended to be run in an environment where the necessary
    dependencies (like a running libvirt instance) are available.
    """
    client = test_context.get("client")
    vm_name: str = test_context.get("vm_name")
    full_os_volume_path: str = test_context.get("volumes").get(config.TEST_OS_VOLUME_NAME).get("path")
    
    try:
        if vm_exists(client, vm_name):
            logger.warning(f"VM '{vm_name}' already exists, skipping creation.")
            return None
        logger.info(f"\nCreating VM '{vm_name}'...")
        create_vm_request_payload: dict = {
            "vm_name": vm_name,
            "memory_mb": config.TEST_VM_MEMORY_MB,
            "vcpu_count": config.TEST_VM_VCPUS,
            "disk_path": full_os_volume_path,
            "disk_name": config.TEST_OS_VOLUME_NAME,
            "network_name": config.TEST_VM_NETWORK_NAME
        }
        logger.debug(f"Create VM request payload:\n{json.dumps(create_vm_request_payload, indent=4)}")
        create_vm_response = client.post(
            "/api/v1/vm/create",
            json=create_vm_request_payload
        )
        logger.debug(f"Create VM response: {create_vm_response.status_code}\n{json.dumps(create_vm_response.json(), indent=4)}")
        assert create_vm_response.status_code == 201
        assert vm_exists(client, vm_name)
        test_get_vm_info(test_context)
        
        return None
    except Exception as e:
        logger.error(f"Error during VM creation: {e}")
        raise