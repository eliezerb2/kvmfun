import os
from typing import Optional
import os
from typing import Optional


class Config:
    """
    Application configuration class.

    """

    @property
    def HOST(self) -> str: return os.getenv("HOST")

    @property
    def PORT(self) -> int: return int(os.getenv("PORT"))

    @property
    def DEBUG(self) -> bool: return os.getenv("DEBUG").lower() == "true"

    @property
    def APP_TITLE(self) -> str: return os.getenv("APP_TITLE")

    @property
    def APP_VERSION(self) -> str: return os.getenv("APP_VERSION")

    @property
    def LIBVIRT_SERVER_ADDRESS(self) -> str: return os.getenv("LIBVIRT_SERVER_ADDRESS")

    @property
    def LIBVIRT_SERVER_PORT(self) -> str: return os.getenv("LIBVIRT_SERVER_PORT")

    @property
    def LIBVIRT_SSH_USER(self) -> str: return os.getenv("LIBVIRT_SSH_USER")

    @property
    def LIBVIRT_URI(self) -> str:
        return f"qemu+ssh://{self.LIBVIRT_SSH_USER}@{self.LIBVIRT_SERVER_ADDRESS}:{self.LIBVIRT_SERVER_PORT}/system"

    @property
    def VIRTIO_DISK_PREFIX(self) -> str: return os.getenv("VIRTIO_DISK_PREFIX")

    @property
    def MAX_VIRTIO_DEVICES(self) -> int: return int(os.getenv("MAX_VIRTIO_DEVICES"))

    @property
    def QCOW2_DEFAULT_SIZE(self) -> str: return os.getenv("QCOW2_DEFAULT_SIZE")

    @property
    def DISK_ATTACH_CONFIRM_RETRIES(self) -> int: return int(os.getenv("DISK_ATTACH_CONFIRM_RETRIES"))

    @property
    def DISK_ATTACH_CONFIRM_DELAY(self) -> float: return float(os.getenv("DISK_ATTACH_CONFIRM_DELAY"))

    @property
    def DISK_DETACH_TIMEOUT(self) -> int: return int(os.getenv("DISK_DETACH_TIMEOUT"))

    @property
    def DISK_DETACH_POLL_INTERVAL(self) -> float: return float(os.getenv("DISK_DETACH_POLL_INTERVAL"))

    @property
    def LOG_LEVEL(self) -> str: return os.getenv("LOG_LEVEL")

    @property
    def LOG_FORMAT(self) -> str: return os.getenv("LOG_FORMAT")

    @property
    def API_PREFIX(self) -> str: return os.getenv("API_PREFIX")

    @property
    def VM_ROUTER_PREFIX(self) -> str: return os.getenv("VM_ROUTER_PREFIX")

    @property
    def DISK_ROUTER_PREFIX(self) -> str: return os.getenv("DISK_ROUTER_PREFIX")


config = Config()