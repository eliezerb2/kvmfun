import libvirt # type: ignore
import logging
import time
from src.services.disk_utils import _check_disk_conflicts, _create_disk_xml
from src.utils.libvirt_utils import parse_domain_xml
from src.utils.config import config
from src.utils.validation_utils import validate_qcow2_path

logger: logging.Logger = logging.getLogger(__name__)

def _confirm_attachment(dom: libvirt.virDomain, qcow2_path: str, target_dev: str) -> bool:
    """Confirm disk attachment by polling VM configuration."""
    vm_name = dom.name()
    logger.debug(f"Starting attachment confirmation for VM '{vm_name}', device '{target_dev}'")
    
    for attempt in range(config.DISK_ATTACH_CONFIRM_RETRIES):
        logger.debug(f"Confirmation attempt {attempt + 1}/{config.DISK_ATTACH_CONFIRM_RETRIES}")
        root = parse_domain_xml(dom, live=True)
        
        for disk in root.findall(".//devices/disk"):
            target = disk.find("target")
            source = disk.find("source")
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
    vm_name: str = dom.name()
    logger.info(f"Starting disk attachment - VM: '{vm_name}', Path: '{qcow2_path}', Target: '{target_dev}'")
    
    # TODO: move the logic for getting next available device from endpoint to here
    
    try:
        # TODO: do we need this?
        validate_qcow2_path(qcow2_path)
        logger.debug(f"Disk file validation passed: {qcow2_path}")
        
        if _check_disk_conflicts(dom, qcow2_path, target_dev):
            return True  # Already attached
        
        # Add custom metadata to the disk XML
        disk_metadata: dict = {"status": "open for write"}
        
        disk_xml: str = _create_disk_xml(qcow2_path, target_dev, metadata=disk_metadata)
        logger.debug(f"Attach disk XML:\n{disk_xml}")
        
        flags: int = libvirt.VIR_DOMAIN_AFFECT_LIVE | libvirt.VIR_DOMAIN_AFFECT_CONFIG
        
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
    except Exception as e:
        logger.error(f"Unexpected error during disk attachment for VM '{vm_name}': {e}")
        return False