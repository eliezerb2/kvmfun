import xml.etree.ElementTree as ET
import logging
from typing import List, Dict, Any
from src.modules.libvirt_utils import parse_domain_xml, NAMESPACES
import libvirt

logger = logging.getLogger(__name__)

def find_disk_by_target(root: ET.Element, target_dev: str) -> ET.Element:
    """
    Find disk element by target device name.
    
    Args:
        root: Parsed XML root element
        target_dev: Target device name to search for
        
    Returns:
        ET.Element: Disk element if found
        
    Raises:
        ValueError: If disk not found
    """
    for disk in root.findall(".//lib:disk", NAMESPACES):
        target = disk.find('lib:target', NAMESPACES)
        if target is not None and target.get('dev') == target_dev:
            return disk
    
    raise ValueError(f"Disk with target '{target_dev}' not found")

def get_used_device_names(dom: libvirt.virDomain) -> set:
    """
    Get all currently used device names in a VM.
    
    Args:
        dom: libvirt Domain object
        
    Returns:
        set: Set of used device names
    """
    vm_name = dom.name()
    logger.debug(f"Getting used device names for VM '{vm_name}'")
    
    root = parse_domain_xml(dom, live=True)
    used_devices = set()
    
    for disk in root.findall(".//lib:disk", NAMESPACES):
        target = disk.find('lib:target', NAMESPACES)
        if target is not None:
            dev = target.get('dev')
            if dev:
                used_devices.add(dev)
                logger.debug(f"Found used device: {dev}")
    
    logger.info(f"Used device names in VM '{vm_name}': {sorted(used_devices)}")
    return used_devices

def list_vm_disks(dom: libvirt.virDomain) -> List[Dict[str, Any]]:
    """
    List all file-backed disks in a VM.
    
    Args:
        dom: libvirt Domain object
        
    Returns:
        List[Dict]: List of disk information dictionaries
    """
    vm_name = dom.name()
    logger.debug(f"Listing disks for VM '{vm_name}'")
    
    root = parse_domain_xml(dom, live=True)
    disks = []
    
    for disk in root.findall(".//lib:disk[@type='file']", NAMESPACES):
        target = disk.find("lib:target", NAMESPACES)
        source = disk.find("lib:source", NAMESPACES)
        if target is not None and source is not None:
            disk_info = {
                "target_dev": target.get("dev"),
                "source_file": source.get("file"),
                "bus": target.get("bus")
            }
            disks.append(disk_info)
            logger.debug(f"Found disk: {disk_info}")
    
    logger.info(f"Listed {len(disks)} disks for VM '{vm_name}'")
    return disks