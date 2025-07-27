from typing import List, Dict, Any
import libvirt # type: ignore
import logging

logger: logging.Logger = logging.getLogger(__name__)

def list_volumes(conn: libvirt.virConnect, pool_name: str) -> List[Dict[str, Any]]:
    """
    List all volumes in a given storage pool.
    """
    volumes: List[Dict[str, Any]] = []
    try:
        pool: libvirt.virStoragePool = conn.storagePoolLookupByName(pool_name)
        pool.refresh()
        for vol_name in pool.listVolumes(): # Renamed 'vol' to 'vol_name' for clarity
            # Correctly get the volume object from the pool
            vol_obj: libvirt.virStorageVol = pool.storageVolLookupByName(vol_name)
            if vol_obj: # Ensure the volume object was found
                volumes.append({"name": vol_name, "path": vol_obj.path()})
            else:
                logger.warning(f"Volume '{vol_name}' not found in pool '{pool_name}' after listing.")
    except libvirt.libvirtError as e:
        logger.error(f"Error listing volumes: {e}")
    return volumes