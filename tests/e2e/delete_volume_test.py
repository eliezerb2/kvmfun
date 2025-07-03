from src.api.volume_endpoints import logger

def delete_volume_test(client, pool_name: str, full_volume_path: str) -> bool:
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
    logger.debug(f"Checking if volume exists: {full_volume_path}")
    # Use list_volumes to check if the volume exists
    list_response = client.get(f"/api/v1/volume/{pool_name}/list")
    logger.debug(f"List response: {list_response.status_code} {list_response.json()}")
    assert list_response.status_code == 200
    volumes = list_response.json().get('volumes', [])
    if not any(v['name'] == full_volume_path for v in volumes):
        logger.info(f"Volume '{full_volume_path}' does not exist, skipping deletion.")
        return True

    logger.info(f"Deleting volume '{full_volume_path}'...")
    response = client.delete(f"/api/v1/volume/{pool_name}/delete/{full_volume_path}")
    if response.status_code == 204:
        return True
    else:
        raise Exception(f"Failed to delete volume: {response.status_code} {response.text}")