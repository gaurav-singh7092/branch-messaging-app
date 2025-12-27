import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .database import init_db
from .api import (
    customers_router,
    agents_router,
    conversations_router,
    canned_messages_router,
    search_router,
    websocket_router,
    external_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    await init_db()
    yield


app = FastAPI(
    title="Branch Messaging API",
    description="Customer messaging platform for Branch agents",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS - allow configurable origins for deployment
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    cors_origins = [origin.strip() for origin in cors_origins_env.split(",")]
else:
    # Default origins for development
    cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

# Also allow any Vercel preview URLs
cors_origins.append("https://*.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(customers_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")
app.include_router(canned_messages_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(websocket_router)
app.include_router(external_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "message": "Branch Messaging API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
