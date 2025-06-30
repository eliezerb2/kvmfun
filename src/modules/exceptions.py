"""Custom exception classes for the application."""

class VMNotFound(Exception):
    """Raised when a specified virtual machine is not found."""
    pass

class DiskNotFound(Exception):
    """Raised when a specified disk is not found on a VM."""
    pass