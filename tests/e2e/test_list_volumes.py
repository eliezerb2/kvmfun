import json
import logging

logger: logging.Logger = logging.getLogger(__name__)

def test_list_volumes(client, pool_name: str) -> list:
    """
    Test listing all volumes in a given storage pool.

    Args:
        client: HTTP client for making requests
        pool_name: Name of the storage pool

    Returns:
        list: List of dictionaries containing volume names and paths
    """
    logger.debug("===================== list volumes =====================")
    try:
        logger.info(f"Listing volumes in pool '{pool_name}'...")
        list_volumes_response = client.get(f"/api/v1/volume/{pool_name}/list")
        if list_volumes_response.status_code != 200:
            raise Exception(f"Failed to list volumes: {list_volumes_response.status_code}\n{json.dumps(list_volumes_response.json, indent=4)}")
        volumes = list_volumes_response.json().get('volumes', [])
        return volumes
    except Exception as e:
        logger.error(f"Error during volume list: {e}")
        raise