from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import libvirt
import logging
from src.modules.disk_attach import get_libvirt_domain, get_next_available_virtio_dev, attach_qcow2_disk
from src.modules.disk_detach import detach_disk

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/disk", tags=["disk"])

class AttachDiskRequest(BaseModel):
    vm_name: str = Field(..., description="Name of the virtual machine")
    qcow2_path: str = Field(..., description="Path to the QCOW2 disk image")
    target_dev: str = Field(None, description="Target device name (auto-assigned if not provided)")

class DetachDiskRequest(BaseModel):
    vm_name: str = Field(..., description="Name of the virtual machine")
    target_dev: str = Field(..., description="Target device name to detach")

@router.post("/attach", summary="Attach disk to VM")
async def attach_disk_endpoint(request: AttachDiskRequest):
    """
    Attach a QCOW2 disk to a running virtual machine.
    
    - **vm_name**: Name of the target VM
    - **qcow2_path**: Full path to the QCOW2 disk file
    - **target_dev**: Device name (optional, auto-assigned if not provided)
    """
    logger.info(f"Attaching disk {request.qcow2_path} to VM {request.vm_name}")
    try:
        conn, dom = get_libvirt_domain(request.vm_name)
        
        if not request.target_dev:
            request.target_dev = get_next_available_virtio_dev(dom)
        
        success = attach_qcow2_disk(dom, request.qcow2_path, request.target_dev)
        conn.close()
        
        if success:
            logger.info(f"Successfully attached disk as {request.target_dev}")
            return {"status": "success", "target_dev": request.target_dev}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to attach disk")
            
    except libvirt.libvirtError as e:
        if "Domain not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"VM '{request.vm_name}' not found")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error attaching disk: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/detach", summary="Detach disk from VM")
async def detach_disk_endpoint(request: DetachDiskRequest):
    """
    Detach a disk from a running virtual machine.
    
    - **vm_name**: Name of the target VM
    - **target_dev**: Device name to detach (e.g., 'vdb')
    """
    logger.info(f"Detaching disk {request.target_dev} from VM {request.vm_name}")
    try:
        conn = libvirt.open('qemu:///system')
        if conn is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to connect to libvirt")
        
        success = detach_disk(conn, request.vm_name, request.target_dev)
        conn.close()
        
        if success:
            logger.info(f"Successfully detached disk {request.target_dev}")
            return {"status": "success"}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to detach disk")
            
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error detaching disk: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/list/{vm_name}", summary="List VM disks")
async def list_disks(vm_name: str):
    """
    List all disks attached to a virtual machine.
    
    - **vm_name**: Name of the virtual machine
    """
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
        
    except libvirt.libvirtError as e:
        if "Domain not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"VM '{vm_name}' not found")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing disks: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))