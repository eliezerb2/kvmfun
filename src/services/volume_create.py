import libvirt #type: ignore
import logging
import textwrap

logger: logging.Logger = logging.getLogger(__name__)

def create_volume(
    conn: libvirt.virConnect, 
    vol_name: str, 
    size_gb: int,
    pool_name: str = 'default', 
    ) -> str:
    """
    Create a new QCOW2 storage volume on a remote host using libvirt.

    This function commands the remote libvirt daemon to create a new, empty
    disk image (storage volume) within a specified storage pool.

    Args:
        conn: Active libvirt connection to the remote host.
        vol_name: The desired name for the new volume (e.g., 'my-vm-disk.qcow2').
        size_gb: The size of the new volume in gigabytes.
        pool_name: The name of the storage pool where the volume will be created (e.g., 'default').

    Returns:
        The full path of the created volume on the libvirt host.

    Raises:
        ValueError: If the storage pool is not found, is inactive, or creation fails.
        libvirt.libvirtError: For other libvirt API errors during creation.
    """
    logger.info(f"Creating volume '{vol_name}' in pool '{pool_name}' with size {size_gb}GB.")
    try:
        pool: libvirt.virStoragePool = conn.storagePoolLookupByName(pool_name)
    except libvirt.libvirtError as e:
        logger.error(f"Storage pool '{pool_name}' not found: {e}")
        raise ValueError(f"Storage pool '{pool_name}' not found.")

    if not pool.isActive():
        raise ValueError(f"Storage pool '{pool_name}' is not active.")

    # Convert GB to bytes for the XML capacity element
    capacity = size_gb * 1024 * 1024 * 1024

    # Define the correct <volume> XML for creating a new storage volume
    vol_xml = textwrap.dedent(f"""
        <volume>
            <name>{vol_name}</name>
            <capacity unit="bytes">{capacity}</capacity>
            <target>
                <format type='qcow2'/>
            </target>
        </volume>
    """)

    try:
        # Use libvirt's storageVolCreateXML to create the disk remotely
        vol: libvirt.virStorageVol = pool.createXML(vol_xml, 0)
        path: str = vol.path()
        logger.info(f"Successfully created volume '{vol.name()}' at path: {path}")
        return path
    except libvirt.libvirtError as e:
        logger.error(f"Failed to create volume '{vol_name}' in pool '{pool_name}': {e}")
        raise ValueError(f"Failed to create disk image remotely: {e}")