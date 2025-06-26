import libvirt
import sys
import xml.etree.ElementTree as ET
import re
import os
import subprocess
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# --- Constants ---
QCOW2_DEFAULT_SIZE = "1G"
LIBVIRT_DOMAIN_NAMESPACE = "http://libvirt.org/schemas/domain/1.0"
NAMESPACES = {'lib': LIBVIRT_DOMAIN_NAMESPACE}
VIRTIO_DISK_PREFIX = "vd"
# --- End Constants ---

# Helper functions
def _letters_to_int(s: str) -> int:
    """
    Converts a letter sequence (e.g., 'a', 'aa') to a 0-indexed integer.

    :param s: The letter sequence (e.g., 'a', 'b', 'aa').
    :type s: str
    :returns: The 0-indexed integer representation.
    :rtype: int
    """
    res = 0
    for char in s:
        res = res * 26 + (ord(char) - ord('a') + 1)
    return res - 1

def _int_to_letters(n: int) -> str:
    """
    Converts a 0-indexed integer to a letter sequence (e.g., 0->'a', 26->'aa').
    Used for generating device names like 'vda', 'vdb'.

    :param n: The 0-indexed integer.
    :type n: int
    :returns: The corresponding letter sequence.
    :rtype: str
    """
    res = ""
    while True:
        res = chr(ord('a') + (n % 26)) + res
        n //= 26
        if n == 0:
            break
        n -= 1
    return res

def get_libvirt_domain(vm_name: str) -> tuple[libvirt.virConnect, libvirt.virDomain]:
    """
    Establishes a libvirt connection and looks up a domain by name.

    :param vm_name: The name of the virtual machine.
    :type vm_name: str
    :returns: A tuple containing the libvirt connection object and the domain object.
    :rtype: tuple[libvirt.virConnect, libvirt.virDomain]
    :raises RuntimeError: If connection fails or domain is not found.
    """
    conn = None
    dom = None
    try:
        conn = libvirt.open('qemu:///system')
        if conn is None:
            raise RuntimeError('Failed to open connection to qemu:///system')

        logging.info(f"Looking up domain '{vm_name}'...")
        dom = conn.lookupByName(vm_name)
        logging.info(f"Domain '{vm_name}' found.")
        return conn, dom

    except libvirt.libvirtError as e:
        if "Domain not found" in str(e):
            raise RuntimeError(f"Domain '{vm_name}' not found: {e}") from e
        else:
            raise RuntimeError(f"Error looking up domain '{vm_name}': {e}") from e
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred during domain lookup for '{vm_name}': {e}") from e
    finally:
        # Always close the connection if it was opened.
        if conn:
            conn.close()


def get_next_available_virtio_dev(dom: libvirt.virDomain) -> str:
    """
    Finds the next available VirtIO block device target (e.g., 'vda', 'vdb', 'vdc', 'vdaa', etc.)
    for a given VM by inspecting its current XML configuration.
    It tracks ALL existing 'dev' names regardless of bus type and assigns an unused
    virtio-style name that does not conflict with any existing 'dev' name.

    :param dom: The libvirt Domain object for the VM.
    :type dom: libvirt.virDomain
    :returns: The next available VirtIO device name.
    :rtype: str
    :raises RuntimeError: If no available device name can be found or on other errors.
    """
    try:
        xml_desc = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_LIVE)
        root = ET.fromstring(xml_desc)

        disk_elements = root.findall(".//lib:disk", NAMESPACES)
        used_all_dev_names = set()

        # Regex to capture the letter suffix of a virtio device name
        dev_name_regex = re.compile(rf"^{re.escape(VIRTIO_DISK_PREFIX)}([a-z]+)$")

        for disk in disk_elements:
            target_element = disk.find('lib:target', NAMESPACES)
            if target_element is not None:
                dev = target_element.get('dev')
                if dev: # Check if 'dev' attribute exists and is not empty
                    used_all_dev_names.add(dev)

        logging.debug(f"Currently used device names across all buses: {used_all_dev_names}")

        # Iterate through possible device suffixes (a, b, ..., z, aa, ab, ..., zz)
        # 26 (a-z) + 26*26 (aa-zz) = 702 combinations. This is generally more than enough.
        for i in range(0, 702):
            current_suffix = _int_to_letters(i)
            # Construct the full proposed device name with the configurable prefix
            proposed_dev_name = f"{VIRTIO_DISK_PREFIX}{current_suffix}"

            # Check if the *full proposed VirtIO name* is already used by *any* disk
            # This handles cases where e.g., 'sda' might exist and we want to avoid 'vda'
            if proposed_dev_name not in used_all_dev_names:
                return proposed_dev_name

        raise RuntimeError("No available VirtIO device suffixes up to 'zz'. All possible VirtIO devices are in use or conflict with existing device names.")

    except ET.ParseError as e:
        raise RuntimeError(f"Error parsing VM XML description: {e}") from e
    except libvirt.libvirtError as e:
        raise RuntimeError(f"Error getting VM XML description from libvirt: {e}") from e
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred while determining next available VirtIO device: {e}") from e


def attach_qcow2_disk(dom: libvirt.virDomain, qcow2_path: str, target_dev: str) -> bool:
    """
    Attaches a QCOW2 disk to a running KVM/QEMU VM using libvirt-python.
    Confirms the disk was added after attachment.
    If the disk with the specified path and target device is already attached,
    it logs a warning and skips re-attachment.

    :param dom: The libvirt Domain object for the VM.
    :type dom: libvirt.virDomain
    :param qcow2_path: The full path to the QCOW2 disk image file on the host.
    :type qcow2_path: str
    :param target_dev: The target device name inside the guest (e.g., 'vdb', 'vdc').
                       This value should be pre-determined.
    :type target_dev: str
    :returns: True if attachment and confirmation were successful, or if the disk was already attached.
              False if an unexpected error occurs during the process.
    :rtype: bool
    :raises RuntimeError: If disk attachment fails due to libvirt specific errors
                          (e.g., device in use, permission issues) or if confirmation fails
                          after attempting attachment.
    """
    try:
        logging.info(f"Attempting to attach disk '{qcow2_path}' as '{target_dev}' to VM '{dom.name()}'.")

        # Check if the disk is already attached with the same path and target device
        xml_desc = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_LIVE)
        root = ET.fromstring(xml_desc)
        disk_already_attached = False
        for disk in root.findall(".//lib:disk", NAMESPACES):
            target = disk.find('lib:target', NAMESPACES)
            source = disk.find('lib:source', NAMESPACES)
            # Check for both target device and source file to confirm it's the exact same disk
            if (target is not None and target.get('dev') == target_dev and
                source is not None and source.get('file') == qcow2_path):
                disk_already_attached = True
                break

        if disk_already_attached:
            logging.warning(f"Disk '{qcow2_path}' is already attached as '{target_dev}' to VM '{dom.name()}'. Skipping attachment.")
            return True  # Return True as the desired state (disk attached) is already achieved

        # --- XML Construction using ElementTree ---
        # Define the default namespace for elements created without a prefix
        ET.register_namespace('', LIBVIRT_DOMAIN_NAMESPACE)

        # Create elements without a prefix; ElementTree will use the registered default namespace
        disk_element = ET.Element('disk', type='file', device='disk')
        driver_element = ET.SubElement(disk_element, 'driver', name='qemu', type='qcow2', cache='none')
        source_element = ET.SubElement(disk_element, 'source', file=qcow2_path)
        target_element = ET.SubElement(disk_element, 'target', dev=target_dev, bus='virtio')

        disk_xml = ET.tostring(disk_element, encoding='unicode')
        logging.debug(f"Generated disk XML for attachment:\n{disk_xml}")
        # --- End XML Construction ---

        flags = libvirt.VIR_DOMAIN_ATTACH_DEVICE_LIVE | \
                libvirt.VIR_DOMAIN_ATTACH_DEVICE_PERSIST | \
                libvirt.VIR_DOMAIN_ATTACH_DEVICE_CONFIG

        dom.attachDeviceFlags(disk_xml, flags)
        logging.info(f"Disk attachment command sent for '{qcow2_path}' as '{target_dev}'.")

        # --- Confirmation of disk addition (using explicit namespaces) ---
        max_retries = 5
        retry_delay_seconds = 0.5
        disk_confirmed = False

        for i in range(max_retries):
            try:
                logging.debug(f"Confirming disk addition (attempt {i+1}/{max_retries})...")
                current_xml_desc = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_LIVE)
                current_root = ET.fromstring(current_xml_desc)
                found = False
                for disk in current_root.findall(".//lib:disk", NAMESPACES):
                    target = disk.find('lib:target', NAMESPACES)
                    source = disk.find('lib:source', NAMESPACES)
                    if (target is not None and target.get('dev') == target_dev and
                        target.get('bus') == 'virtio' and # Still confirm it's virtio for the newly added one
                        source is not None and source.get('file') == qcow2_path):
                        found = True
                        break
                if found:
                    disk_confirmed = True
                    break
            except ET.ParseError as e:
                logging.warning(f"Warning: XML parsing error during confirmation: {e}")
            except libvirt.libvirtError as e:
                logging.warning(f"Warning: Libvirt error during confirmation: {e}")

            if not disk_confirmed:
                time.sleep(retry_delay_seconds)

        if not disk_confirmed:
            raise RuntimeError(f"Failed to confirm disk '{qcow2_path}' (as '{target_dev}') was added to VM '{dom.name()}' after {max_retries} attempts.")

        logging.info(f"Successfully confirmed disk '{qcow2_path}' attached as '{target_dev}' to VM '{dom.name()}'.")
        return True

    except libvirt.libvirtError as e:
        # Check if the error is due to a duplicate device (e.g., target_dev already exists with a different source)
        if "duplicate device" in str(e).lower() or "device 'vd" in str(e).lower() and "already in use" in str(e).lower():
            raise RuntimeError(f"Disk attachment failed: Target device '{target_dev}' is already in use by another disk or is conflicting. Please choose a different device. Libvirt error: {e}") from e
        else:
            raise RuntimeError(f"Libvirt error during disk attachment: {e}") from e
    except Exception as e:
        # Catch any other unexpected exceptions, log them, and return False
        logging.error(
            f"An unexpected error occurred while attaching disk '{qcow2_path}' as '{target_dev}' to VM '{dom.name()}': {e}"
        )
        return False


if __name__ == '__main__':
    vm_name = "my_ubuntu_vm"  # Replace with your VM's name
    qcow2_file = "/var/lib/libvirt/images/my_separate_func_disk.qcow2"  # Replace with your disk path

    conn = None
    dom = None

    try:
        conn, dom = get_libvirt_domain(vm_name)

        # Only create the dummy QCOW2 file if it doesn't exist
        if not os.path.isfile(qcow2_file):
            logging.info(f"Creating a dummy QCOW2 file at {qcow2_file} of size {QCOW2_DEFAULT_SIZE} for testing...")
            try:
                subprocess.run(
                    ["qemu-img", "create", "-f", "qcow2", qcow2_file, QCOW2_DEFAULT_SIZE],
                    check=True,  # Raise an exception for non-zero exit codes
                    capture_output=True, # Capture stdout and stderr
                    text=True # Decode stdout and stderr as text
                )
                logging.info("Dummy QCOW2 created successfully.")
            except FileNotFoundError:
                raise RuntimeError(f"'qemu-img' command not found. Please ensure qemu-utils is installed.")
            except subprocess.CalledProcessError as e:
                # Log detailed error from qemu-img
                raise RuntimeError(f"Failed to create dummy QCOW2: Command '{e.cmd}' returned non-zero exit status {e.returncode}.\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}") from e
            except Exception as e:
                raise RuntimeError(f"An unexpected error occurred while creating dummy QCOW2: {e}") from e

        logging.info(f"Determining next available VirtIO device for VM '{vm_name}'...")
        target_device = get_next_available_virtio_dev(dom)

        logging.info(f"Next available VirtIO target device found: {target_device}")

        if attach_qcow2_disk(dom, qcow2_file, target_device):
            logging.info("\nDisk attachment process completed successfully.")
            logging.info("\nNow, log into your VM and verify the disk:")
            logging.info(f"  lsblk")
            logging.info(f"  sudo mkdir -p /mnt/{target_device}_data")
            logging.info(f"  sudo mkfs.ext4 /dev/{target_device} # ONLY IF NEW UNPARTITIONED DISK. Otherwise, use e.g. /dev/{target_device}1")
            logging.info(f"  sudo mount /dev/{target_device} /mnt/{target_device}_data")
            logging.info(f"  # To make persistent, get UUID: sudo blkid /dev/{target_device}")
            logging.info(f"  # Add to /etc/fstab: UUID=... /mnt/{target_device}_data ext4 defaults 0 0")
        else:
            # This branch is now explicitly reached if attach_qcow2_disk returns False
            logging.error("Disk attachment failed (unexpected path or error during attachment).")

    except RuntimeError as e:
        logging.error(f"Operation failed: {e}")
        sys.exit(1)
    except Exception as e:
        logging.exception("An unhandled critical error occurred during the script execution.")
        sys.exit(1)
    finally:
        if conn:
            conn.close()
            logging.info("Libvirt connection closed.")
