import os
import logging
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import libvirt # type: ignore
import textwrap

logger: logging.Logger = logging.getLogger(__name__)

def list_vms(conn: libvirt.virConnect) -> list:
    """
    List all virtual machines defined in the libvirt hypervisor.
    
    Args:
        conn (libvirt.virConnect): Connection to the libvirt hypervisor.
        
    Returns:
        list: A list of dictionaries containing VM names and UUIDs.
    """
    vms: list[dict[str, str]] = []
    domains: list[libvirt.virDomain] = conn.listAllDomains()
    for domain in domains:
        try:
            vm_info: dict[str, str] = {
                "name": domain.name(),
                "uuid": domain.UUIDString()
            }
            vms.append(vm_info)
        except libvirt.libvirtError as e:
            logger.error(f"Error retrieving VM information: {e}")
    return vms

def create_vm(
    vm_name: str, memory_mb: int, vcpu_count: int, disk_path: str, network_name: str, conn: libvirt.virConnect) -> str:
    """
    Create a new virtual machine with the specified parameters.
    
    Args:
        vm_name (str): Name of the virtual machine.
        memory_mb (int): Amount of memory in MB for the VM.
        vcpu_count (int): Number of virtual CPUs for the VM.
        disk_path (str): Path to the disk image file (e.g., qcow2).
        network_name (str): Name of the network to attach the VM to.
        conn (libvirt.virConnect): Connection to the libvirt hypervisor.
    Returns:
        str: UUID of the created VM.
    Raises:
        Exception: If the VM cannot be defined.
    """
    # Escape user inputs to prevent XML injection
    safe_vm_name: str = escape(str(vm_name))
    safe_memory_mb: str = escape(str(memory_mb))
    safe_vcpu_count: str = escape(str(vcpu_count))
    safe_disk_path: str = escape(str(disk_path))
    safe_network_name: str = escape(str(network_name))

    # Define VM XML
    domain_xml: str = textwrap.dedent(f"""
        <domain type='qemu'>
          <name>{safe_vm_name}</name>
          <memory unit='MiB'>{safe_memory_mb}</memory>
          <vcpu>{safe_vcpu_count}</vcpu>
          <os>
            <type arch='x86_64' machine='q35'>hvm</type>
            <boot dev='hd'/>
          </os>
          <devices>
            <disk type='file' device='disk'>
              <driver name='qemu' type='qcow2'/>
              <source file='{safe_disk_path}'/>
              <target dev='vda' bus='virtio'/>
            </disk>
            <controller type='scsi' model='virtio-scsi' index='0'/>
            <controller type='pci' index='0' model='pcie-root'/>
            <interface type='network'>
              <source network='{safe_network_name}'/>
              <model type='virtio'/>
            </interface>
            <graphics type='vnc' port='-1'/>
          </devices>
        </domain>
    """)

    logger.debug(f"Creating VM with XML:\n{domain_xml}")

    # Define the VM
    domain: libvirt.virDomain = conn.defineXML(domain_xml)
    if domain is None:
        raise Exception("Failed to define the VM domain")
    return domain.UUIDString()
  
def delete_vm(vm_name: str, conn: libvirt.virConnect) -> bool:
    """
    Delete a virtual machine by its name.
    
    Args:
        vm_name (str): Name of the virtual machine to delete.
        conn (libvirt.virConnect): Connection to the libvirt hypervisor.
        
    Returns:
        bool: True if the VM was successfully deleted, False if not found.
        
    Raises:
        Exception: If there is an error during deletion.
    """
    try:
        domain: libvirt.virDomain = conn.lookupByName(vm_name)
        # check if vm is running
        if domain.isActive():
            domain.destroy()  # Stop the VM if it's running
        domain.undefine()  # Remove the VM definition
        return True
    except libvirt.libvirtError as e:
        if 'does not exist' in str(e):
            return False  # VM not found
        raise e  # Re-raise other errors  

def start_vm(vm_name: str, conn: libvirt.virConnect) -> bool:
    """
    Start a virtual machine by its name.
    Args:
        vm_name (str): Name of the virtual machine to start.
        conn (libvirt.virConnect): Connection to the libvirt hypervisor.
    Returns:
        bool: True if the VM was successfully started, False otherwise.
    Raises:
        Exception: If the VM cannot be found or started.
    """
    try:
        domain: libvirt.virDomain = conn.lookupByName(vm_name)
        domain.create()
        return True
    except libvirt.libvirtError as e:
        raise Exception(f"Failed to start VM: {e}")

def stop_vm(vm_name: str, conn: libvirt.virConnect) -> bool:
    """
    Stop a virtual machine by its name.
    Args:
        vm_name (str): Name of the virtual machine to stop.
        conn (libvirt.virConnect): Connection to the libvirt hypervisor.

    Returns:
        bool: True if the VM was successfully stopped, False otherwise.
    Raises:
        Exception: If the VM cannot be found or stopped.
    """
    domain: libvirt.virDomain = conn.lookupByName(vm_name)
    if domain is None:
        raise Exception("Failed to find VM with name: " + vm_name)
    try:
        domain.shutdown()
        return True
    except libvirt.libvirtError as e:
        raise Exception(f"Failed to stop VM: {e}")
    
def get_vm_info(vm_name: str, conn: libvirt.virConnect) -> dict:
    """
    Retrieve information about a virtual machine by its name.
    Args:
        vm_name (str): Name of the virtual machine.
        conn (libvirt.virConnect): Connection to the libvirt hypervisor.

    Returns:
        dict: A dictionary containing VM information (name, UUID, state, memory, vCPU count, and disk path).
    Raises:
        Exception: If the VM cannot be found.
    """
    try:
        domain: libvirt.virDomain = conn.lookupByName(vm_name)
        info: tuple = domain.info()
        xml_desc: str = domain.XMLDesc(0)
        logger.debug(f"VM XML description:\n{xml_desc}")
        root: ET.Element = ET.fromstring(xml_desc)

        # get info of all disks
        disks: dict = {}
        disks_elements: list[ET.Element] = root.findall("./devices/disk[@type='file']")
        for disk_element in disks_elements:
            source_elem: ET.Element | None = disk_element.find("source")
            target_elem: ET.Element | None = disk_element.find("target")          
            if source_elem is not None and target_elem is not None:
                source_path: str | None = source_elem.get('file')
                if source_path:
                    disk_name: str = os.path.basename(source_path)
                    disks[disk_name] = {
                        "source": source_path,
                        "target": target_elem.get('dev')
                    }
                    logger.debug(f"Disk: {disk_name}, Source: {source_path}, Target: {target_elem.get('dev')}")

        network_source: ET.Element | None = root.find("./devices/interface/source")

        return {
            "name": domain.name(),
            "uuid": domain.UUIDString(),
            "state": info[0],
            "memory": info[2],
            "vcpu_count": info[3],
            "disks": disks,
            "network_name": network_source.get('network') if network_source is not None else None,
        }
    except libvirt.libvirtError as e:
        # Use the specific error code for "not found" to be more robust
        if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
            raise Exception(f"Failed to find VM with name: {vm_name}") from e
        raise e