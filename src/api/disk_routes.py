from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
import libvirt
import logging
from src.modules.disk_attach import get_next_available_virtio_dev, attach_disk
from src.modules.disk_detach import detach_disk
from src.modules.libvirt_utils import get_connection_dependency
from src.modules.validation_utils import validate_vm_name, validate_target_device, validate_qcow2_path
from src.modules.exceptions import DiskNotFound
from src.modules.disk_utils import list_vm_disks
from src.config import config

logger = logging.getLogger(__name__)
router = APIRouter(prefix=config.DISK_ROUTER_PREFIX, tags=["disk"])

class AttachDiskRequest(BaseModel):
    """Request model for disk attachment."""
    vm_name: str = Field(..., description="Name of the virtual machine", min_length=1, max_length=255)
    qcow2_path: str = Field(..., description="Path to the QCOW2 disk image", min_length=1)
    target_dev: str = Field(None, description="Target device name (auto-assigned if not provided)")
    
    @validator('vm_name')
    def validate_vm_name_field(cls, v):
        return validate_vm_name(v)
    
    @validator('qcow2_path')
    def validate_qcow2_path_field(cls, v):
        if not v.endswith('.qcow2'):
            raise ValueError('Disk path must end with .qcow2')
        return v
    
    @validator('target_dev')
    def validate_target_dev_field(cls, v):
        return validate_target_device(v)

class DetachDiskRequest(BaseModel):
    """Request model for disk detachment."""
    vm_name: str = Field(..., description="Name of the virtual machine", min_length=1, max_length=255)
    target_dev: str = Field(..., description="Target device name to detach", min_length=1)
    
    @validator('vm_name')
    def validate_vm_name_field(cls, v):
        return validate_vm_name(v)
    
    @validator('target_dev')
    def validate_target_dev_field(cls, v):
        return validate_target_device(v)

@router.post("/attach", 
            summary="Attach disk to VM",
            description="Attach a QCOW2 disk to a running virtual machine with automatic device assignment",
            responses={
                200: {"description": "Disk successfully attached"},
                400: {"description": "Invalid request parameters"},
                404: {"description": "VM not found"},
                409: {"description": "Device already in use or disk already attached"},
                500: {"description": "Internal server error"}
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
    
    # Validate request parameters
    try:
        validate_qcow2_path(request.qcow2_path)
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
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
    except Exception as e:
        logger.error(f"Unexpected error during disk attach: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/detach", 
            summary="Detach disk from VM",
            description="Detach a disk from a running virtual machine by target device name",
            responses={
                200: {"description": "Disk successfully detached"},
                400: {"description": "Invalid request parameters"},
                404: {"description": "VM or disk not found"},
                500: {"description": "Internal server error"}
            })
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
    except Exception as e:
        logger.error(f"Unexpected error during disk detach: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/list/{vm_name}", 
           summary="List VM disks",
           description="List all file-backed disks attached to a virtual machine",
           responses={
               200: {"description": "List of disks successfully retrieved"},
               400: {"description": "Invalid VM name format"},
               404: {"description": "VM not found"},
               500: {"description": "Internal server error"}
           })
async def list_disks(vm_name: str, conn: libvirt.virConnect = Depends(get_connection_dependency)):
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
        validate_vm_name(vm_name)
    except ValueError as e:
        logger.error(f"Invalid VM name: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    try:
        dom = conn.lookupByName(vm_name)
        logger.info(f"Successfully connected to VM '{vm_name}'")
        
        disks = list_vm_disks(dom)
        
        logger.info(f"Successfully listed {len(disks)} disks for VM '{vm_name}'")
        return {"vm_name": vm_name, "disks": disks}
        
    except Exception as e:
        logger.error(f"Unexpected error during disk list for VM '{vm_name}': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))