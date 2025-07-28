import os
from libvirt import libvirtError # type: ignore
import pytest #type: ignore
from contextlib import contextmanager
import warnings
from src.api.disk_endpoints import logger
from tests.e2e.delete_volumes import test_delete_volumes
from tests.e2e.delete_vm import test_delete_vm
from tests.config import config

volumes: dict = {
    config.TEST_OS_VOLUME_NAME: {
        "path": "",
        "device": ""
    },
    config.TEST_DATA_VOLUME_NAME: {
        "path": "",
        "device": ""
    }
}


@contextmanager
def silent_operations():
    """Context manager to silently ignore assertion errors and warnings"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            yield
        except (AssertionError, libvirtError) as e:
            logger.debug(f"Suppressed error during setup/teardown: {str(e)}")
        except Exception as e:
            logger.warning(f"Unexpected error suppressed: {str(e)}")

def system_cleanup(client):
    """Cleanup function to run before and after all tests"""
    logger.info("Running system cleanup...")
    test_delete_vm(client, config.TEST_VM_NAME)
    test_delete_volumes(client, config.LIBVIRT_STORAGE_POOL, volumes)
        
@pytest.fixture(scope="session", autouse=True)
def test_context(client):
    with silent_operations():
        if config.TEST_CLEANUP_ON_START:
            system_cleanup(client)
        else:
            logger.info("Skipping system cleanup...")
    yield {
        "client": client, 
        "pool_name": config.LIBVIRT_STORAGE_POOL,
        "volumes": volumes,
        "vm_name": config.TEST_VM_NAME
        }
    with silent_operations():
        if config.TEST_CLEANUP_ON_END:
            system_cleanup(client)
        else:
            logger.info("Skipping system cleanup...")            