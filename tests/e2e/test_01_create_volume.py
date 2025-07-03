import pytest # type: ignore
from src.api.volume_endpoints import logger
from tests.e2e.utils import volume_exists

@pytest.mark.e2e
@pytest.mark.dependency(name="test_create_volume")
def test_create_volume(test_context) -> bool:
    """
    Test the real create_volume function.
    This function is intended to be run in an environment where the necessary
    dependencies (like a running libvirt instance) are available.
    """
    logger.debug("===================== create volume =====================")
    client = test_context.get("client")
    pool_name: str = test_context.get("pool_name")
    volume_name: str = test_context.get("volume_name")
    try:
        if volume_exists(client, pool_name, volume_name):
            logger.info(f"Volume '{volume_name}' already exists, skipping creation.")
            return True
        logger.info(f"\nCreating volume '{volume_name}' in pool '{pool_name}'...")
        create_response = client.post(
            f"/api/v1/volume/{pool_name}/create/{volume_name}",
            json={
                "size_gb": 1
            }
        )
        logger.debug(f"Create response: {create_response.status_code} {create_response.json()}")
        assert create_response.status_code == 201
        volume_full_path = create_response.json()["volume_path"]
        assert volume_exists(client, pool_name, volume_name)
        logger.debug(f"Volume created at: {volume_full_path}")
        test_context["full_volume_path"] = volume_full_path
        return True
    except Exception as e:
        logger.error(f"Error during volume creation: {e}")
        raise