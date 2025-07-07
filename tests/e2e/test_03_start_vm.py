import logging

logger = logging.getLogger(__name__)

def test_start_vm(client, vm_name: str) -> None:
    """
    Test the real start_vm function.
    This function is intended to be run in an environment where the necessary
    dependencies (like a running libvirt instance) are available.
    """
    logger.debug("===================== start VM =====================")
    try:
        logger.info(f"\nStarting VM '{vm_name}'...")
        start_response = client.post(f"/api/v1/vm/start/{vm_name}")
        logger.debug(f"Start response: {start_response.status_code} {start_response.json()}")
        assert start_response.status_code == 200
        return None
    except Exception as e:
        logger.error(f"Error during VM start: {e}")
        raise