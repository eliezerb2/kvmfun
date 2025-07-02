from fastapi import APIRouter, Depends, HTTPException # type: ignore
import libvirt # type: ignore
import logging
from src.schemas.base_schemas import BaseVMRequest
from src.schemas.create_vm_request import CreateVMRequest
from src.utils.libvirt_utils import get_connection_dependency
from src.services.vm_services import create_vm, delete_vm, start_vm, stop_vm
from src.utils.config import config
from src.utils.constants import COMMON_API_RESPONSES

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix=config.VM_ROUTER_PREFIX, 
    tags=["vm"],
    responses={
        **COMMON_API_RESPONSES,
        }
    )

@router.get("/list",
            summary="List all virtual machines",
            description="List all virtual machines defined in the libvirt hypervisor.",
            )
async def list_vms_endpoint(conn: libvirt.virConnect = Depends(get_connection_dependency)):
    """
    List all virtual machines defined in the libvirt hypervisor.

    This endpoint retrieves a list of all VMs, including their names, UUIDs, states, and other properties.

    Args:
        conn (libvirt.virConnect): Connection to the libvirt hypervisor.

    Returns:
        dict: List of VMs with their properties

    Raises:
        HTTPException: 500 for server errors
    """
    try:
        vms = conn.listAllDomains(0)
        vm_list = []
        for vm in vms:
            vm_info = vm.info()
            vm_list.append({
                "name": vm.name(),
                "uuid": vm.UUIDString(),
                "state": vm_info[0],
                "max_memory": vm_info[1],
                "max_vcpus": vm_info[2]
            })
        return {"vms": vm_list}
    except libvirt.libvirtError as e:
        logger.error(f"Libvirt error while listing VMs: {repr(e)}", exc_info=True)
        raise HTTPException(status_code=500)

@router.post("/create",
             summary="Create a new virtual machine",
             description="Create a new VM with specified parameters and attach a QCOW2 disk image.",
             responses={
                 409: {"description": "VM already exists or disk already attached"},
             },
             status_code=201)
async def create_vm_endpoint(request: CreateVMRequest, conn: libvirt.virConnect = Depends(get_connection_dependency)):
    """
    Create a new virtual machine with specified parameters.
    
    This endpoint creates a new VM with the provided name, memory, vCPU count, disk image, and network.

    Args:
        request: CreateVMRequest containing:
            - vm_name: Name of the VM (alphanumeric, hyphens, underscores only)
            - memory_mb: Memory size in MB (128-65536)
            - vcpu_count: Number of virtual CPUs (1-64)
            - disk_path: Full path to the QCOW2 disk file (must end with .qcow2)
            - network_name: Name of the network to attach the VM to
            
    Returns:
        dict: Success status and VM UUID
        
    Raises:
        HTTPException: 400 for invalid input, 409 for conflicts, 500 for server errors
    """
    logger.info(f"VM creation request - Name: {request.vm_name}, Memory: {request.memory_mb}MB, VCPUs: {request.vcpu_count}, Disk: {request.disk_path}, Network: {request.network_name}")
    
    try:
        # Create the VM using the service function
        uuid = create_vm(request.vm_name, request.memory_mb, request.vcpu_count, request.disk_path, request.network_name, conn)
        
        logger.info(f"VM '{request.vm_name}' created successfully with UUID: {uuid}")
        return {"status": "success", "uuid": uuid}
    
    except ValueError as e:
        logger.error(f"Validation error during VM creation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except libvirt.libvirtError as e:
        logger.error(f"Libvirt error during VM creation: {repr(e)}", exc_info=True)
        raise HTTPException(status_code=500)
    except Exception as e:
        logger.error(f"Unexpected error during VM creation: {repr(e)}", exc_info=True)
        raise HTTPException(status_code=500)

@router.post("/start/{vm_name}",
             summary="Start a virtual machine",
             description="Start a virtual machine by its name.",
             )
async def start_vm_endpoint(vm_name: str, conn = Depends(get_connection_dependency)):
    """
    Start a virtual machine by its name.

    Args:
        vm_name (str): Name of the virtual machine to start.
        conn (libvirt.virConnect): Connection to the libvirt hypervisor.

    Returns:
        dict: Success status

    Raises:
        HTTPException: 404 for not found, 500 for server errors
    """
    try:
        if start_vm(vm_name, conn):
            return {"status": "success"}
        else:
            raise HTTPException(status_code=404)
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions (such as 404) so FastAPI can handle them properly
        raise http_exc
    except Exception as e:
        logger.error(f"Error starting VM '{vm_name}': {repr(e)}", exc_info=True)
        raise HTTPException(status_code=500)
    
@router.post("/stop/{vm_name}",
             summary="Stop a virtual machine",
             description="Stop a virtual machine by its name.",
             )
async def stop_vm_endpoint(vm_name: str, conn = Depends(get_connection_dependency)):
    """
    Stop a virtual machine by its name.

    Args:
        vm_name (str): Name of the virtual machine to stop.
        conn (libvirt.virConnect): Connection to the libvirt hypervisor.

    Returns:
        dict: Success status

    Raises:
        HTTPException: 404 for not found, 500 for server errors
    """
    try:
        if stop_vm(vm_name, conn):
            return {"status": "success"}
        else:
            raise HTTPException(status_code=404)
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions (such as 404) so FastAPI can handle them properly
        raise http_exc
    except Exception as e:
        logger.error(f"Error stopping VM '{vm_name}': {repr(e)}", exc_info=True)
        raise HTTPException(status_code=500)

@router.delete("/delete/{vm_name}",
               summary="Delete a virtual machine",
               description="Delete a virtual machine by its name.",
               )
async def delete_vm_endpoint(vm_name: str, conn = Depends(get_connection_dependency)):
    """
    Delete a virtual machine by its name.

    Args:
        vm_name (str): Name of the virtual machine to delete.
        conn (libvirt.virConnect): Connection to the libvirt hypervisor.

    Returns:
        dict: Success status

    Raises:
        HTTPException: 404 for not found, 500 for server errors
    """
    try:
        if delete_vm(vm_name, conn):
            return {"status": "success"}
        else:
            raise HTTPException(status_code=404)
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions (such as 404) so FastAPI can handle them properly
        raise http_exc
    except Exception as e:
        logger.error(f"Error deleting VM '{vm_name}': {repr(e)}", exc_info=True)
        raise HTTPException(status_code=500)