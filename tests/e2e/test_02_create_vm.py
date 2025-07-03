from logging import log
import pytest  # type: ignore
from src.api.vm_endpoints import logger
from tests.e2e.utils import vm_exists

@pytest.mark.e2e
@pytest.mark.dependency(depends=["test_create_volume"])
def test_create_vm(test_context) -> bool:
    """
    Test the real create_vm function.
    This function is intended to be run in an environment where the necessary
    dependencies (like a running libvirt instance) are available.
    """
    logger.debug("===================== create VM =====================")
    client = test_context.get("client")
    vm_name: str = test_context.get("vm_name")
    full_volume_path: str = test_context.get("full_volume_path")
    try:
        if vm_exists(client, vm_name):
            logger.info(f"VM '{vm_name}' already exists, skipping creation.")
            return True
        logger.info(f"\nCreating VM '{vm_name}'...")
        json: dict = {
            "vm_name": vm_name,
            "memory_mb": 1024,
            "vcpu_count": 1,
            "disk_path": full_volume_path,
            "network_name": "default"
        }
        logger.debug(f"JSON: {json}")
        create_response = client.post(
            "/api/v1/vm/create",
            json=json
        )
        logger.debug(f"Create response: {create_response.status_code} {create_response.json()}")
        assert create_response.status_code == 201
        assert vm_exists(client, vm_name)
        return True
    except Exception as e:
        logger.error(f"Error during VM creation: {e}")
        raise