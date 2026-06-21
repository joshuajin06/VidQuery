from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.summarize import router as summarize_router

app = FastAPI()

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

@app.get("/")
async def root():
  return {"message": "Hello World!"}

