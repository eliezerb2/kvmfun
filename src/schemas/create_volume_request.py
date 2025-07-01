from dataclasses import Field
from pydantic import BaseModel, Field, field_validator
import libvirt
import logging
from src.utils.validation_utils import validate_name, validate_size_gb

class CreateVolumeRequest(BaseModel):
    """Request model for creating a new disk volume in a storage pool."""
    pool_name: str = Field(..., description="The name of the storage pool where the volume will be created (e.g., 'default').")
    volume_name: str = Field(..., description="The name of the volume to create.")
    size_gb: int = Field(..., description="The size of the volume to create (in GB).")
    
    @field_validator('pool_name')
    @classmethod
    def validate_name(cls, value):
        return validate_name(value, "Storage pool name")

    @field_validator('volume_name')
    @classmethod
    def validate_volume_name(cls, value):
        return validate_name(value, "Volume name")

    @field_validator('size_gb')
    @classmethod
    def validate_size_gb(cls, value):
        return validate_size_gb(value)
