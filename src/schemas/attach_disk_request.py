from pydantic import BaseModel, Field, field_validator
from src.utils.validation_utils import validate_vm_name, validate_target_device, validate_qcow2_path

class AttachDiskRequest(BaseModel):
    """Request model for disk attachment."""
    vm_name: str = Field(..., description="Name of the virtual machine", min_length=1, max_length=255)
    qcow2_path: str = Field(..., description="Path to the QCOW2 disk image", min_length=1)
    target_dev: str = Field(None, description="Target device name (auto-assigned if not provided)")
    
    @field_validator('vm_name')
    @classmethod
    def validate_vm_name_field(cls, v: str) -> str:
        return validate_vm_name(v)
    
    @field_validator('qcow2_path')
    @classmethod
    def validate_qcow2_path_field(cls, v: str) -> str:
        if not v.endswith('.qcow2'):
            raise ValueError('Disk path must end with .qcow2')
        return v
    
    @field_validator('target_dev')
    @classmethod
    def validate_target_dev_field(cls, v: str) -> str:
        return validate_target_device(v)