import libvirt
import xml.etree.ElementTree as ET
import re
import os
import subprocess
import logging
import time
from typing import Tuple

QCOW2_DEFAULT_SIZE = "1G"
LIBVIRT_DOMAIN_NAMESPACE = "http://libvirt.org/schemas/domain/1.0"
NAMESPACES = {'lib': LIBVIRT_DOMAIN_NAMESPACE}
VIRTIO_DISK_PREFIX = "vd"

def _letters_to_int(s: str) -> int:
    res = 0
    for char in s:
        res = res * 26 + (ord(char) - ord('a') + 1)
    return res - 1

def _int_to_letters(n: int) -> str:
    res = ""
    while True:
        res = chr(ord('a') + (n % 26)) + res
        n //= 26
        if n == 0:
            break
        n -= 1
    return res

def get_libvirt_domain(vm_name: str) -> Tuple[libvirt.virConnect, libvirt.virDomain]:
    conn = libvirt.open('qemu:///system')
    if conn is None:
        raise RuntimeError('Failed to open connection to qemu:///system')
    
    dom = conn.lookupByName(vm_name)
    return conn, dom

def get_next_available_virtio_dev(dom: libvirt.virDomain) -> str:
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
    
    for i in range(0, 702):
        current_suffix = _int_to_letters(i)
        proposed_dev_name = f"{VIRTIO_DISK_PREFIX}{current_suffix}"
        
        if proposed_dev_name not in used_all_dev_names:
            return proposed_dev_name
    
    raise RuntimeError("No available VirtIO device suffixes")

def attach_qcow2_disk(dom: libvirt.virDomain, qcow2_path: str, target_dev: str) -> bool:
    try:
        # Check if disk already attached
        xml_desc = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_LIVE)
        root = ET.fromstring(xml_desc)
        
        for disk in root.findall(".//lib:disk", NAMESPACES):
            target = disk.find('lib:target', NAMESPACES)
            source = disk.find('lib:source', NAMESPACES)
            if (target is not None and target.get('dev') == target_dev and
                source is not None and source.get('file') == qcow2_path):
                logging.warning(f"Disk already attached as {target_dev}")
                return True
        
        # Create disk XML
        ET.register_namespace('', LIBVIRT_DOMAIN_NAMESPACE)
        disk_element = ET.Element('disk', type='file', device='disk')
        ET.SubElement(disk_element, 'driver', name='qemu', type='qcow2', cache='none')
        ET.SubElement(disk_element, 'source', file=qcow2_path)
        ET.SubElement(disk_element, 'target', dev=target_dev, bus='virtio')
        
        disk_xml = ET.tostring(disk_element, encoding='unicode')
        
        flags = (libvirt.VIR_DOMAIN_ATTACH_DEVICE_LIVE | 
                libvirt.VIR_DOMAIN_ATTACH_DEVICE_PERSIST | 
                libvirt.VIR_DOMAIN_ATTACH_DEVICE_CONFIG)
        
        dom.attachDeviceFlags(disk_xml, flags)
        
        # Confirm attachment
        for i in range(5):
            current_xml_desc = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_LIVE)
            current_root = ET.fromstring(current_xml_desc)
            
            for disk in current_root.findall(".//lib:disk", NAMESPACES):
                target = disk.find('lib:target', NAMESPACES)
                source = disk.find('lib:source', NAMESPACES)
                if (target is not None and target.get('dev') == target_dev and
                    source is not None and source.get('file') == qcow2_path):
                    return True
            time.sleep(0.5)
        
        raise RuntimeError(f"Failed to confirm disk attachment")
        
    except Exception as e:
        logging.error(f"Error attaching disk: {e}")
        return False