from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.ingest import router as ingest_router
from routers.summarize import router as summarize_router
from services.vector_store import init_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
  init_schema()
  yield


app = FastAPI(lifespan=lifespan)

origins = [
  "http://localhost:8000"
]

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],       # List of allowed origins
  allow_credentials=True,     # Allow cookies and authentication headers
  allow_methods=["*"],        # Allow all HTTP methods (GET, POST, etc.)
  allow_headers=["*"],   
)

app.include_router(summarize_router)
app.include_router(ingest_router)


@app.api_route("/", methods=["GET", "HEAD"])
async def root():
  return {"message": "Hello World!"}

