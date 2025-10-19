"""Start the Skadi FastAPI backend server."""
import uvicorn
from core.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print("🌨️  Starting Skadi Backend API Server")
    print("=" * 60)
    print(f"Host: {settings.host}")
    print(f"Port: {settings.port}")
    print(f"Mode: {settings.default_mode}")
    print(f"Docs: http://{settings.host}:{settings.port}/docs")
    print(f"ML Heatmap: http://{settings.host}:{settings.port}/ml-heatmap/ims-anomaly")
    print("=" * 60)
    
    uvicorn.run(
        "api.app:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info"
    )
