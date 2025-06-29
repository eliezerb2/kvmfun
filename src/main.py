import logging
from fastapi import FastAPI
from src.api import disk_routes
from src.config import config

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

app.include_router(disk_routes.router, prefix=config.API_PREFIX)

@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "version": config.APP_VERSION}

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {config.HOST}:{config.PORT}, debug={config.DEBUG}")
    uvicorn.run(app, host=config.HOST, port=config.PORT, debug=config.DEBUG)