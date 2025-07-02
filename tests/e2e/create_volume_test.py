import os
from src.api.volume_endpoints import logger

def create_volume_test(client, full_volume_path: str) -> str:
    """
    Test the real create_volume function.
    This function is intended to be run in an environment where the necessary
    dependencies (like a running libvirt instance) are available.
    """

    logger.debug("===================== create volume =====================")

    pool_name = os.environ.get("LIBVIRT_STORAGE_POOL")
    assert pool_name, "LIBVIRT_STORAGE_POOL environment variable must be set for E2E tests"

    try:
        logger.debug(f"Checking if volume exists: {full_volume_path}")
        # Use list_volumes to check if the volume already exists
        list_response = client.get(f"/api/v1/volume/list/{pool_name}")
        logger.debug(f"List response: {list_response.status_code} {list_response.json()}")
        assert list_response.status_code == 200
        volumes = list_response.json().get('volumes', [])
        if any(v['name'] == full_volume_path for v in volumes):
            logger.info(f"Volume '{full_volume_path}' already exists, skipping creation.")
            return full_volume_path
        
        logger.info(f"\nCreating volume '{full_volume_path}' in pool '{pool_name}'...")
        create_response = client.post(
            "/api/v1/volume/create", 
            json={
                "pool_name": pool_name,
                "volume_name": full_volume_path,
                "size_gb": 1
            }
        )
        logger.debug(f"Create response: {create_response.status_code} {create_response.json()}")
        assert create_response.status_code == 201
        # The API now returns the full path, so no manual concatenation is needed.
        full_volume_path = create_response.json()["volume_path"]
        logger.debug(f"Volume created at: {full_volume_path}")
        return full_volume_path
    except Exception as e:
        logger.error(f"Error during volume creation: {e}")
        raise
    
