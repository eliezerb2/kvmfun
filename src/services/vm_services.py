from xml.sax.saxutils import escape
import libvirt # type: ignore
import textwrap

def list_vms(conn: libvirt.virConnect) -> list:
    """
    List all virtual machines defined in the libvirt hypervisor.
    
    Args:
        conn (libvirt.virConnect): Connection to the libvirt hypervisor.
        
    Returns:
        list: A list of dictionaries containing VM names and UUIDs.
    """
    vms = []
    domains = conn.listAllDomains()
    for domain in domains:
        vm_info = {
            "name": domain.name(),
            "uuid": domain.UUIDString()
        }
        vms.append(vm_info)
    return vms

def create_vm(vm_name, memory_mb, vcpu_count, disk_path, network_name, conn) -> str:
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
    safe_vm_name = escape(str(vm_name))
    safe_memory_mb = escape(str(memory_mb))
    safe_vcpu_count = escape(str(vcpu_count))
    safe_disk_path = escape(str(disk_path))
    safe_network_name = escape(str(network_name))

    # Define VM XML
    domain_xml = textwrap.dedent(f"""
        <domain type='qemu'>
          <name>{safe_vm_name}</name>
          <memory unit='MiB'>{safe_memory_mb}</memory>
          <vcpu>{safe_vcpu_count}</vcpu>
          <os>
            <type arch='x86_64' machine='pc'>hvm</type>
            <boot dev='hd'/>
          </os>
          <devices>
            <disk type='file' device='disk'>
              <driver name='qemu' type='qcow2'/>
              <source file='{safe_disk_path}'/>
              <target dev='vda' bus='virtio'/>
            </disk>
            <interface type='network'>
              <source network='{safe_network_name}'/>
              <model type='virtio'/>
            </interface>
            <graphics type='vnc' port='-1'/>
          </devices>
        </domain>
    """)

    # Define the VM
    domain = conn.defineXML(domain_xml)
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
        domain = conn.lookupByName(vm_name)
        domain.destroy()  # Stop the VM if it's running
        domain.undefine()  # Remove the VM definition
        return True
    except libvirt.libvirtError as e:
        if 'does not exist' in str(e):
            return False  # VM not found
        raise e  # Re-raise other errors  

def start_vm(vm_name, conn):
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
        domain = conn.lookupByName(vm_name)
        domain.create()
        return True
    except libvirt.libvirtError as e:
        raise Exception(f"Failed to start VM: {e}")
      
def stop_vm(vm_name, conn):
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
    domain = conn.lookupByName(vm_name)
    if domain is None:
        raise Exception("Failed to find VM with name: " + vm_name)
    try:
        domain.shutdown()
        return True
    except libvirt.libvirtError as e:
        raise Exception(f"Failed to stop VM: {e}")