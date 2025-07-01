from pydantic import BaseModel, Field, field_validator
from src.utils.validation_utils import validate_qcow2_path
from src.schemas.base_schemas import BaseVMRequest

class CreateVMRequest(BaseVMRequest):
    """Request model for vm creation."""
    memory_mb: int = Field(..., description="Memory size in MB", ge=128, le=65536)
    vcpu_count: int = Field(..., description="Number of virtual CPUs", ge=1, le=64)
    disk_path: str = Field(..., description="Path to the QCOW2 disk image", min_length=1)
    network_name: str = Field(..., description="Name of the network to attach the VM to", min_length=1)
    
    # The ge/le constraints on memory_mb Field are sufficient; no custom validator needed.


    @field_validator('disk_path')
    @classmethod
    def validate_disk_path_field(cls, v: str) -> str:
        return validate_qcow2_path(v)

    @field_validator('network_name')
    @classmethod
    def validate_network_name_field(cls, v: str) -> str:
        if not v.isidentifier():
            raise ValueError('Network name must be a valid identifier')
        return v

    
