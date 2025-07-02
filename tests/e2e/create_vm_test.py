from src.api.vm_endpoints import logger

def create_vm_test(client, vm_name: str, full_volume_path: str) -> bool:
    """
    Test the real create_vm function.
    This function is intended to be run in an environment where the necessary
    dependencies (like a running libvirt instance) are available.
    """
    logger.debug("===================== create VM =====================")
    try:
        logger.debug(f"Checking if VM exists: {vm_name}")
        # use list_vms to check if the VM already exists
        list_response = client.get(f"/api/v1/vm/list")
        logger.debug(f"List response: {list_response.status_code} {list_response.json()}")
        assert list_response.status_code == 200
        vms = list_response.json().get('vms', [])
        if any(vm['name'] == vm_name for vm in vms):
            logger.info(f"VM '{vm_name}' already exists, skipping creation.")
            return True

        logger.info(f"\nCreating VM '{vm_name}'...")
        create_response = client.post(
            "/api/v1/vm/create",
            json={
                "vm_name": vm_name,
                "memory_mb": 1024,
                "vcpu_count": 1,
                "disk_path": full_volume_path,
                "network_name": "default"
            }
        )
        logger.debug(f"Create response: {create_response.status_code} {create_response.json()}")
        assert create_response.status_code == 201
        return True
    except Exception as e:
        logger.error(f"Error during VM creation: {e}")
        raise