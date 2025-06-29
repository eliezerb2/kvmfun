import libvirt
import xml.etree.ElementTree as ET
import time
import logging
import json
from typing import Optional

logger = logging.getLogger(__name__)

def get_disk_xml_for_target_dev(dom: libvirt.virDomain, target_dev: str) -> str:
    """
    Extract XML description of specific disk from VM's domain XML.
    
    Args:
        dom: libvirt Domain object
        target_dev: Target device name (e.g., 'vdb')
        
    Returns:
        XML string of the disk element
        
    Raises:
        ValueError: If disk not found or not file-backed
    """
    logger.debug(f"Getting disk XML for device '{target_dev}' in VM '{dom.name()}'")
    current_dom_xml = dom.XMLDesc(0)
    root = ET.fromstring(current_dom_xml)
    
    for disk_elem in root.findall(".//disk"):
        target_elem = disk_elem.find("target")
        if target_elem is not None and target_elem.get("dev") == target_dev:
            source_elem = disk_elem.find("source")
            if source_elem is None or not source_elem.get("file"):
                raise ValueError(f"Disk '{target_dev}' is not a file-backed disk")
            
            disk_xml = ET.tostring(disk_elem, encoding='unicode')
            logger.debug(f"Found disk XML for '{target_dev}': {disk_xml}")
            return disk_xml
    
    raise ValueError(f"Disk with target '{target_dev}' not found")

def poll_for_disk_removal(dom: libvirt.virDomain, target_dev: str, timeout: int = 60) -> bool:
    """
    Poll VM's live XML to confirm disk removal.
    
    Args:
        dom: libvirt Domain object
        target_dev: Target device name to check for removal
        timeout: Maximum time to wait in seconds
        
    Returns:
        True if disk successfully removed, False if timeout
    """
    logger.info(f"Polling for removal of disk '{target_dev}' from VM '{dom.name()}'")
    max_retries = int(timeout / 0.5)
    
    for i in range(max_retries):
        current_dom_xml_live = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_LIVE)
        root_live = ET.fromstring(current_dom_xml_live)
        
        disk_found = False
        for disk_elem_live in root_live.findall(".//disk"):
            target_elem_live = disk_elem_live.find("target")
            if target_elem_live is not None and target_elem_live.get("dev") == target_dev:
                disk_found = True
                break
        
        if not disk_found:
            logger.info(f"Confirmed disk '{target_dev}' removed from VM '{dom.name()}'")
            return True
        
        logger.debug(f"Disk '{target_dev}' still present, retrying...")
        time.sleep(0.5)
    
    logger.error(f"Timeout waiting for disk '{target_dev}' removal after {timeout}s")
    return False

def detach_disk(conn: libvirt.virConnect, vm_name: str, target_dev: str) -> bool:
    """
    Detach disk from running VM.
    
    Args:
        conn: libvirt connection object
        vm_name: Name of the virtual machine
        target_dev: Target device name to detach
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Detaching disk '{target_dev}' from VM '{vm_name}'")
    
    try:
        dom = conn.lookupByName(vm_name)
        if dom is None:
            raise ValueError(f'VM "{vm_name}" not found')
        
        # Get disk XML before detachment
        disk_xml_to_detach = get_disk_xml_for_target_dev(dom, target_dev)
        logger.debug(f"Disk XML to detach: {disk_xml_to_detach}")
        
        # Perform detachment
        detach_flags = libvirt.VIR_DOMAIN_AFFECT_LIVE | libvirt.VIR_DOMAIN_AFFECT_CONFIG
        
        ret = dom.detachDeviceFlags(disk_xml_to_detach, detach_flags)
        if ret != 0:
            logger.error(f"detachDeviceFlags returned non-zero: {ret}")
            raise RuntimeError(f"Failed to initiate detach operation")
        
        logger.info(f"Detach command sent for '{target_dev}', polling for confirmation")
        
        # Confirm detachment
        if not poll_for_disk_removal(dom, target_dev):
            logger.error(f"Disk '{target_dev}' failed to detach within timeout")
            raise RuntimeError(f"Disk '{target_dev}' failed to detach")
        
        logger.info(f"Successfully detached disk '{target_dev}' from VM '{vm_name}'")
        return True
        
    except Exception as e:
        logger.error(f"Error detaching disk '{target_dev}' from VM '{vm_name}': {e}")
        return False