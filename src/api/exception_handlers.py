import libvirt
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

async def libvirt_error_handler(request: Request, exc: libvirt.libvirtError):
    """
    Custom exception handler for libvirt.libvirtError.
    
    Translates specific libvirt errors into appropriate HTTP responses.
    """
    error_msg = str(exc)
    logger.error(f"Libvirt error caught by handler: {error_msg}")

    if "Domain not found" in error_msg:
        detail = f"The specified VM was not found."
        status_code = status.HTTP_404_NOT_FOUND
    elif "already in use" in error_msg or "Target device" in error_msg:
        detail = error_msg
        status_code = status.HTTP_409_CONFLICT
    else:
        detail = f"An internal libvirt error occurred: {error_msg}"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
    )