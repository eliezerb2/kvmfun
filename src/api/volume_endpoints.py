from fastapi import APIRouter, Depends, HTTPException, status, Response # type: ignore
import libvirt # type: ignore
import logging
from src.utils.exceptions import VolumeInUseError
from src.services.volume_create import create_volume
from src.services.volume_delete import delete_volume
from src.services.volume_list import list_volumes
from src.utils.config import config
from src.schemas.create_volume_request import CreateVolumeRequest  # Adjust the import path as needed
from src.utils.constants import COMMON_API_RESPONSES
from src.utils.libvirt_utils import get_connection_dependency  # Make sure this import path is correct

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix=config.VOLUME_ROUTER_PREFIX + "/{pool_name}",
    tags=["volume"],
    responses={
        **COMMON_API_RESPONSES,
    }
)

@router.post("/create/{volume_name}",
            summary="Create a new disk volume",
            description="Create a new QCOW2 disk volume in a specified storage pool on the libvirt host.",
            status_code=status.HTTP_201_CREATED)
async def create_volume_endpoint(
    pool_name: str, 
    volume_name: str,
    request: CreateVolumeRequest, 
    conn: libvirt.virConnect = Depends(get_connection_dependency)):
    """
    Create a new disk (storage volume) on the libvirt host.

    Args:
        request: CreateVolumeRequest containing pool name, volume name, and size.

    Returns:
        dict: Success status and the full path of the created volume.
    """
    logger.info(f"Disk volume creation request - Pool: {pool_name}, Name: {volume_name}, Size: {request.size_gb}GB")
    try:
        # The service layer returns the full, correct path. Do not modify it.
        volume_path = create_volume(conn, volume_name, int(request.size_gb), pool_name)
        return {"status": "success", "volume_path": volume_path}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except libvirt.libvirtError as e:
        # Check for specific libvirt error for existing volume
        if e.get_error_code() == libvirt.VIR_ERR_STORAGE_VOL_EXIST:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Storage volume '{volume_name}' already exists in pool '{pool_name}'."
            )
        logger.error(f"Libvirt error during volume creation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@router.delete("/delete/{volume_name}",
             summary="Delete a disk volume",
             description="Delete a disk volume from a storage pool on the libvirt host.",
             status_code=status.HTTP_204_NO_CONTENT,
             responses={
                409: {"description": "Volume is in use by a VM and cannot be deleted"},
             })
async def delete_volume_endpoint(
    volume_name: str, 
    pool_name: str, 
    conn: libvirt.virConnect = Depends(get_connection_dependency)):
    """
    Delete a disk (storage volume) from the libvirt host. This is idempotent.
    """
    logger.info(f"Disk volume deletion request - Pool: {pool_name}, Name: {volume_name}")
    try:
        delete_volume(conn, pool_name, volume_name)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except VolumeInUseError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/list",
            summary="List all disk volumes",
            description="List all disk volumes in a storage pool on the libvirt host.",
            )
async def list_volumes_endpoint(pool_name: str, conn: libvirt.virConnect = Depends(get_connection_dependency)):
    """
    List all disk volumes in a specified storage pool.

    Args:
        pool_name: Name of the storage pool to list volumes from.

    Returns:
        dict: A list of volumes in the specified pool.
    """
    logger.info(f"Disk volume list request - Pool: {pool_name}")
    try:
        volumes = list_volumes(conn, pool_name)
        return {"volumes": volumes}
    except libvirt.libvirtError as e:
        logger.error(f"Libvirt error during volume list: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
