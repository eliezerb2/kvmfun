from dataclasses import Field
from pydantic import BaseModel, Field, field_validator # type: ignore
import libvirt # type: ignore
from src.utils.validation_utils import validate_size_gb

class CreateVolumeRequest(BaseModel):
    """Request model for creating a new disk volume in a storage pool."""
    size_gb: int = Field(..., description="The size of the volume to create (in GB).")
    
    @field_validator('size_gb')
    @classmethod
    def validate_size_gb(cls, value):
        return validate_size_gb(value)
