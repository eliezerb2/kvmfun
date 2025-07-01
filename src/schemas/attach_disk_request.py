from pydantic import BaseModel, Field, field_validator
from src.utils.validation_utils import validate_vm_name, validate_target_device, validate_qcow2_path
from src.schemas.base_schemas import BaseDiskRequest, BaseVMRequest

class AttachDiskRequest(BaseDiskRequest):
    """Request model for disk attachment."""
    qcow2_path: str = Field(..., description="Path to the QCOW2 disk image", min_length=1)
    
    @field_validator('qcow2_path')
    @classmethod
    def validate_qcow2_path_field(cls, v: str) -> str:
        if not v.endswith('.qcow2'):
            raise ValueError('Disk path must end with .qcow2')
        return v