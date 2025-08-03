from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from .db import init_db
from .api import router as api_router
from .api.websockets import websocket_endpoint
from .queue import job_queue


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database
    await init_db()
    
    # Start job queue consumer
    await job_queue.start_consumer()
    
    yield
    
    # Cleanup on shutdown
    await job_queue.stop_consumer()


app = FastAPI(
    title="Utility Profit Web Scraper API",
    description="AI-powered web form scraping with LangGraph agents",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.websocket("/ws/{client_id}")
async def websocket_handler(websocket: WebSocket, client_id: str):
    await websocket_endpoint(websocket, client_id)


@app.get("/")
async def root():
    return {"message": "Utility Profit Web Scraper API is running!"}


if __name__ == "__main__":
    # Use the fully-qualified module path so the reloader can import it correctly
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
