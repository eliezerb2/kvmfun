import libvirt
import xml.etree.ElementTree as ET
import time
import logging
import json

def get_disk_xml_for_target_dev(dom: libvirt.virDomain, target_dev: str) -> str:
    current_dom_xml = dom.XMLDesc(0)
    root = ET.fromstring(current_dom_xml)
    
    for disk_elem in root.findall(".//disk"):
        target_elem = disk_elem.find("target")
        if target_elem is not None and target_elem.get("dev") == target_dev:
            source_elem = disk_elem.find("source")
            if source_elem is None or not source_elem.get("file"):
                raise ValueError(f"Disk '{target_dev}' is not a file-backed disk")
            
            return ET.tostring(disk_elem, encoding='unicode')
    
    raise ValueError(f"Disk with target '{target_dev}' not found")

def poll_for_disk_removal(dom: libvirt.virDomain, target_dev: str, timeout: int = 60) -> bool:
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
            return True
        
        time.sleep(0.5)
    
    return False

def detach_disk(conn: libvirt.virConnect, vm_name: str, target_dev: str) -> bool:
    try:
        dom = conn.lookupByName(vm_name)
        if dom is None:
            raise ValueError(f'VM "{vm_name}" not found')
        
        disk_xml_to_detach = get_disk_xml_for_target_dev(dom, target_dev)
        
        detach_flags = libvirt.VIR_DOMAIN_AFFECT_LIVE | libvirt.VIR_DOMAIN_AFFECT_CONFIG
        
        ret = dom.detachDeviceFlags(disk_xml_to_detach, detach_flags)
        if ret != 0:
            raise RuntimeError(f"Failed to initiate detach operation")
        
        if not poll_for_disk_removal(dom, target_dev):
            raise RuntimeError(f"Disk '{target_dev}' failed to detach")
        
        return True
        
    except Exception as e:
        logging.error(f"Error detaching disk: {e}")
        return False