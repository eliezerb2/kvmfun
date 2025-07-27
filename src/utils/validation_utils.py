import re
import logging
from typing import Optional

logger: logging.Logger = logging.getLogger(__name__)

def validate_size_gb(size_gb: int) -> int:
    """
    Validate size in GB for storage volumes.
    
    Args:
        size_gb: Size in GB to validate
        
    Returns:
        int: Validated size in GB
        
    Raises:
        ValueError: If size is not a positive integer or exceeds 1024 GB
    """
    if not isinstance(size_gb, int) or size_gb <= 0:
        raise ValueError('Size must be a positive integer')
    
    if size_gb > 1024:
        raise ValueError('Size must not exceed 1024 GB')
    
    return size_gb

def validate_name(name: str, type_name: str = "Name") -> str:
    """
    Validate storage volume name format.
    
    Args:
        volume_name: Storage volume name to validate
        
    Returns:
        str: Validated storage volume name
        
    Raises:
        ValueError: If volume name format is invalid
    """
    if not name or not isinstance(name, str):
        msg: str = f'{type_name} must be a non-empty string'
        logger.error(msg)
        raise ValueError(msg)

    if not re.match(r'^[a-zA-Z0-9_.-]+$', name):
        raise ValueError(f'{type_name} must contain only alphanumeric characters, hyphens, underscores, and periods')
    if len(name) > 255:
        raise ValueError(f'{type_name} must be 255 characters or less')

    return name

def validate_target_device(target_dev: Optional[str]) -> str | None:
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
        return ""
    
    if not isinstance(target_dev, str):
        raise ValueError('Target device must be a string')
    
    if not re.match(r'^[vs]d[a-z]+$', target_dev):
        raise ValueError('Target device must follow format vd[a-z]+ or sd[a-z]+ (e.g., vda, sdb)')
    
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
    
    return qcow2_path