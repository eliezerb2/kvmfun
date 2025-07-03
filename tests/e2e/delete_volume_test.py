from logging import log
from src.api.volume_endpoints import logger
from tests.e2e.utils import volume_exists

def delete_volume_test(client, pool_name: str, volume_name: str) -> bool:
    """
    Test deleting a volume by its full path.
    
    Args:
        client: HTTP client for making requests
        pool_name: Name of the storage pool
        full_volume_path: Full path of the volume to delete

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    logger.debug("===================== delete volume =====================")
    try:
        if not volume_exists(client, pool_name, volume_name):
            logger.info(f"Volume '{volume_name}' does not exist, skipping deletion.")
            return True
    except Exception as e:
        logger.error(f"Error during volume list: {e}")
        raise
    try:   
        logger.info(f"Deleting volume '{volume_name}'...")
        response = client.delete(f"/api/v1/volume/{pool_name}/delete/{volume_name}")
        logger.debug(f"Delete volume response: {response.status_code} {response.json()}")
        assert response.status_code in [200, 204]
        assert not volume_exists(client, pool_name, volume_name)
        return True
    except Exception as e:
        logger.error(f"Error during volume deletion: {e}")
        raise