import os
import logging
from fastapi import FastAPI
from src.api import disk_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
HOST = os.getenv("HOST", "0.0.0.0")

app = FastAPI(
    title="KVM Disk Manager", 
    version="1.0.0",
    debug=DEBUG
)

app.include_router(disk_routes.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {HOST}:{PORT}, debug={DEBUG}")
    uvicorn.run(app, host=HOST, port=PORT, debug=DEBUG)