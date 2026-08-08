"""Main FastAPI Application Entrypoint."""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.routes import router as pdf_router

app = FastAPI(
    title="High-Fidelity Automated PDF Text-Field Editor",
    description="Deterministic PDF text editor that preserves all non-target content, images, logos, vectors, and geometry.",
    version="1.0.0"
)

# Include API routes
app.include_router(pdf_router)

# Mount static web UI files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    """Serves the primary web interface."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "PDF Text-Field Editor API is online. Access /docs for API documentation."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
