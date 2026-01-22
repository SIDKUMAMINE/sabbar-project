"""SABBAR - Application principale"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from app.db import get_supabase
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Active le mode debug
app = FastAPI(
    title=settings.APP_NAME,
    description="API SABBAR - Plateforme immobilière avec Agent IA",
    version="1.0.0",
    debug=settings.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    try:
        db = get_supabase()
        logger.info("✓ Supabase connecté")
    except Exception as e:
        logger.error(f"✗ Erreur Supabase: {e}")

@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Routes API
app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)