import logging
import pytest # type: ignore
import json
import xml.etree.ElementTree as ET

# from tests.config import config


logger: logging.Logger = logging.getLogger(__name__)

def test_get_vm_info(test_context) -> None:
    """
    Test the real get_vm_info function.
    This function is intended to be run in an environment where the necessary
    dependencies (like a running libvirt instance) are available.
    """
    logger.debug("===================== get VM info ================")
    try:
        client = test_context.get("client")
        vm_name: str = test_context.get("vm_name")
        logger.info(f"getting info for VM '{vm_name}'...")
        get_vm_info_response = client.post(f"/api/v1/vm/get_info/{vm_name}")
        assert get_vm_info_response.status_code == 200
        get_vm_info_response_data = get_vm_info_response.json()
        logger.debug(f"Get info response: {get_vm_info_response.status_code}\n{json.dumps(get_vm_info_response_data, indent=4)}")
        return None
    except Exception as e:
        logger.error(f"Error during VM start: {e}")
        raise