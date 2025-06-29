from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import libvirt
import logging
from src.modules.disk_attach import get_libvirt_domain, get_next_available_virtio_dev, attach_qcow2_disk
from src.modules.disk_detach import detach_disk

router = APIRouter(prefix="/disk", tags=["disk"])

class AttachDiskRequest(BaseModel):
    vm_name: str
    qcow2_path: str
    target_dev: str = None

class DetachDiskRequest(BaseModel):
    vm_name: str
    target_dev: str

@router.post("/attach")
async def attach_disk_endpoint(request: AttachDiskRequest):
    try:
        conn, dom = get_libvirt_domain(request.vm_name)
        
        if not request.target_dev:
            request.target_dev = get_next_available_virtio_dev(dom)
        
        success = attach_qcow2_disk(dom, request.qcow2_path, request.target_dev)
        conn.close()
        
        if success:
            return {"status": "success", "target_dev": request.target_dev}
        else:
            raise HTTPException(status_code=500, detail="Failed to attach disk")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/detach")
async def detach_disk_endpoint(request: DetachDiskRequest):
    try:
        conn = libvirt.open('qemu:///system')
        if conn is None:
            raise HTTPException(status_code=500, detail="Failed to connect to libvirt")
        
        success = detach_disk(conn, request.vm_name, request.target_dev)
        conn.close()
        
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Failed to detach disk")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list/{vm_name}")
async def list_disks(vm_name: str):
    try:
        conn, dom = get_libvirt_domain(vm_name)
        xml_desc = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_LIVE)
        conn.close()
        
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_desc)
        
        disks = []
        for disk in root.findall(".//disk[@type='file']"):
            target = disk.find("target")
            source = disk.find("source")
            if target is not None and source is not None:
                disks.append({
                    "target_dev": target.get("dev"),
                    "source_file": source.get("file"),
                    "bus": target.get("bus")
                })
        
        return {"vm_name": vm_name, "disks": disks}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))