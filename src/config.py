import os
from typing import Optional


class Config:
    """Application configuration class."""
    
    # Server configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Application metadata
    APP_TITLE: str = os.getenv("APP_TITLE", "KVM Disk Manager")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    
    # Libvirt configuration
    LIBVIRT_URI: str = os.getenv("LIBVIRT_URI", "qemu:///system")
    
    # Disk configuration
    VIRTIO_DISK_PREFIX: str = os.getenv("VIRTIO_DISK_PREFIX", "vd")
    MAX_VIRTIO_DEVICES: int = int(os.getenv("MAX_VIRTIO_DEVICES", "702"))
    QCOW2_DEFAULT_SIZE: str = os.getenv("QCOW2_DEFAULT_SIZE", "1G")
    
    # Timeouts and retries
    DISK_ATTACH_CONFIRM_RETRIES: int = int(os.getenv("DISK_ATTACH_CONFIRM_RETRIES", "5"))
    DISK_ATTACH_CONFIRM_DELAY: float = float(os.getenv("DISK_ATTACH_CONFIRM_DELAY", "0.5"))
    DISK_DETACH_TIMEOUT: int = int(os.getenv("DISK_DETACH_TIMEOUT", "60"))
    DISK_DETACH_POLL_INTERVAL: float = float(os.getenv("DISK_DETACH_POLL_INTERVAL", "0.5"))
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # API configuration
    API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")
    DISK_ROUTER_PREFIX: str = os.getenv("DISK_ROUTER_PREFIX", "/disk")


config = Config()