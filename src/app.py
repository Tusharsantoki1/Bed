"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import create_all_tables
from .routes import (
    auth,
    company,
    dashboard,
    invoices,
    parties,
    superadmin,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (use Alembic migrations in production).
    create_all_tables()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Multi-tenant GST billing backend for the mobile billing app.",
    lifespan=lifespan,
)

# CORS — Bearer-token auth, so credentials are not needed.
origins = settings.cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"])
def root():
    return {"name": settings.PROJECT_NAME, "status": "ok"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


api = settings.API_PREFIX
app.include_router(auth.router, prefix=api)
app.include_router(company.router, prefix=api)
app.include_router(parties.router, prefix=api)
app.include_router(invoices.router, prefix=api)
app.include_router(dashboard.router, prefix=api)
app.include_router(superadmin.router, prefix=api)
