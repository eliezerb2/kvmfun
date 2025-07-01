import re
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def validate_vm_name(vm_name: str) -> str:
    """
    Validate VM name format.
    
    Args:
        vm_name: VM name to validate
        
    Returns:
        str: Validated VM name
        
    Raises:
        ValueError: If VM name format is invalid
    """
    if not vm_name or not isinstance(vm_name, str):
        raise ValueError('VM name must be a non-empty string')
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', vm_name):
        raise ValueError('VM name must contain only alphanumeric characters, hyphens, and underscores')
    
    if len(vm_name) > 255:
        raise ValueError('VM name must be 255 characters or less')
    
    return vm_name

def validate_target_device(target_dev: Optional[str]) -> Optional[str]:
    """
    Validate target device name format.
    
    Args:
        target_dev: Target device name to validate (can be None)
        
    Returns:
        str or None: Validated target device name
        
    Raises:
        ValueError: If target device format is invalid
    """
    if target_dev is None:
        return None
    
    if not isinstance(target_dev, str):
        raise ValueError('Target device must be a string')
    
    if not re.match(r'^vd[a-z]+$', target_dev):
        raise ValueError('Target device must follow format vd[a-z]+ (e.g., vda, vdb)')
    
    return target_dev

def validate_qcow2_path(qcow2_path: str) -> str:
    """
    Validate QCOW2 file path.
    
    Args:
        qcow2_path: Path to QCOW2 file
        
    Returns:
        str: Validated path
        
    Raises:
        ValueError: If path is invalid or file doesn't exist
    """
    if not qcow2_path or not isinstance(qcow2_path, str):
        raise ValueError('QCOW2 path must be a non-empty string')
    
    if not qcow2_path.endswith('.qcow2'):
        raise ValueError('Disk path must end with .qcow2')
    
    if not os.path.exists(qcow2_path):
        raise ValueError(f'Disk file not found: {qcow2_path}')
    
    if not os.access(qcow2_path, os.R_OK):
        raise ValueError(f'Disk file is not readable: {qcow2_path}')
    
    return qcow2_path