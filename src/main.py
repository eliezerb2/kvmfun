from fastapi import FastAPI
from src.api import disk_routes

app = FastAPI(title="KVM Disk Manager", version="1.0.0")

app.include_router(disk_routes.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)