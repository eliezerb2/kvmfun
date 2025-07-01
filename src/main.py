import logging
import libvirt
from fastapi import FastAPI
from src.api import disk
from src.utils.config import config
from src.utils.exception_handlers import libvirt_error_handler

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper()),
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=config.APP_TITLE, 
    version=config.APP_VERSION,
    debug=config.DEBUG
)

# Register the custom exception handler for all libvirt errors
app.add_exception_handler(libvirt.libvirtError, libvirt_error_handler)

app.include_router(disk.router, prefix=config.API_PREFIX)

@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "version": config.APP_VERSION}

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {config.HOST}:{config.PORT}, debug={config.DEBUG}")
    uvicorn.run(app, host=config.HOST, port=config.PORT, debug=config.DEBUG)