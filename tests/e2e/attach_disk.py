import json
import logging
import pytest # type: ignore
from tests.config import config
from tests.e2e.test_get_vm_info import test_get_vm_info


logger: logging.Logger = logging.getLogger(__name__)

@pytest.mark.e2e
@pytest.mark.dependency(name="attach_disk")
@pytest.mark.dependency(depends=["start_vm"])
def test_attach_disk(test_context) -> None:
    """
    Test the real attach_disk function.
    """
    try:
        client = test_context.get("client")
        vm_name: str = test_context.get("vm_name")
        full_data_volume_path: str = test_context.get("volumes").get(config.TEST_DATA_VOLUME_NAME).get("path")
        disk_name: str = config.TEST_DATA_VOLUME_NAME
        logger.info(f"\nAttaching volume '{full_data_volume_path}' to VM '{vm_name}' as '{disk_name}'...")
        attach_request_payload: dict = {
            "vm_name": vm_name,
            "qcow2_path": full_data_volume_path,
            "disk_name": disk_name
        }
        logger.debug(f"Attach request payload:\n{json.dumps(attach_request_payload, indent=4)}")
        attach_response = client.post("/api/v1/disk/attach", json=attach_request_payload)
        logger.debug(f"Attach response: {attach_response.status_code}\n{json.dumps(attach_response.json(), indent=4)}")
        assert attach_response.status_code == 200
        test_get_vm_info(test_context)
        # setting the disk dev in the test context
        test_context["volumes"].update({disk_name: {"device": attach_response.json()["target_dev"]}})
        logger.debug(f"Volumes updated:\n{json.dumps(test_context['volumes'], indent=4)}")
        return None
    except Exception as e:
        logger.error(f"Error during disk attachment: {e}")
        raise