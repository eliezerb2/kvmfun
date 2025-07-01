from pydantic import BaseModel, Field, field_validator
from src.utils.validation_utils import validate_target_device, validate_name

class BaseVMRequest(BaseModel):
    """Base request model for virtual machine operations."""
    vm_name: str = Field(..., description="Name of the virtual machine", min_length=1, max_length=255)

    @field_validator('vm_name')
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Validate the VM name."""
        return validate_name(value, "VM name")

class BaseDiskRequest(BaseVMRequest):
    """Request model for disk detachment."""
    target_dev: str = Field(..., description="Target device name to detach", min_length=1)

    @field_validator('target_dev')
    @classmethod
    def validate_target_dev_field(cls, v: str) -> str:
        return validate_target_device(v)