import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import init_db
from app.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema on application startup
    await init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="QuickDrop Rider Payout Dispute Desk Service API",
    version="1.0.0",
    lifespan=lifespan
)

# Include API Routes
app.include_router(router)

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health():
    return {"status": "ok", "service": settings.PROJECT_NAME}

# Mount Ops Dashboard UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "status": "RUNNING",
        "health_url": "/health",
        "docs_url": "/docs"
    }

@app.get("/ops", tags=["Ops UI"])
async def ops_dashboard():
    ui_path = os.path.join(os.path.dirname(__file__), "static", "ops.html")
    if os.path.exists(ui_path):
        return FileResponse(ui_path)
    return {"message": "Ops UI template ready at app/static/ops.html"}
