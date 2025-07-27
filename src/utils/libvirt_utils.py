import libvirt # type: ignore
import xml.etree.ElementTree as ET
import logging
from src.utils.config import config

logger: logging.Logger = logging.getLogger(__name__)

# Compatibility shim for older libvirt-python versions that may lack modern flags.
# This patches the module with integer values that correspond to the flags,
# allowing the code to run even if the Python bindings are slightly outdated.
if not hasattr(libvirt, 'VIR_DOMAIN_ATTACH_DEVICE_LIVE'):
    setattr(libvirt, 'VIR_DOMAIN_ATTACH_DEVICE_LIVE', 1)
if not hasattr(libvirt, 'VIR_DOMAIN_ATTACH_DEVICE_PERSIST'):
    setattr(libvirt, 'VIR_DOMAIN_ATTACH_DEVICE_PERSIST', 2)
if not hasattr(libvirt, 'VIR_DOMAIN_ATTACH_DEVICE_CONFIG'):
    setattr(libvirt, 'VIR_DOMAIN_ATTACH_DEVICE_CONFIG', 4)

if not hasattr(libvirt, 'VIR_DOMAIN_AFFECT_LIVE'):
    setattr(libvirt, 'VIR_DOMAIN_AFFECT_LIVE', 1)
if not hasattr(libvirt, 'VIR_DOMAIN_AFFECT_CONFIG'):
    setattr(libvirt, 'VIR_DOMAIN_AFFECT_CONFIG', 2)

if not hasattr(libvirt, 'VIR_DOMAIN_XML_LIVE'):
    setattr(libvirt, 'VIR_DOMAIN_XML_LIVE', 1)

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
        conn: libvirt.virConnect = libvirt.open(config.LIBVIRT_URI)
        if conn is None:
            error_msg: str = f'Failed to open connection to {config.LIBVIRT_URI}'
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
    conn: libvirt.virConnect | None = None
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
    vm_name: str = dom.name()
    logger.debug(f"Parsing XML for VM '{vm_name}' (live={live})")
    
    try:
        flags: int = libvirt.VIR_DOMAIN_XML_LIVE if live else 0
        xml_desc: str = dom.XMLDesc(flags)
        root: ET.Element = ET.fromstring(xml_desc)
        logger.debug(f"Successfully parsed XML for VM '{vm_name}' : {root}")
        return root
        
    except ET.ParseError as e:
        logger.error(f"Failed to parse VM XML for '{vm_name}': {e}")
        raise
    except libvirt.libvirtError as e:
        logger.error(f"Failed to retrieve VM XML for '{vm_name}': {e}")
        raise

def _letters_to_int(s: str) -> int:
    """Convert letter sequence to 0-indexed integer."""
    res: int = 0
    for char in s:
        res = res * 26 + (ord(char) - ord('a') + 1)
    return res - 1

def _int_to_letters(n: int) -> str:
    """Convert 0-indexed integer to letter sequence."""
    res: str = ""
    while True:
        res = chr(ord('a') + (n % 26)) + res
        n //= 26
        if n == 0:
            break
        n -= 1
    return res

def get_next_available_scsi_dev(dom: libvirt.virDomain) -> str:
    """
    Find the next available SCSI disk target device name (e.g., sdb, sdc)
    for use with virtio-scsi controller.

    Args:
        dom: libvirt Domain object representing the VM.

    Returns:
        str: The next available SCSI disk device name.

    Raises:
        RuntimeError: If no available device name is found.
    """
    vm_name: str = dom.name()
    logger.info(f"Finding next available SCSI device for VM '{vm_name}'")

    root: ET.Element = parse_domain_xml(dom, live=True)
    used_devices: set[str] = set()

    for disk in root.findall(".//devices/disk"):
        target: ET.Element | None = disk.find("target")
        bus: str | None = disk.get("bus") or (target.get("bus") if target is not None else None)
        dev: str | None = target.get("dev") if target is not None else None

        if dev and (bus == "scsi" or dev.startswith("sd")):
            used_devices.add(dev)

    for i in range(config.MAX_SCSI_DEVICES):
        suffix: str = _int_to_letters(i)
        proposed_dev: str = f"sd{suffix}"

        if proposed_dev not in used_devices:
            logger.info(f"Next available SCSI device for VM '{vm_name}': {proposed_dev}")
            return proposed_dev

    raise RuntimeError(f"No available SCSI device names found (checked {config.MAX_SCSI_DEVICES} possibilities)")
