import os

class Config:
    """
    Application configuration class.

    """
   
    @property
    def LIBVIRT_STORAGE_POOL(self) -> str: return os.getenv("LIBVIRT_STORAGE_POOL", "default")
    
    @property
    def TEST_VM_VCPUS(self) -> int: return int(os.getenv("TEST_VM_VCPUS", "1"))
    
    @property
    def TEST_VM_MEMORY_MB(self) -> int: return int(os.getenv("TEST_VM_MEMORY_MB", "1024"))
   
    @property
    def TEST_VM_NAME(self) -> str: return os.getenv("TEST_VM_NAME", "ubuntu-test-vm")
    
    @property
    def TEST_VM_NETWORK_NAME(self) -> str: return os.getenv("TEST_VM_NETWORK_NAME", "default")
    
    @property
    def TEST_OS_VOLUME_NAME(self) -> str: return os.getenv("TEST_OS_VOLUME_NAME", f"e2e-test-os-vol.qcow2")
    
    @property
    def TEST_DATA_VOLUME_NAME(self) -> str: return os.getenv("TEST_DATA_VOLUME_NAME", f"e2e-test-data-vol.qcow2")
    
    @property
    def TEST_DATA_VOLUME_SIZE_GB(self) -> int: return int(os.getenv("TEST_DATA_VOLUME_SIZE_GB", "1"))
    
    @property
    def TEST_CLEANUP_ON_START(self) -> bool: return (os.getenv("TEST_CLEANUP_ON_START", "true").lower() == "true")
    
    @property
    def TEST_CLEANUP_ON_END(self) -> bool: return (os.getenv("TEST_CLEANUP_ON_END", "true").lower() == "true")

config = Config()