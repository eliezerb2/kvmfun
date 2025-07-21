import pytest # type: ignore
import json
import logging
from tests.e2e.utils import get_volume_path
from tests.config import config


logger = logging.getLogger(__name__)

@pytest.mark.e2e
@pytest.mark.dependency(name="create_volumes")
def test_create_volumes(test_context) -> None:
    """
    Test the real create_volume function.
    This function is intended to be run in an environment where the necessary
    dependencies (like a running libvirt instance) are available.
    """
    client = test_context.get("client")
    pool_name: str = test_context.get("pool_name")
    volumes: dict = test_context.get("volumes")
    for volume_name in volumes.keys():
        path = create_volume(client, pool_name, volume_name, test_context)
        if path:
            logger.debug(f"Volume {volume_name} created at {path}")
            test_context["volumes"].update({volume_name: {"path": path}})
    logger.debug(f"Volumes created:\n{json.dumps(test_context['volumes'], indent=4)}")
    return


def create_volume(client, pool_name, volume_name, test_context) -> str | None:
    """
    Create a volume in the specified pool.
    """
    logger.debug(f"Creating volume {volume_name} in pool {pool_name}")
    try:
        volume_full_path: str | None = get_volume_path(client, pool_name, volume_name)
        if volume_full_path:
            logger.warning(f"Volume '{volume_name}' already exists, skipping creation.")
            return volume_full_path
        logger.info(f"\nCreating volume '{volume_name}' in pool '{pool_name}'...")
        create_volume_request_payload = {
            "size_gb": config.TEST_DATA_VOLUME_SIZE_GB
        }
        logger.debug(f"Create volume request payload:\n{json.dumps(create_volume_request_payload, indent=4)}")
        create_volume_response = client.post(
            f"/api/v1/volume/{pool_name}/create/{volume_name}",
            json=create_volume_request_payload
        )
        logger.debug(f"Create volume response: {create_volume_response.status_code}\n{json.dumps(create_volume_response.json(), indent=4)}")
        assert create_volume_response.status_code == 201
        volume_full_path = create_volume_response.json()["volume_path"]
        assert get_volume_path(client, pool_name, volume_name) == volume_full_path
        logger.debug(f"Volume created at: {volume_full_path}")
        return volume_full_path
    except Exception as e:
        logger.error(f"Error during volume creation: {e}")
        raise