from pydantic import BaseModel, Field, field_validator # type: ignore
from src.utils.validation_utils import validate_name

class BaseVMRequest(BaseModel):
    """Base request model for virtual machine operations."""
    vm_name: str = Field(..., description="Name of the virtual machine", min_length=1, max_length=255)

    @field_validator('vm_name')
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Validate the VM name."""
        return validate_name(value, "VM name")
    
class BaseVolumeRequest(BaseModel):
    """Base request model for volume operations."""
    pool_name: str = Field(..., description="The name of the storage pool where the volume is located (e.g., 'default').")
    volume_name: str = Field(..., description="The name of the volume to delete.")

    @field_validator('pool_name')
    @classmethod
    def validate_name(cls, value):
        return validate_name(value, "Storage pool name")

    @field_validator('volume_name')
    @classmethod
    def validate_volume_name(cls, value):
        return validate_name(value, "Volume name")