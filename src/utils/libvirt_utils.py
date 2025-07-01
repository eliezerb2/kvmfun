import libvirt
import xml.etree.ElementTree as ET
import logging
from typing import Tuple
from src.utils.config import config

logger = logging.getLogger(__name__)

LIBVIRT_DOMAIN_NAMESPACE = "http://libvirt.org/schemas/domain/1.0"
NAMESPACES = {'lib': LIBVIRT_DOMAIN_NAMESPACE}

def get_libvirt_connection() -> libvirt.virConnect:
    """
    Establish libvirt connection.
    
    Creates a connection to the libvirt daemon.
    
    Returns:
        libvirt.virConnect: Connection object
        
    Raises:
        RuntimeError: If connection fails
        
    Note:
        Caller is responsible for closing the connection when done.
    """
    logger.info(f"Establishing libvirt connection using URI: {config.LIBVIRT_URI}")
    
    try:
        conn = libvirt.open(config.LIBVIRT_URI)
        if conn is None:
            error_msg = f'Failed to open connection to {config.LIBVIRT_URI}'
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.debug(f"Libvirt connection established successfully")
        return conn
        
    except Exception as e:
        logger.error(f"Unexpected error connecting to libvirt: {e}")
        raise RuntimeError(f"Unexpected error: {e}")

def get_connection_dependency() -> libvirt.virConnect:
    """
    FastAPI dependency to manage the libvirt connection lifecycle.

    Yields:
        libvirt.virConnect: An active libvirt connection object.
    
    Note:
        This generator function establishes a connection and yields it to the
        request handler. The 'finally' block ensures the connection is
        always closed, even if errors occur during the request.
    """
    logger.debug("Dependency: acquiring libvirt connection.")
    conn = None
    try:
        conn = get_libvirt_connection()
        yield conn
    finally:
        if conn:
            conn.close()
            logger.debug("Dependency: libvirt connection closed.")

def parse_domain_xml(dom: libvirt.virDomain, live: bool = True) -> ET.Element:
    """
    Parse domain XML configuration.
    
    Args:
        dom: libvirt Domain object
        live: Whether to get live configuration (default: True)
        
    Returns:
        ET.Element: Parsed XML root element
        
    Raises:
        ET.ParseError: If XML parsing fails
        libvirt.libvirtError: If unable to retrieve XML
    """
    vm_name = dom.name()
    logger.debug(f"Parsing XML for VM '{vm_name}' (live={live})")
    
    try:
        flags = libvirt.VIR_DOMAIN_XML_LIVE if live else 0
        xml_desc = dom.XMLDesc(flags)
        root = ET.fromstring(xml_desc)
        logger.debug(f"Successfully parsed XML for VM '{vm_name}'")
        return root
        
    except ET.ParseError as e:
        logger.error(f"Failed to parse VM XML for '{vm_name}': {e}")
        raise
    except libvirt.libvirtError as e:
        logger.error(f"Failed to retrieve VM XML for '{vm_name}': {e}")
        raise

def _letters_to_int(s: str) -> int:
    """Convert letter sequence to 0-indexed integer."""
    res = 0
    for char in s:
        res = res * 26 + (ord(char) - ord('a') + 1)
    return res - 1

def _int_to_letters(n: int) -> str:
    """Convert 0-indexed integer to letter sequence."""
    res = ""
    while True:
        res = chr(ord('a') + (n % 26)) + res
        n //= 26
        if n == 0:
            break
        n -= 1
    return res

def get_next_available_virtio_dev(dom: libvirt.virDomain) -> str:
    """Find next available VirtIO device name."""
    vm_name = dom.name()
    logger.info(f"Finding next available VirtIO device for VM '{vm_name}'")
    
    root = parse_domain_xml(dom, live=True)
    used_devices = set()
    
    for disk in root.findall(".//lib:disk", NAMESPACES):
        target = disk.find('lib:target', NAMESPACES)
        if target is not None:
            dev = target.get('dev')
            if dev:
                used_devices.add(dev)
    
    for i in range(config.MAX_VIRTIO_DEVICES):
        suffix = _int_to_letters(i)
        proposed_dev = f"{config.VIRTIO_DISK_PREFIX}{suffix}"
        
        if proposed_dev not in used_devices:
            logger.info(f"Next available device for VM '{vm_name}': {proposed_dev}")
            return proposed_dev
    
    raise RuntimeError(f"No available VirtIO device names found (checked {config.MAX_VIRTIO_DEVICES} possibilities)")