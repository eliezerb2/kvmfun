import logging
from tests.e2e.test_list_volumes import test_list_volumes

logger = logging.getLogger(__name__)

def pool_exists(client, pool_name: str) -> bool:
    """
    Check if a storage pool exists.

    Args:
        client: HTTP client for making requests
        pool_name: Name of the storage pool

    Returns:
        bool: True if the pool exists, False otherwise
    """
    logger.info(f"Checking if pool exists: {pool_name}")
    try:
        list_response = client.get(f"/api/v1/volume/{pool_name}/list")
        logger.debug(f"List response: {list_response.status_code} {list_response.json()}")
        return list_response.status_code == 200
    except Exception as e:
        logger.error(f"Error checking if pool exists: {e}")
        return False

def volume_exists(client, pool_name: str, volume_name: str) -> bool:
    """
    Check if a volume exists in the specified storage pool.

    Args:
        client: HTTP client for making requests
        pool_name: Name of the storage pool
        full_volume_path: Full path of the volume to check

    Returns:
        bool: True if the volume exists, False otherwise
    """
    logger.info(f"Checking if volume exists: {volume_name} in pool {pool_name}")
    if not pool_exists(client, pool_name):
        logger.error(f"Storage pool '{pool_name}' does not exist.")
        return False
    try:
        logger.debug(f"Listing volumes in pool '{pool_name}'...")
        volumes = test_list_volumes(client, pool_name)
        return any(v['name'] == volume_name for v in volumes)
    except Exception as e:
        logger.error(f"Error checking if volume exists: {e}")
        return False
    
def vm_exists(client, vm_name: str) -> bool:
    """
    Check if a VM exists.

    Args:
        client: HTTP client for making requests
        vm_name: Name of the VM to check

    Returns:
        bool: True if the VM exists, False otherwise
    """
    logger.info(f"Checking if VM exists: {vm_name}")
    try:
        list_response = client.get("/api/v1/vm/list")
        logger.debug(f"List response: {list_response.status_code} {list_response.json()}")
        if list_response.status_code != 200:
            raise Exception(f"Failed to list VMs: {list_response.status_code} {list_response.text}")

        vms = list_response.json().get('vms', [])
        return any(vm['name'] == vm_name for vm in vms)
    except Exception as e:
        logger.error(f"Error checking if VM exists: {e}")
        return False