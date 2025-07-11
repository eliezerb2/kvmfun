from fastapi import APIRouter, Depends, HTTPException, status, Response # type: ignore
import libvirt # type: ignore
import logging
from src.services.disk_attach import attach_disk
from src.services.disk_detach import detach_disk
from src.utils.constants import COMMON_API_RESPONSES
from src.utils.libvirt_utils import get_connection_dependency, get_next_available_virtio_dev
from src.utils.validation_utils import validate_name
from src.utils.exceptions import DiskNotFound
from src.services.disk_utils import list_vm_disks
from src.utils.config import config
from src.schemas.attach_disk_request import AttachDiskRequest
from src.schemas.detach_disk_request import DetachDiskRequest

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix=config.DISK_ROUTER_PREFIX, 
    tags=["disk"],
    responses={
        **COMMON_API_RESPONSES,
        }
    )

@router.get("/list/{vm_name}", 
           summary="List VM disks",
           description="List all file-backed disks attached to a virtual machine",
           )
async def list_disks_endpoint(vm_name: str, conn: libvirt.virConnect = Depends(get_connection_dependency)):
    """
    List all disks attached to a virtual machine.
    
    This endpoint retrieves information about all file-backed disks currently
    attached to the specified virtual machine.
    
    Args:
        vm_name: Name of the virtual machine (alphanumeric, hyphens, underscores only)
    
    Returns:
        dict: VM name and list of attached disks with their properties
        
    Raises:
        HTTPException: 400 for invalid VM name, 404 for VM not found, 
                      500 for server errors
    """
    logger.info(f"Disk list request for VM: {vm_name}")

    # Validate VM name format
    try:
        validate_name(vm_name)
    except ValueError as e:
        logger.error(f"Invalid VM name: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    dom = conn.lookupByName(vm_name)
    logger.info(f"Successfully connected to VM '{vm_name}'")

    disks = list_vm_disks(dom)

    logger.info(f"Successfully listed {len(disks)} disks for VM '{vm_name}'")
    return {"vm_name": vm_name, "disks": disks}

@router.post("/attach",
            summary="Attach disk to VM",
            description="Attach a QCOW2 disk to a running virtual machine with automatic device assignment",
            responses={
                409: {"description": "Device already in use or disk already attached"},
            })
async def attach_disk_endpoint(request: AttachDiskRequest, conn: libvirt.virConnect = Depends(get_connection_dependency)):
    """
    Attach a QCOW2 disk to a running virtual machine.
    
    This endpoint performs hot-attach of a disk to a running VM. The disk will be
    automatically assigned to the next available virtio device if target_dev is not specified.
    
    Args:
        request: AttachDiskRequest containing:
            - vm_name: Name of the target VM (alphanumeric, hyphens, underscores only)
            - qcow2_path: Full path to the QCOW2 disk file (must end with .qcow2)
            - target_dev: Device name (optional, format: vd[a-z]+)
    
    Returns:
        dict: Success status and assigned target device
        
    Raises:
        HTTPException: 400 for invalid input, 404 for VM not found, 
                      409 for conflicts, 500 for server errors
    """
    logger.info(f"Disk attach request - VM: {request.vm_name}, Path: {request.qcow2_path}, Target: {request.target_dev}")
    
    try:
        dom = conn.lookupByName(request.vm_name)
        logger.info(f"Successfully connected to VM '{request.vm_name}'")
        
        if not request.target_dev:
            request.target_dev = get_next_available_virtio_dev(dom)
            logger.info(f"Auto-assigned target device: {request.target_dev}")
        
        success = attach_disk(dom, request.qcow2_path, request.target_dev)
        
        if success:
            logger.info(f"Successfully attached disk '{request.qcow2_path}' as '{request.target_dev}' to VM '{request.vm_name}'")
            return {"status": "success", "target_dev": request.target_dev}
        else:
            logger.error(f"Failed to attach disk '{request.qcow2_path}' to VM '{request.vm_name}'")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                              detail="Failed to attach disk")
            
    except ValueError as e:
        logger.error(f"Validation error during disk attach: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/detach", 
            summary="Detach disk from VM",
            description="Detach a disk from a running virtual machine by target device name",
            )
async def detach_disk_endpoint(request: DetachDiskRequest, conn: libvirt.virConnect = Depends(get_connection_dependency)):
    """
    Detach a disk from a running virtual machine.
    
    This endpoint performs hot-detach of a disk from a running VM by specifying
    the target device name.
    
    Args:
        request: DetachDiskRequest containing:
            - vm_name: Name of the target VM (alphanumeric, hyphens, underscores only)
            - target_dev: Device name to detach (format: vd[a-z]+)
    
    Returns:
        dict: Success status
        
    Raises:
        HTTPException: 400 for invalid input, 404 for VM/disk not found, 
                      500 for server errors
    """
    logger.info(f"Disk detach request - VM: {request.vm_name}, Target: {request.target_dev}")
    
    try:
        success = detach_disk(conn, request.vm_name, request.target_dev)
        
        if success:
            logger.info(f"Successfully detached disk '{request.target_dev}' from VM '{request.vm_name}'")
            return {"status": "success"}
        else:
            logger.error(f"Failed to detach disk '{request.target_dev}' from VM '{request.vm_name}'")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                              detail="Failed to detach disk")
            
    except DiskNotFound as e:
        logger.error(f"Disk not found during detach: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e: # Catches other validation errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))