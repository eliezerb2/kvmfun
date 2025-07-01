import libvirt
import os

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