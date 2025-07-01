from pydantic import BaseModel, Field, field_validator
from src.utils.validation_utils import validate_vm_name, validate_target_device

class DetachDiskRequest(BaseModel):
    """Request model for disk detachment."""
    vm_name: str = Field(..., description="Name of the virtual machine", min_length=1, max_length=255)
    target_dev: str = Field(..., description="Target device name to detach", min_length=1)
    
    @field_validator('vm_name')
    @classmethod
    def validate_vm_name_field(cls, v: str) -> str:
        return validate_vm_name(v)
    
    @field_validator('target_dev')
    @classmethod
    def validate_target_dev_field(cls, v: str) -> str:
        return validate_target_device(v)