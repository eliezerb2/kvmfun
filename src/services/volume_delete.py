import libvirt # type: ignore
import logging
import xml.etree.ElementTree as ET
from src.utils.libvirt_utils import parse_domain_xml
from src.utils.exceptions import VolumeInUseError

logger: logging.Logger = logging.getLogger(__name__)

def delete_volume(conn: libvirt.virConnect, pool_name: str, volume_name: str):
    """
    Deletes a storage volume after ensuring it is not in use by any VM.

    Args:
        conn: Active libvirt connection.
        pool_name: The name of the storage pool.
        volume_name: The name of the volume to delete.

    Raises:
        VolumeInUseError: If the volume is attached to any VM.
        libvirt.libvirtError: For other libvirt-related errors.
    """
    logger.info(f"Attempting to delete volume '{volume_name}' from pool '{pool_name}'.")

    try:
        pool: libvirt.virStoragePool = conn.storagePoolLookupByName(pool_name)
        vol: libvirt.virStorageVol = pool.storageVolLookupByName(volume_name)
        vol_path: str = vol.path()
    except libvirt.libvirtError as e:
        # If pool or volume doesn't exist, it's safe to consider it "deleted".
        # This maintains idempotency for the delete operation.
        if e.get_error_code() in (libvirt.VIR_ERR_NO_STORAGE_POOL, libvirt.VIR_ERR_NO_STORAGE_VOL):
            logger.warning(f"Volume '{volume_name}' or pool '{pool_name}' not found. Assuming already deleted.")
            return
        logger.error(f"Libvirt error looking up volume '{volume_name}': {e}")
        raise # Re-raise other libvirt errors

    # Check if the volume is in use by any VM
    all_domains: list[libvirt.virDomain] = conn.listAllDomains(0)
    for dom in all_domains:
        try:
            # Check the persistent configuration, as the VM might be shut down
            # but still have the disk attached in its definition.
            root: ET.Element = parse_domain_xml(dom, live=False)
            for disk in root.findall(".//disk[@type='file']"):
                source: ET.Element | None = disk.find("source")
                if source is not None and source.get("file") == vol_path:
                    vm_name: str = dom.name()
                    error_msg: str = f"Volume '{volume_name}' in pool '{pool_name}' is in use by VM '{vm_name}' and cannot be deleted. Please detach it first."
                    logger.error(error_msg)
                    raise VolumeInUseError(error_msg)
        except libvirt.libvirtError:
            logger.warning(f"Could+ not check domain '{dom.name()}' for volume usage. Skipping.")
            continue

    logger.info(f"Volume '{volume_name}' is not in use. Proceeding with deletion from path '{vol_path}'.")
    vol.delete(flags=0)
    logger.info(f"Successfully deleted volume '{volume_name}' from pool '{pool_name}'.")