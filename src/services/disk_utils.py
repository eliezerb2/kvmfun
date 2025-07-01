import xml.etree.ElementTree as ET
import logging
from typing import List, Dict, Any
from src.utils.libvirt_utils import parse_domain_xml, NAMESPACES, LIBVIRT_DOMAIN_NAMESPACE
import libvirt

logger = logging.getLogger(__name__)

def _create_disk_xml(qcow2_path: str, target_dev: str = None) -> str:
    """
    Create disk XML for attachment.

    Args:
        qcow2_path (str): Path to the QCOW2 disk image file.
        target_dev (str, optional): Target device name (e.g., 'vdb').
            If not provided, the disk will be attached as the next available device.

    Returns:
        str: Disk XML as a string.

    Raises:
        ValueError: If disk conflicts are detected or creation fails.
    """
    logger.debug(f"Creating disk XML for '{qcow2_path}' as '{target_dev}'")
    ET.register_namespace('', LIBVIRT_DOMAIN_NAMESPACE)
    disk_element = ET.Element('disk', type='file', device='disk')
    ET.SubElement(disk_element, 'driver', name='qemu', type='qcow2', cache='none')
    ET.SubElement(disk_element, 'source', file=qcow2_path)
    target_kwargs = {'bus': 'virtio'}
    if target_dev is not None:
        target_kwargs['dev'] = target_dev
    ET.SubElement(disk_element, 'target', **target_kwargs)
    disk_xml = ET.tostring(disk_element, encoding='unicode')
    logger.debug(f"Generated disk XML: {disk_xml}")
    return disk_xml

def _check_disk_conflicts(dom: libvirt.virDomain, qcow2_path: str, target_dev: str) -> bool:
    """Check if disk is already attached or conflicts exist."""
    vm_name = dom.name()
    logger.debug(f"Checking disk conflicts for VM '{vm_name}', device '{target_dev}'")
    root = parse_domain_xml(dom, live=True)
    
    for disk in root.findall(".//lib:disk", NAMESPACES):
        target = disk.find('lib:target', NAMESPACES)
        source = disk.find('lib:source', NAMESPACES)
        
        if target is not None and target.get('dev') == target_dev:
            existing_source = source.get('file') if source is not None else 'unknown'
            if existing_source == qcow2_path:
                logger.warning(f"Disk '{qcow2_path}' already attached as '{target_dev}' to VM '{vm_name}'")
                return True
            error_msg = f"Target device '{target_dev}' already in use by '{existing_source}'"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if source is not None and source.get('file') == qcow2_path:
            existing_target = target.get('dev') if target is not None else 'unknown'
            error_msg = f"Disk '{qcow2_path}' already attached as '{existing_target}'"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    logger.debug(f"No disk conflicts found for VM '{vm_name}'")
    return False

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