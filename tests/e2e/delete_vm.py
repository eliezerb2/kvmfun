import logging
import json
from tests.e2e.utils import vm_exists

logger: logging.Logger = logging.getLogger(__name__)

def test_delete_vm(client, vm_name):
    """
    Test deleting a VM by its name.

    Args:
        client: HTTP client for making requests
        vm_name: Name of the VM to delete

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    logger.debug("===================== delete VM =====================")
    logger.info(f"Deleting VM '{vm_name}'...")
    try:
        # Check if the VM exists before attempting to delete it
        if not vm_exists(client, vm_name):
            logger.info(f"VM '{vm_name}' does not exist, skipping deletion.")
            return True
    except Exception as e:
        logger.error(f"Error during VM list: {e}")
        raise
    try:
        # Attempt to delete the VM
        logger.info(f"VM '{vm_name}' does exist")
        delete_vm_response = client.delete(f"/api/v1/vm/delete/{vm_name}")
        logger.debug(f"Delete VM response: {delete_vm_response.status_code}\n{json.dumps(delete_vm_response.json(), indent=4)}")
        assert delete_vm_response.status_code == 200
        assert not vm_exists(client, vm_name)
        return True
    except Exception as e:
        logger.error(f"Error during VM deletion: {e}")
        raise
