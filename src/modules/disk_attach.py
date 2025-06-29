import libvirt
import xml.etree.ElementTree as ET
import re
import os
import subprocess
import logging
import time
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

QCOW2_DEFAULT_SIZE = "1G"
LIBVIRT_DOMAIN_NAMESPACE = "http://libvirt.org/schemas/domain/1.0"
NAMESPACES = {'lib': LIBVIRT_DOMAIN_NAMESPACE}
VIRTIO_DISK_PREFIX = "vd"

def _letters_to_int(s: str) -> int:
    """
    Convert letter sequence to 0-indexed integer.
    
    Args:
        s: Letter sequence (e.g., 'a', 'b', 'aa')
        
    Returns:
        0-indexed integer representation
    """
    res = 0
    for char in s:
        res = res * 26 + (ord(char) - ord('a') + 1)
    return res - 1

def _int_to_letters(n: int) -> str:
    """
    Convert 0-indexed integer to letter sequence.
    
    Args:
        n: 0-indexed integer
        
    Returns:
        Corresponding letter sequence (e.g., 0->'a', 26->'aa')
    """
    res = ""
    while True:
        res = chr(ord('a') + (n % 26)) + res
        n //= 26
        if n == 0:
            break
        n -= 1
    return res

def get_libvirt_domain(vm_name: str) -> Tuple[libvirt.virConnect, libvirt.virDomain]:
    """
    Establish libvirt connection and lookup domain.
    
    Args:
        vm_name: Name of the virtual machine
        
    Returns:
        Tuple of (connection, domain) objects
        
    Raises:
        RuntimeError: If connection fails or domain not found
    """
    logger.info(f"Connecting to libvirt for VM '{vm_name}'")
    conn = libvirt.open('qemu:///system')
    if conn is None:
        raise RuntimeError('Failed to open connection to qemu:///system')
    
    try:
        dom = conn.lookupByName(vm_name)
        logger.info(f"Successfully found domain '{vm_name}'")
        return conn, dom
    except libvirt.libvirtError as e:
        conn.close()
        logger.error(f"Failed to find domain '{vm_name}': {e}")
        raise

def get_next_available_virtio_dev(dom: libvirt.virDomain) -> str:
    """
    Find next available VirtIO device name.
    
    Args:
        dom: libvirt Domain object
        
    Returns:
        Next available device name (e.g., 'vda', 'vdb')
        
    Raises:
        RuntimeError: If no available device names found
    """
    logger.debug(f"Finding next available VirtIO device for VM '{dom.name()}'")
    xml_desc = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_LIVE)
    root = ET.fromstring(xml_desc)
    
    disk_elements = root.findall(".//lib:disk", NAMESPACES)
    used_all_dev_names = set()
    
    for disk in disk_elements:
        target_element = disk.find('lib:target', NAMESPACES)
        if target_element is not None:
            dev = target_element.get('dev')
            if dev:
                used_all_dev_names.add(dev)
    
    logger.debug(f"Currently used device names: {used_all_dev_names}")
    
    for i in range(0, 702):
        current_suffix = _int_to_letters(i)
        proposed_dev_name = f"{VIRTIO_DISK_PREFIX}{current_suffix}"
        
        if proposed_dev_name not in used_all_dev_names:
            logger.info(f"Next available device: {proposed_dev_name}")
            return proposed_dev_name
    
    raise RuntimeError("No available VirtIO device suffixes")

def attach_qcow2_disk(dom: libvirt.virDomain, qcow2_path: str, target_dev: str) -> bool:
    """
    Attach QCOW2 disk to running VM.
    
    Args:
        dom: libvirt Domain object
        qcow2_path: Path to QCOW2 disk image
        target_dev: Target device name (e.g., 'vdb')
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Attaching disk '{qcow2_path}' as '{target_dev}' to VM '{dom.name()}'")
    
    try:
        # Check if disk already attached
        xml_desc = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_LIVE)
        root = ET.fromstring(xml_desc)
        
        for disk in root.findall(".//lib:disk", NAMESPACES):
            target = disk.find('lib:target', NAMESPACES)
            source = disk.find('lib:source', NAMESPACES)
            if (target is not None and target.get('dev') == target_dev and
                source is not None and source.get('file') == qcow2_path):
                logger.warning(f"Disk already attached as {target_dev}")
                return True
        
        # Create disk XML
        ET.register_namespace('', LIBVIRT_DOMAIN_NAMESPACE)
        disk_element = ET.Element('disk', type='file', device='disk')
        ET.SubElement(disk_element, 'driver', name='qemu', type='qcow2', cache='none')
        ET.SubElement(disk_element, 'source', file=qcow2_path)
        ET.SubElement(disk_element, 'target', dev=target_dev, bus='virtio')
        
        disk_xml = ET.tostring(disk_element, encoding='unicode')
        logger.debug(f"Generated disk XML: {disk_xml}")
        
        flags = (libvirt.VIR_DOMAIN_ATTACH_DEVICE_LIVE | 
                libvirt.VIR_DOMAIN_ATTACH_DEVICE_PERSIST | 
                libvirt.VIR_DOMAIN_ATTACH_DEVICE_CONFIG)
        
        dom.attachDeviceFlags(disk_xml, flags)
        logger.info(f"Disk attachment command sent for '{target_dev}'")
        
        # Confirm attachment
        for i in range(5):
            current_xml_desc = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_LIVE)
            current_root = ET.fromstring(current_xml_desc)
            
            for disk in current_root.findall(".//lib:disk", NAMESPACES):
                target = disk.find('lib:target', NAMESPACES)
                source = disk.find('lib:source', NAMESPACES)
                if (target is not None and target.get('dev') == target_dev and
                    source is not None and source.get('file') == qcow2_path):
                    logger.info(f"Successfully confirmed disk attachment: {target_dev}")
                    return True
            time.sleep(0.5)
        
        logger.error(f"Failed to confirm disk attachment for {target_dev}")
        raise RuntimeError(f"Failed to confirm disk attachment")
        
    except Exception as e:
        logger.error(f"Error attaching disk '{qcow2_path}' as '{target_dev}': {e}")
        return False