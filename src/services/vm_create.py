import libvirt
import os
import textwrap
from xml.etree import ElementTree
from xml.sax.saxutils import escape

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
        <domain type='kvm'>
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