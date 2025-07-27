import logging
import json
import pytest # type: ignore
from tests.config import config
from tests.e2e.test_get_vm_info import test_get_vm_info


logger: logging.Logger = logging.getLogger(__name__)

@pytest.mark.e2e
@pytest.mark.dependency(name="detach_disk")
@pytest.mark.dependency(depends=["attach_disk"])
def test_detach_disk(test_context) -> None:
    """
    Test the real detach_disk function.
    """
    try:
        client = test_context.get("client")
        vm_name: str = test_context.get("vm_name")
        data_disk_device: str = test_context.get("volumes").get(config.TEST_DATA_VOLUME_NAME).get("device")
        logger.info(f"\nDetaching disk '{data_disk_device}' from VM '{vm_name}'...")
        # construct the payload
        detach_disk_request_payload = {
            "vm_name": vm_name,
            "target_dev": data_disk_device
        }
        logger.debug(f"Detach disk request payload:\n{json.dumps(detach_disk_request_payload, indent=4)}")
        detach_disk_response = client.post(f"/api/v1/disk/detach", json=detach_disk_request_payload)
        logger.debug(f"Detach disk response: {detach_disk_response.status_code}\n{json.dumps(detach_disk_response.json(), indent=4)}")
        assert detach_disk_response.status_code == 200
        test_get_vm_info(test_context)
        return None
    except Exception as e:
        logger.error(f"Error during disk detach: {e}")
        raise