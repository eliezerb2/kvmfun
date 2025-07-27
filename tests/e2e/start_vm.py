import logging
import json
import pytest # type: ignore
from tests.e2e.test_get_vm_info import test_get_vm_info


logger: logging.Logger = logging.getLogger(__name__)

@pytest.mark.e2e
@pytest.mark.dependency(name="start_vm")
@pytest.mark.dependency(depends=["create_vm"])
def test_start_vm(test_context) -> None:
    """
    Test the real start_vm function.
    This function is intended to be run in an environment where the necessary
    dependencies (like a running libvirt instance) are available.
    """
    try:
        client = test_context.get("client")
        vm_name: str = test_context.get("vm_name")
        logger.info(f"\nStarting VM '{vm_name}'...")
        start_vm_response = client.post(f"/api/v1/vm/start/{vm_name}")
        logger.debug(f"Start VM response: {start_vm_response.status_code}\n{json.dumps(start_vm_response.json(), indent=4)}")
        assert start_vm_response.status_code == 200
        test_get_vm_info(test_context)
        return None
    except Exception as e:
        logger.error(f"Error during VM start: {e}")
        raise