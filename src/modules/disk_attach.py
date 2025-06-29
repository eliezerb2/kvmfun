import libvirt
import xml.etree.ElementTree as ET
import os
import logging
import time
from typing import Optional
from src.config import config
from src.modules.libvirt_utils import get_libvirt_domain, parse_domain_xml, get_next_available_virtio_dev, NAMESPACES, LIBVIRT_DOMAIN_NAMESPACE
from src.modules.validation_utils import validate_qcow2_path

logger = logging.getLogger(__name__)



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

def _create_disk_xml(qcow2_path: str, target_dev: str) -> str:
    """Create disk XML for attachment."""
    logger.debug(f"Creating disk XML for '{qcow2_path}' as '{target_dev}'")
    ET.register_namespace('', LIBVIRT_DOMAIN_NAMESPACE)
    disk_element = ET.Element('disk', type='file', device='disk')
    ET.SubElement(disk_element, 'driver', name='qemu', type='qcow2', cache='none')
    ET.SubElement(disk_element, 'source', file=qcow2_path)
    ET.SubElement(disk_element, 'target', dev=target_dev, bus='virtio')
    disk_xml = ET.tostring(disk_element, encoding='unicode')
    logger.debug(f"Generated disk XML: {disk_xml}")
    return disk_xml

def _confirm_attachment(dom: libvirt.virDomain, qcow2_path: str, target_dev: str) -> bool:
    """Confirm disk attachment by polling VM configuration."""
    vm_name = dom.name()
    logger.debug(f"Starting attachment confirmation for VM '{vm_name}', device '{target_dev}'")
    
    for attempt in range(config.DISK_ATTACH_CONFIRM_RETRIES):
        logger.debug(f"Confirmation attempt {attempt + 1}/{config.DISK_ATTACH_CONFIRM_RETRIES}")
        root = parse_domain_xml(dom, live=True)
        
        for disk in root.findall(".//lib:disk", NAMESPACES):
            target = disk.find('lib:target', NAMESPACES)
            source = disk.find('lib:source', NAMESPACES)
            if (target is not None and target.get('dev') == target_dev and
                source is not None and source.get('file') == qcow2_path):
                logger.info(f"Successfully confirmed disk attachment - VM: '{vm_name}', Device: '{target_dev}', Attempt: {attempt + 1}")
                return True
        
        if attempt < config.DISK_ATTACH_CONFIRM_RETRIES - 1:
            logger.debug(f"Attachment not confirmed, waiting {config.DISK_ATTACH_CONFIRM_DELAY}s")
            time.sleep(config.DISK_ATTACH_CONFIRM_DELAY)
    
    logger.error(f"Failed to confirm attachment after {config.DISK_ATTACH_CONFIRM_RETRIES} attempts")
    return False

def attach_disk(dom: libvirt.virDomain, qcow2_path: str, target_dev: str) -> bool:
    """Attach disk to running VM."""
    vm_name = dom.name()
    logger.info(f"Starting disk attachment - VM: '{vm_name}', Path: '{qcow2_path}', Target: '{target_dev}'")
    
    try:
        validate_qcow2_path(qcow2_path)
        logger.debug(f"Disk file validation passed: {qcow2_path}")
        
        if _check_disk_conflicts(dom, qcow2_path, target_dev):
            return True  # Already attached
        
        disk_xml = _create_disk_xml(qcow2_path, target_dev)
        flags = (libvirt.VIR_DOMAIN_ATTACH_DEVICE_LIVE | 
                libvirt.VIR_DOMAIN_ATTACH_DEVICE_PERSIST | 
                libvirt.VIR_DOMAIN_ATTACH_DEVICE_CONFIG)
        
        logger.debug(f"Executing disk attachment with flags: {flags}")
        dom.attachDeviceFlags(disk_xml, flags)
        logger.info(f"Disk attachment command executed for VM '{vm_name}', device '{target_dev}'")
        
        if not _confirm_attachment(dom, qcow2_path, target_dev):
            raise RuntimeError(f"Failed to confirm disk attachment after {config.DISK_ATTACH_CONFIRM_RETRIES} attempts")
        
        logger.info(f"Successfully attached disk '{qcow2_path}' as '{target_dev}' to VM '{vm_name}'")
        return True
        
    except (ValueError, RuntimeError) as e:
        logger.error(f"Disk attachment failed for VM '{vm_name}': {e}")
        raise
    except libvirt.libvirtError as e:
        logger.error(f"Libvirt error during disk attachment for VM '{vm_name}': {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during disk attachment for VM '{vm_name}': {e}")
        return False