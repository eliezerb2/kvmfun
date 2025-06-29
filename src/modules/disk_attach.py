import libvirt
import xml.etree.ElementTree as ET
import re
import os
import subprocess
import logging
import time
from typing import Tuple, Optional
from src.config import config

logger = logging.getLogger(__name__)

LIBVIRT_DOMAIN_NAMESPACE = "http://libvirt.org/schemas/domain/1.0"
NAMESPACES = {'lib': LIBVIRT_DOMAIN_NAMESPACE}

def _letters_to_int(s: str) -> int:
    """
    Convert letter sequence to 0-indexed integer.
    
    Converts alphabetic sequences like 'a', 'b', 'aa' to their corresponding
    0-indexed integer values for device name generation.
    
    Args:
        s: Letter sequence (e.g., 'a', 'b', 'aa')
        
    Returns:
        int: 0-indexed integer representation
        
    Example:
        'a' -> 0, 'b' -> 1, 'z' -> 25, 'aa' -> 26
    """
    logger.debug(f"Converting letters '{s}' to integer")
    res = 0
    for char in s:
        res = res * 26 + (ord(char) - ord('a') + 1)
    result = res - 1
    logger.debug(f"Letters '{s}' converted to integer: {result}")
    return result

def _int_to_letters(n: int) -> str:
    """
    Convert 0-indexed integer to letter sequence.
    
    Converts integer values to their corresponding alphabetic sequences
    for device name generation.
    
    Args:
        n: 0-indexed integer
        
    Returns:
        str: Corresponding letter sequence (e.g., 0->'a', 26->'aa')
        
    Example:
        0 -> 'a', 1 -> 'b', 25 -> 'z', 26 -> 'aa'
    """
    logger.debug(f"Converting integer {n} to letters")
    res = ""
    while True:
        res = chr(ord('a') + (n % 26)) + res
        n //= 26
        if n == 0:
            break
        n -= 1
    logger.debug(f"Integer {n} converted to letters: {res}")
    return res

def get_libvirt_domain(vm_name: str) -> Tuple[libvirt.virConnect, libvirt.virDomain]:
    """
    Establish libvirt connection and lookup domain.
    
    Creates a connection to the libvirt daemon and retrieves the specified
    virtual machine domain object.
    
    Args:
        vm_name: Name of the virtual machine to lookup
        
    Returns:
        Tuple[libvirt.virConnect, libvirt.virDomain]: Connection and domain objects
        
    Raises:
        RuntimeError: If connection fails
        libvirt.libvirtError: If domain not found or other libvirt errors
        
    Note:
        Caller is responsible for closing the connection when done.
    """
    logger.info(f"Establishing libvirt connection for VM '{vm_name}' using URI: {config.LIBVIRT_URI}")
    
    try:
        conn = libvirt.open(config.LIBVIRT_URI)
        if conn is None:
            error_msg = f'Failed to open connection to {config.LIBVIRT_URI}'
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.debug(f"Libvirt connection established successfully")
        
        dom = conn.lookupByName(vm_name)
        logger.info(f"Successfully found domain '{vm_name}' (ID: {dom.ID()}, State: {dom.state()})")
        return conn, dom
        
    except libvirt.libvirtError as e:
        if conn:
            conn.close()
        logger.error(f"Failed to find domain '{vm_name}': {e}")
        raise
    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Unexpected error connecting to libvirt: {e}")
        raise RuntimeError(f"Unexpected error: {e}")

def get_next_available_virtio_dev(dom: libvirt.virDomain) -> str:
    """
    Find next available VirtIO device name.
    
    Analyzes the VM's current disk configuration to determine the next
    available virtio device name following the pattern vd[a-z]+.
    
    Args:
        dom: libvirt Domain object for the target VM
        
    Returns:
        str: Next available device name (e.g., 'vda', 'vdb', 'vdc')
        
    Raises:
        RuntimeError: If no available device names found within the limit
        libvirt.libvirtError: If unable to retrieve VM configuration
        
    Note:
        Searches up to MAX_VIRTIO_DEVICES (default: 702) possible device names.
    """
    vm_name = dom.name()
    logger.info(f"Finding next available VirtIO device for VM '{vm_name}'")
    
    try:
        xml_desc = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_LIVE)
        logger.debug(f"Retrieved VM configuration XML for '{vm_name}'")
        
        root = ET.fromstring(xml_desc)
        disk_elements = root.findall(".//lib:disk", NAMESPACES)
        used_all_dev_names = set()
        
        for disk in disk_elements:
            target_element = disk.find('lib:target', NAMESPACES)
            if target_element is not None:
                dev = target_element.get('dev')
                if dev:
                    used_all_dev_names.add(dev)
                    logger.debug(f"Found used device: {dev}")
        
        logger.info(f"Currently used device names in VM '{vm_name}': {sorted(used_all_dev_names)}")
        
        for i in range(0, config.MAX_VIRTIO_DEVICES):
            current_suffix = _int_to_letters(i)
            proposed_dev_name = f"{config.VIRTIO_DISK_PREFIX}{current_suffix}"
            
            if proposed_dev_name not in used_all_dev_names:
                logger.info(f"Next available device for VM '{vm_name}': {proposed_dev_name}")
                return proposed_dev_name
        
        error_msg = f"No available VirtIO device names found (checked {config.MAX_VIRTIO_DEVICES} possibilities)"
        logger.error(f"Device exhaustion for VM '{vm_name}': {error_msg}")
        raise RuntimeError(error_msg)
        
    except ET.ParseError as e:
        logger.error(f"Failed to parse VM XML for '{vm_name}': {e}")
        raise RuntimeError(f"Failed to parse VM configuration: {e}")
    except Exception as e:
        logger.error(f"Unexpected error finding available device for VM '{vm_name}': {e}")
        raise

def attach_qcow2_disk(dom: libvirt.virDomain, qcow2_path: str, target_dev: str) -> bool:
    """
    Attach QCOW2 disk to running VM.
    
    Performs hot-attach of a QCOW2 disk image to a running virtual machine.
    The operation includes validation, XML generation, attachment, and confirmation.
    
    Args:
        dom: libvirt Domain object for the target VM
        qcow2_path: Full path to the QCOW2 disk image file
        target_dev: Target device name (e.g., 'vdb', 'vdc')
        
    Returns:
        bool: True if attachment successful and confirmed, False otherwise
        
    Raises:
        RuntimeError: If attachment fails or cannot be confirmed
        libvirt.libvirtError: If libvirt operations fail
        
    Note:
        - Checks for existing attachment before attempting
        - Uses live, persistent, and config flags for attachment
        - Confirms attachment by polling VM configuration
    """
    vm_name = dom.name()
    logger.info(f"Starting disk attachment - VM: '{vm_name}', Path: '{qcow2_path}', Target: '{target_dev}'")
    
    try:
        # Validate disk file exists and is readable
        if not os.path.exists(qcow2_path):
            error_msg = f"Disk file does not exist: {qcow2_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if not os.access(qcow2_path, os.R_OK):
            error_msg = f"Disk file is not readable: {qcow2_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.debug(f"Disk file validation passed: {qcow2_path}")
        
        # Check if disk already attached
        xml_desc = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_LIVE)
        root = ET.fromstring(xml_desc)
        
        for disk in root.findall(".//lib:disk", NAMESPACES):
            target = disk.find('lib:target', NAMESPACES)
            source = disk.find('lib:source', NAMESPACES)
            
            # Check for same target device
            if target is not None and target.get('dev') == target_dev:
                existing_source = source.get('file') if source is not None else 'unknown'
                if existing_source == qcow2_path:
                    logger.warning(f"Disk '{qcow2_path}' already attached as '{target_dev}' to VM '{vm_name}'")
                    return True
                else:
                    error_msg = f"Target device '{target_dev}' already in use by '{existing_source}'"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            
            # Check for same source file
            if source is not None and source.get('file') == qcow2_path:
                existing_target = target.get('dev') if target is not None else 'unknown'
                error_msg = f"Disk '{qcow2_path}' already attached as '{existing_target}'"
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        logger.debug(f"Pre-attachment validation passed for VM '{vm_name}'")
        
        # Create disk XML
        ET.register_namespace('', LIBVIRT_DOMAIN_NAMESPACE)
        disk_element = ET.Element('disk', type='file', device='disk')
        ET.SubElement(disk_element, 'driver', name='qemu', type='qcow2', cache='none')
        ET.SubElement(disk_element, 'source', file=qcow2_path)
        ET.SubElement(disk_element, 'target', dev=target_dev, bus='virtio')
        
        disk_xml = ET.tostring(disk_element, encoding='unicode')
        logger.info(f"Generated disk XML for VM '{vm_name}': {disk_xml}")
        
        # Perform attachment
        flags = (libvirt.VIR_DOMAIN_ATTACH_DEVICE_LIVE | 
                libvirt.VIR_DOMAIN_ATTACH_DEVICE_PERSIST | 
                libvirt.VIR_DOMAIN_ATTACH_DEVICE_CONFIG)
        
        logger.debug(f"Executing disk attachment with flags: {flags}")
        dom.attachDeviceFlags(disk_xml, flags)
        logger.info(f"Disk attachment command executed for VM '{vm_name}', device '{target_dev}'")
        
        # Confirm attachment
        logger.debug(f"Starting attachment confirmation (max retries: {config.DISK_ATTACH_CONFIRM_RETRIES})")
        for attempt in range(config.DISK_ATTACH_CONFIRM_RETRIES):
            current_xml_desc = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_LIVE)
            current_root = ET.fromstring(current_xml_desc)
            
            for disk in current_root.findall(".//lib:disk", NAMESPACES):
                target = disk.find('lib:target', NAMESPACES)
                source = disk.find('lib:source', NAMESPACES)
                if (target is not None and target.get('dev') == target_dev and
                    source is not None and source.get('file') == qcow2_path):
                    logger.info(f"Successfully confirmed disk attachment - VM: '{vm_name}', Device: '{target_dev}', Attempt: {attempt + 1}")
                    return True
            
            logger.debug(f"Attachment not yet confirmed, attempt {attempt + 1}/{config.DISK_ATTACH_CONFIRM_RETRIES}")
            time.sleep(config.DISK_ATTACH_CONFIRM_DELAY)
        
        error_msg = f"Failed to confirm disk attachment after {config.DISK_ATTACH_CONFIRM_RETRIES} attempts"
        logger.error(f"Attachment confirmation failed for VM '{vm_name}', device '{target_dev}': {error_msg}")
        raise RuntimeError(error_msg)
        
    except (ValueError, RuntimeError) as e:
        logger.error(f"Disk attachment failed for VM '{vm_name}': {e}")
        raise
    except libvirt.libvirtError as e:
        logger.error(f"Libvirt error during disk attachment for VM '{vm_name}': {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during disk attachment for VM '{vm_name}': {e}")
        return False