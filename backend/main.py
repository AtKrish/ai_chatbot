import sys
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Ensure backend is in PYTHONPATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Import router
from backend.routes.chat import router as chat_router
from services.cache_service import stats as cache_stats

app = FastAPI(title="AI Support API")

# Include routes
app.include_router(chat_router)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend")), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint (health check)
@app.get("/")
def root():
    return {"message": "API is working"}

@app.get("/cache/stats")
def get_cache_stats():
    return cache_stats()

@app.get("/widget")
def widget():
    return FileResponse(os.path.join(BASE_DIR, "frontend", "index.html"))

# Favicon (optional)
@app.get("/favicon.ico")
async def favicon():
    favicon_path = os.path.join(BASE_DIR, "frontend", "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return {"message": "No favicon found"}
