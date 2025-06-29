import libvirt
import xml.etree.ElementTree as ET
import time
import logging
import json
from typing import Optional
from src.config import config

logger = logging.getLogger(__name__)

def get_disk_xml_for_target_dev(dom: libvirt.virDomain, target_dev: str) -> str:
    """
    Extract XML description of specific disk from VM's domain XML.
    
    Retrieves the complete XML configuration for a specific disk device
    from the virtual machine's domain configuration.
    
    Args:
        dom: libvirt Domain object for the target VM
        target_dev: Target device name to search for (e.g., 'vdb', 'vdc')
        
    Returns:
        str: Complete XML string of the disk element
        
    Raises:
        ValueError: If disk not found or not file-backed
        libvirt.libvirtError: If unable to retrieve VM configuration
        
    Note:
        Only returns XML for file-backed disks (not block devices or other types).
    """
    vm_name = dom.name()
    logger.info(f"Retrieving disk XML for device '{target_dev}' in VM '{vm_name}'")
    
    try:
        current_dom_xml = dom.XMLDesc(0)
        logger.debug(f"Retrieved VM configuration XML for '{vm_name}'")
        
        root = ET.fromstring(current_dom_xml)
        
        for disk_elem in root.findall(".//disk"):
            target_elem = disk_elem.find("target")
            if target_elem is not None and target_elem.get("dev") == target_dev:
                logger.debug(f"Found matching disk element for device '{target_dev}'")
                
                # Validate it's a file-backed disk
                source_elem = disk_elem.find("source")
                if source_elem is None or not source_elem.get("file"):
                    error_msg = f"Disk '{target_dev}' is not a file-backed disk"
                    logger.error(f"Invalid disk type for VM '{vm_name}': {error_msg}")
                    raise ValueError(error_msg)
                
                disk_xml = ET.tostring(disk_elem, encoding='unicode')
                source_file = source_elem.get("file")
                logger.info(f"Successfully retrieved disk XML for VM '{vm_name}', device '{target_dev}', source: '{source_file}'")
                logger.debug(f"Disk XML: {disk_xml}")
                return disk_xml
        
        error_msg = f"Disk with target '{target_dev}' not found"
        logger.error(f"Disk not found in VM '{vm_name}': {error_msg}")
        raise ValueError(error_msg)
        
    except ET.ParseError as e:
        logger.error(f"Failed to parse VM XML for '{vm_name}': {e}")
        raise ValueError(f"Failed to parse VM configuration: {e}")
    except Exception as e:
        logger.error(f"Unexpected error retrieving disk XML for VM '{vm_name}', device '{target_dev}': {e}")
        raise

def poll_for_disk_removal(dom: libvirt.virDomain, target_dev: str, timeout: Optional[int] = None) -> bool:
    """
    Poll VM's live XML to confirm disk removal.
    
    Continuously checks the VM's live configuration to verify that the specified
    disk device has been successfully removed from the domain.
    
    Args:
        dom: libvirt Domain object for the target VM
        target_dev: Target device name to check for removal (e.g., 'vdb')
        timeout: Maximum time to wait in seconds (uses config default if None)
        
    Returns:
        bool: True if disk successfully removed, False if timeout reached
        
    Raises:
        libvirt.libvirtError: If unable to retrieve VM configuration
        
    Note:
        Polls at intervals defined by DISK_DETACH_POLL_INTERVAL configuration.
    """
    if timeout is None:
        timeout = config.DISK_DETACH_TIMEOUT
    
    vm_name = dom.name()
    max_retries = int(timeout / config.DISK_DETACH_POLL_INTERVAL)
    
    logger.info(f"Starting disk removal polling - VM: '{vm_name}', Device: '{target_dev}', Timeout: {timeout}s, Max retries: {max_retries}")
    
    try:
        for attempt in range(max_retries):
            logger.debug(f"Polling attempt {attempt + 1}/{max_retries} for disk '{target_dev}' removal")
            
            current_dom_xml_live = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_LIVE)
            root_live = ET.fromstring(current_dom_xml_live)
            
            disk_found = False
            for disk_elem_live in root_live.findall(".//disk"):
                target_elem_live = disk_elem_live.find("target")
                if target_elem_live is not None and target_elem_live.get("dev") == target_dev:
                    disk_found = True
                    logger.debug(f"Disk '{target_dev}' still present in VM '{vm_name}' configuration")
                    break
            
            if not disk_found:
                logger.info(f"Successfully confirmed disk '{target_dev}' removed from VM '{vm_name}' (attempt {attempt + 1})")
                return True
            
            if attempt < max_retries - 1:  # Don't sleep on the last attempt
                logger.debug(f"Disk '{target_dev}' still present, waiting {config.DISK_DETACH_POLL_INTERVAL}s before retry")
                time.sleep(config.DISK_DETACH_POLL_INTERVAL)
        
        logger.error(f"Timeout waiting for disk '{target_dev}' removal from VM '{vm_name}' after {timeout}s ({max_retries} attempts)")
        return False
        
    except ET.ParseError as e:
        logger.error(f"Failed to parse VM XML during polling for VM '{vm_name}': {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during disk removal polling for VM '{vm_name}', device '{target_dev}': {e}")
        return False

def detach_disk(conn: libvirt.virConnect, vm_name: str, target_dev: str) -> bool:
    """
    Detach disk from running VM.
    
    Performs hot-detach of a disk device from a running virtual machine.
    The operation includes validation, XML retrieval, detachment, and confirmation.
    
    Args:
        conn: Active libvirt connection object
        vm_name: Name of the virtual machine
        target_dev: Target device name to detach (e.g., 'vdb', 'vdc')
        
    Returns:
        bool: True if detachment successful and confirmed, False otherwise
        
    Raises:
        ValueError: If VM not found or disk not found/invalid
        RuntimeError: If detachment operation fails
        libvirt.libvirtError: If libvirt operations fail
        
    Note:
        - Uses live and config flags for detachment
        - Confirms detachment by polling VM configuration
        - Timeout controlled by DISK_DETACH_TIMEOUT configuration
    """
    logger.info(f"Starting disk detachment - VM: '{vm_name}', Device: '{target_dev}'")
    
    try:
        # Lookup domain
        dom = conn.lookupByName(vm_name)
        if dom is None:
            error_msg = f'VM "{vm_name}" not found'
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        vm_state = dom.state()
        logger.info(f"Found VM '{vm_name}' (ID: {dom.ID()}, State: {vm_state})")
        
        # Validate VM is running (required for hot-detach)
        if vm_state[0] != libvirt.VIR_DOMAIN_RUNNING:
            error_msg = f"VM '{vm_name}' is not running (state: {vm_state[0]})"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Get disk XML before detachment
        logger.debug(f"Retrieving disk XML for device '{target_dev}'")
        disk_xml_to_detach = get_disk_xml_for_target_dev(dom, target_dev)
        logger.info(f"Successfully retrieved disk XML for detachment")
        logger.debug(f"Disk XML to detach: {disk_xml_to_detach}")
        
        # Perform detachment
        detach_flags = libvirt.VIR_DOMAIN_AFFECT_LIVE | libvirt.VIR_DOMAIN_AFFECT_CONFIG
        logger.debug(f"Executing disk detachment with flags: {detach_flags}")
        
        ret = dom.detachDeviceFlags(disk_xml_to_detach, detach_flags)
        if ret != 0:
            error_msg = f"detachDeviceFlags returned non-zero status: {ret}"
            logger.error(f"Detachment command failed for VM '{vm_name}', device '{target_dev}': {error_msg}")
            raise RuntimeError(error_msg)
        
        logger.info(f"Disk detachment command executed successfully for VM '{vm_name}', device '{target_dev}'")
        
        # Confirm detachment
        logger.debug(f"Starting detachment confirmation polling")
        if not poll_for_disk_removal(dom, target_dev):
            error_msg = f"Disk '{target_dev}' failed to detach within timeout ({config.DISK_DETACH_TIMEOUT}s)"
            logger.error(f"Detachment confirmation failed for VM '{vm_name}': {error_msg}")
            raise RuntimeError(error_msg)
        
        logger.info(f"Successfully detached and confirmed removal of disk '{target_dev}' from VM '{vm_name}'")
        return True
        
    except (ValueError, RuntimeError) as e:
        logger.error(f"Disk detachment failed for VM '{vm_name}', device '{target_dev}': {e}")
        raise
    except libvirt.libvirtError as e:
        logger.error(f"Libvirt error during disk detachment for VM '{vm_name}', device '{target_dev}': {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during disk detachment for VM '{vm_name}', device '{target_dev}': {e}")
        return False