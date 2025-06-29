import libvirt
import xml.etree.ElementTree as ET
import time
import logging
import json # For QEMU Guest Agent JSON output

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Helper Functions ---

def _get_disk_xml_for_target_dev(dom: libvirt.virDomain, target_dev: str) -> str:
    """
    Extracts the XML description of a specific disk from a VM's domain XML.
    """
    current_dom_xml = dom.XMLDesc(0) # Get persistent XML
    root = ET.fromstring(current_dom_xml)
    
    disk_to_detach_xml = None
    for disk_elem in root.findall(".//disk"):
        target_elem = disk_elem.find("target")
        if target_elem is not None and target_elem.get("dev") == target_dev:
            source_elem = disk_elem.find("source")
            if source_elem is None or not source_elem.get("file"):
                raise ValueError(f"Disk '{target_dev}' is not a file-backed disk. Cannot proceed.")
            
            disk_to_detach_xml = ET.tostring(disk_elem, encoding='unicode')
            break
    
    if disk_to_detach_xml is None:
        raise ValueError(f"Disk with target '{target_dev}' not found in VM '{dom.name()}' XML.")
    
    return disk_to_detach_xml

def _poll_for_disk_removal(dom: libvirt.virDomain, target_dev: str, timeout: int = 60, initial_delay: float = 0.5):
    """
    Polls the VM's live XML to confirm a disk has been removed.
    """
    max_retries = int(timeout / initial_delay) # Roughly, adjusts for max timeout
    retry_delay_base = initial_delay
    
    logger.info(f"Polling for removal of disk '{target_dev}' from VM '{dom.name()}'...")
    
    for i in range(max_retries):
        current_dom_xml_live = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_LIVE) # Get live XML
        root_live = ET.fromstring(current_dom_xml_live)
        
        disk_found = False
        for disk_elem_live in root_live.findall(".//disk"):
            target_elem_live = disk_elem_live.find("target")
            if target_elem_live is not None and target_elem_live.get("dev") == target_dev:
                disk_found = True
                break
        
        if not disk_found:
            logger.info(f"Confirmed: Disk '{target_dev}' successfully removed from VM '{dom.name()}' live configuration.")
            return True
        else:
            delay = retry_delay_base * (1.5 ** i) # Exponential backoff
            if delay > 5: delay = 5 # Cap max delay
            logger.debug(f"Disk '{target_dev}' still present in live config. Retrying in {delay:.2f} seconds...")
            time.sleep(delay)
            
    logger.error(f"Timed out waiting for disk '{target_dev}' to be removed from VM '{dom.name()}' live configuration after {timeout} seconds.")
    return False

def confirm_guest_disk_unmounted(dom: libvirt.virDomain, target_dev: str, vm_disk_path: str):
    """
    Attempts to confirm that the disk is unmounted in the guest OS using QEMU Guest Agent.
    NOTE: Requires QEMU Guest Agent to be installed and running in the VM.
    This is a *best effort* check. If QGA isn't working or the disk is raw, it might not confirm.

    Args:
        dom: The libvirt domain object.
        target_dev: The libvirt target device name (e.g., 'vdb').
        vm_disk_path: A path or identifier for the disk within the guest OS (e.g., '/dev/vdb1' or a mount point).
                      This is highly guest-OS dependent and may need refinement.
    """
    logger.info(f"Attempting to confirm disk '{target_dev}' (guest path: {vm_disk_path}) is unmounted in guest via QGA...")
    try:
        # Example QGA command to list mounted filesystems
        # The output format can vary, and interpreting it reliably is complex.
        # This is a conceptual example. A robust solution needs careful parsing.
        qga_command = {
            "execute": "guest-get-fsinfo"
        }
        
        # QemuAgentCommand returns a string, which is JSON.
        result_json_str = dom.qemuAgentCommand(json.dumps(qga_command), 0, 0)
        result = json.loads(result_json_str)

        if "return" in result:
            mounted_filesystems = result["return"]
            for fs_info in mounted_filesystems:
                if fs_info.get("mountpoint") == vm_disk_path or fs_info.get("name") == vm_disk_path:
                    logger.warning(f"Guest: Disk '{vm_disk_path}' appears to still be mounted at {fs_info.get('mountpoint')}.")
                    raise Exception(f"Disk '{vm_disk_path}' is still mounted in guest. Aborting detach.")
            logger.info(f"Guest: Disk '{vm_disk_path}' does not appear to be actively mounted (based on QGA fsinfo).")
        else:
            logger.warning("QEMU Guest Agent did not return filesystem info or command failed. Cannot confirm unmounted status reliably.")
            # Decide if you want to proceed without confirmation or raise an error
            # raise Exception("Cannot confirm disk unmounted state via QGA.")

    except libvirt.libvirtError as e:
        if "agent is not running" in str(e):
            logger.warning(f"QEMU Guest Agent not running in VM '{dom.name()}'. Cannot confirm disk unmounted status via QGA. Proceeding with caution.")
        else:
            logger.error(f"Error communicating with QEMU Guest Agent for VM '{dom.name()}': {e}. Cannot confirm disk unmounted status reliably.", exc_info=True)
            # Decide if you want to proceed without confirmation or raise an error
            # raise Exception("QGA communication error. Cannot confirm disk unmounted state.")
    except json.JSONDecodeError:
        logger.error("QEMU Guest Agent returned invalid JSON. Cannot confirm disk unmounted status reliably.")
    except Exception as e:
        logger.error(f"Unexpected error during QGA check: {e}", exc_info=True)
        # raise Exception("QGA check failed unexpectedly.")

def detach_disk(conn: libvirt.virConnect, vm_name: str, target_dev: str):
    """
    Detaches a disk from a running VM, persisting the change to config.
    Includes validation and polling.
    """
    dom = conn.lookupByName(vm_name)
    if dom is None:
        raise ValueError(f'VM "{vm_name}" not found.')
    
    # 1. Get the disk XML
    disk_xml_to_detach = _get_disk_xml_for_target_dev(dom, target_dev)
    logger.info(f"XML for disk '{target_dev}' obtained:\n{disk_xml_to_detach}")

    # 2. Perform the detach operation
    detach_flags = libvirt.VIR_DOMAIN_AFFECT_LIVE | libvirt.VIR_DOMAIN_AFFECT_CONFIG
    logger.info(f"Attempting to detach disk '{target_dev}' from '{vm_name}' (live and config)...")
    
    ret = dom.detachDeviceFlags(disk_xml_to_detach, detach_flags)
    if ret != 0:
        logger.error(f"dom.detachDeviceFlags() for disk '{target_dev}' returned non-zero ({ret}). Check libvirt logs for details.")
        raise RuntimeError(f"Failed to initiate detach operation for disk '{target_dev}'.")
    
    # 3. Poll for confirmation of disk removal
    if not _poll_for_disk_removal(dom, target_dev):
        logger.error(f"Disk '{target_dev}' did not detach successfully after polling. Check libvirt logs (e.g., /var/log/libvirt/qemu/{vm_name}.log or journalctl -u libvirtd).")
        raise RuntimeError(f"Disk '{target_dev}' failed to detach fully from '{vm_name}'.")

    logger.info(f"Disk '{target_dev}' successfully detached from '{vm_name}'.")

def update_snapshot_metadata(
    conn: libvirt.virConnect,
    vm_name: str,
    snapshot_name: str,
    custom_namespace_prefix: str,
    custom_namespace_uri: str,
    custom_tag_local_name: str,
    new_custom_tag_value: str
):
    """
    Updates a custom flag in the specified external snapshot's metadata XML.
    """
    dom = conn.lookupByName(vm_name)
    if dom is None:
        raise ValueError(f'VM "{vm_name}" not found.')

    snap = dom.snapshotLookupByName(snapshot_name)
    if snap is None:
        raise ValueError(f'Snapshot "{snapshot_name}" not found for VM "{vm_name}".')
    logger.info(f"Found snapshot: {snap.getName()}")

    current_snap_xml = snap.getXMLDesc(0)
    snap_root = ET.fromstring(current_snap_xml)

    # Register the namespace for correct serialization (especially if new tags are added)
    ET.register_namespace(custom_namespace_prefix, custom_namespace_uri)

    custom_tag_fqn = f"{{{custom_namespace_uri}}}{custom_tag_local_name}"
    custom_elem = snap_root.find(custom_tag_fqn)

    if custom_elem is None:
        logger.info(f"Custom tag '{custom_tag_local_name}' not found. Creating it.")
        custom_elem = ET.SubElement(snap_root, custom_tag_fqn)
    else:
        logger.info(f"Custom tag '{custom_tag_local_name}' found. Updating its value.")

    custom_elem.text = new_custom_tag_value

    modified_snap_xml = ET.tostring(snap_root, encoding='unicode', xml_declaration=True)
    
    logger.debug("Modified Snapshot XML (for redefinition):\n%s", modified_snap_xml)

    # Validate the modified XML by attempting to parse it
    try:
        ET.fromstring(modified_snap_xml)
        logger.info("Modified snapshot XML is well-formed.")
    except ET.ParseError as e:
        logger.error(f"Generated snapshot XML is malformed! Error: {e}", exc_info=True)
        raise ValueError("Invalid XML generated for snapshot metadata.")

    # Redefine the snapshot's metadata
    logger.info(f"Redefining metadata for snapshot '{snapshot_name}'...")
    dom.snapshotCreateXML(modified_snap_xml, libvirt.VIR_DOMAIN_SNAPSHOT_CREATE_REDEFINE)
    logger.info(f"Successfully updated metadata for snapshot '{snapshot_name}'.")

# --- Main Orchestration Logic ---
def main_operation(
    vm_name: str,
    target_dev: str,
    snapshot_name: str,
    custom_namespace_prefix: str,
    custom_namespace_uri: str,
    custom_tag_local_name: str,
    new_custom_tag_value: str,
    guest_disk_path_for_qga: str = None # Optional: e.g., '/mnt/data' or '/dev/vdb1'
):
    """
    Orchestrates the entire process: confirming guest unmount (optional),
    detaching the disk, and updating snapshot metadata.
    """
    conn = None
    try:
        conn = libvirt.open('qemu:///system')
        if conn is None:
            raise Exception('Failed to open connection to qemu:///system')
        
        logger.info(f"Starting operation for VM: {vm_name}, Disk: {target_dev}, Snapshot: {snapshot_name}")

        # Optional: Confirm disk unmounted in guest via QGA
        if guest_disk_path_for_qga:
            confirm_guest_disk_unmounted(conn.lookupByName(vm_name), target_dev, guest_disk_path_for_qga)
        else:
            logger.warning("No guest_disk_path_for_qga provided. Skipping QEMU Guest Agent unmount check. Ensure disk is unmounted manually!")
            # Potentially add a manual confirmation prompt here in interactive scripts

        # Step 1: Detach the disk
        detach_disk(conn, vm_name, target_dev)

        # Step 2: Update the snapshot metadata
        update_snapshot_metadata(
            conn,
            vm_name,
            snapshot_name,
            custom_namespace_prefix,
            custom_namespace_uri,
            custom_tag_local_name,
            new_custom_tag_value
        )
        
        logger.info("All operations completed successfully.")

    except (libvirt.libvirtError, ValueError, RuntimeError) as e:
        logger.critical(f"Operation failed: {e}")
        # In a real system, you might add more sophisticated rollback or alert logic here
    except Exception as e:
        logger.critical(f"An unexpected error occurred during the main operation: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logger.info("Libvirt connection closed.")


# --- Configuration ---
VM_NAME = "Fedora39" # <<--- REPLACE with your VM name
TARGET_DEVICE_NAME = "vdb"  # <<--- REPLACE with the target dev of the disk to detach
SNAPSHOT_NAME = "f39_data_snap_archived_20250629" # <<--- REPLACE with the libvirt name of your external snapshot

# Your custom namespace details
CUSTOM_NAMESPACE_PREFIX = "mycustom"
CUSTOM_NAMESPACE_URI = "http://yourcompany.com/libvirt/snapshot/customdata/1.0"
CUSTOM_TAG_LOCAL_NAME = "archive_status" # The tag name WITHOUT the prefix
NEW_CUSTOM_TAG_VALUE = "detached_for_long_term_archive_20250629"

# Optional: Path to the disk/mount point in the guest OS for QGA check
# IMPORTANT: This needs to be accurate for your guest!
GUEST_DISK_PATH_FOR_QGA = "/mnt/mydata" # <<--- REPLACE if you use QGA and have a specific path


# --- Execute ---
if __name__ == "__main__":
    main_operation(
        VM_NAME,
        TARGET_DEVICE_NAME,
        SNAPSHOT_NAME,
        CUSTOM_NAMESPACE_PREFIX,
        CUSTOM_NAMESPACE_URI,
        CUSTOM_TAG_LOCAL_NAME,
        NEW_CUSTOM_TAG_VALUE,
        guest_disk_path_for_qga=GUEST_DISK_PATH_FOR_QGA
    )
