from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel, Field, field_validator
import libvirt
import logging
from src.services.disk_attach import get_next_available_virtio_dev, attach_disk
from src.services.disk_detach import detach_disk
from src.services.disk_create import create_disk_volume
from src.utils.constants import COMMON_API_RESPONSES
from src.utils.libvirt_utils import get_connection_dependency
from src.utils.validation_utils import validate_target_device, validate_qcow2_path
from src.utils.exceptions import DiskNotFound
from src.services.disk_utils import list_vm_disks
from src.utils.config import config
from src.schemas.attach_disk_request import AttachDiskRequest
from src.schemas.base_schemas import BaseDiskRequest
from src.schemas.create_volume_request import CreateVolumeRequest

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix=config.DISK_ROUTER_PREFIX, 
    tags=["disk"],
    responses={
        **COMMON_API_RESPONSES,
        }
    )

@router.post("/create",
            summary="Create a new disk volume",
            description="Create a new QCOW2 disk volume in a specified storage pool on the libvirt host.",
            status_code=status.HTTP_201_CREATED)
async def create_disk_volume_endpoint(request: CreateVolumeRequest, conn: libvirt.virConnect = Depends(get_connection_dependency)):
    """
    Create a new disk (storage volume) on the libvirt host.

    Args:
        request: CreateVolumeRequest containing pool name, volume name, and size.

    Returns:
        dict: Success status and the full path of the created volume.
    """
    logger.info(f"Disk volume creation request - Pool: {request.pool_name}, Name: {request.volume_name}, Size: {request.size_gb}GB")
    try:
        volume_path = create_disk_volume(conn, request.volume_name, int(request.size_gb), request.pool_name)
        return {"status": "success", "volume_path": volume_path}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except libvirt.libvirtError as e:
        # Check for specific libvirt error for existing volume
        if e.get_error_code() == libvirt.VIR_ERR_STORAGE_VOL_EXIST:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Storage volume '{request.volume_name}' already exists in pool '{request.pool_name}'.")
        logger.error(f"Libvirt error during volume creation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal libvirt error.")

@router.delete("/delete",
             summary="Delete a disk volume",
             description="Delete a disk volume from a storage pool on the libvirt host.",
             status_code=status.HTTP_204_NO_CONTENT)
async def delete_disk_volume_endpoint(pool_name: str, volume_name: str, conn: libvirt.virConnect = Depends(get_connection_dependency)):
    """
    Delete a disk (storage volume) from the libvirt host. This is idempotent.
    """
    from src.services.volume_utils import delete_volume
    logger.info(f"Disk volume deletion request - Pool: {pool_name}, Name: {volume_name}")
    try:
        delete_volume(conn, pool_name, volume_name)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

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
async def detach_disk_endpoint(request: BaseDiskRequest, conn: libvirt.virConnect = Depends(get_connection_dependency)):
    """
    Detach a disk from a running virtual machine.
    
    This endpoint performs hot-detach of a disk from a running VM by specifying
    the target device name.
    
    Args:
        request: BaseDiskRequest containing:
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