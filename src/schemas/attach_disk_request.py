from pydantic import Field, field_validator # type: ignore
from src.schemas.base_schemas import BaseVMRequest
from src.utils.validation_utils import validate_qcow2_path

class AttachDiskRequest(BaseVMRequest):
    """Request model for disk attachment."""
    qcow2_path: str = Field(..., description="Path to the QCOW2 disk image", min_length=1)
    
    @field_validator('qcow2_path')
    @classmethod
    def validate_qcow2_path_field(cls, v: str) -> str:
        return validate_qcow2_path(v)