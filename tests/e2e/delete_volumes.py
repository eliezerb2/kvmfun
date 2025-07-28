import logging
import json
from tests.e2e.utils import get_volume_path


logger: logging.Logger = logging.getLogger(__name__)

def test_delete_volumes(client, pool_name: str, volumes: dict) -> None:
    """
    Test deleting a list of volumes.
    
    Args:
        client: HTTP client for making requests
        pool_name: Name of the storage pool
        volumes: List of dictionaries containing volume names and paths

    Returns:
        None
    """
    logger.debug("===================== delete volumes =====================")
    try:
        logger.info(f"Deleting volumes '{list(volumes.keys())}' in pool '{pool_name}'...")
        for volume_name in volumes.keys():
            assert delete_volume(client, pool_name, volume_name)
            assert not get_volume_path(client, pool_name, volume_name)
        return
    except Exception as e:
        logger.error(f"Error during volume deletion: {e}")
        raise


def delete_volume(client, pool_name: str, volume_name: str) -> bool:
    """
    Deleting a volume by its full path.
    """
    try:
        if not get_volume_path(client, pool_name, volume_name):
            logger.info(f"Volume '{volume_name}' does not exist, skipping deletion.")
            return True
        logger.info(f"Deleting volume '{volume_name}'...")
        delete_volume_response = client.delete(f"/api/v1/volume/{pool_name}/delete/{volume_name}")
        delete_volume_response_data:str = ''
        if delete_volume_response.status_code not in [200, 204]:
            delete_volume_response_data = delete_volume_response.json()
        logger.debug(f"Delete volume response: {delete_volume_response.status_code}\n{json.dumps(delete_volume_response_data, indent=4)}")
        return delete_volume_response.status_code in [200, 204]
    except Exception as e:
        logger.error(f"Error during volume deletion: {e}")
        raise