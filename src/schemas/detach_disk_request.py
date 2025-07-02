from pydantic import BaseModel, Field, field_validator # type: ignore
from src.utils.validation_utils import validate_target_device
from src.schemas.base_schemas import BaseVMRequest

class DetachDiskRequest(BaseVMRequest):
    """Request model for disk detachment."""
    target_dev: str = Field(..., description="Target device name to detach", min_length=1)

    @field_validator('target_dev')
    @classmethod
    def validate_target_dev_field(cls, v: str) -> str:
        return validate_target_device(v)