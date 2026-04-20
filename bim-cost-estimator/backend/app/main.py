"""
FastAPI Application Entry Point
---------------------------------
Main application setup with middleware, CORS, lifecycle events,
and route registration.
"""

import os
# Prevent OpenBLAS/OMP from allocating hundreds of MBs per thread on low RAM instances (Render free tier)
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_CORETYPE"] = "HASWELL" # Prevents illegal instruction crashes on generic VMs


from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from app.config import get_settings
from app.db import init_db
from app.utils import setup_logging, get_logger
from app.api import api_router

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown events."""
    # Startup
    setup_logging()
    logger.info("🚀 BIM Cost & Time Estimator starting up...")
    init_db()
    logger.info("✅ Database initialized")

    # Ensure required directories exist
    settings = get_settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.model_path.mkdir(parents=True, exist_ok=True)
    settings.extracted_data_path.mkdir(parents=True, exist_ok=True)
    settings.processed_data_path.mkdir(parents=True, exist_ok=True)
    settings.reports_path.mkdir(parents=True, exist_ok=True)

    logger.info("✅ All directories verified")
    logger.info(f"📊 API documentation: http://localhost:{settings.backend_port}/docs")

    yield

    # Shutdown
    logger.info("🛑 Application shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="BIM Cost & Time Estimator API",
        description=(
            "AI-Driven BIM Cost & Time Estimator with Explainable Machine Learning, "
            "Graph-Based Scheduling, and Interactive Decision Intelligence Dashboard.\n\n"
            "Built for **Larsen & Toubro (L&T)** — Industry-Grade Production System."
        ),
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ─── CORS Middleware ───
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Request Timing Middleware ───
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        return response

    # ─── Global Exception Handler ───
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception | path={request.url.path} | error={exc}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": str(exc) if settings.debug else "An unexpected error occurred",
            },
        )

    # ─── Register Routes ───
    app.include_router(api_router)

    # ─── Health Check ───
    @app.get("/health", tags=["System"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
        }

    @app.get("/", tags=["System"])
    async def root():
        return {
            "message": "BIM Cost & Time Estimator API",
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/health",
        }

    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
    )
