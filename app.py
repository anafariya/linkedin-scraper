# app.py
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from dotenv import load_dotenv

from api.routes import router as api_router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LinkedIn Profile Scraper API",
    description="API for scraping LinkedIn profiles with user credentials",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("NEXTJS_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple API key authentication
API_KEY = os.getenv("API_KEY")

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

# Include API routes
app.include_router(api_router, prefix="/api", dependencies=[Depends(verify_api_key)])

@app.get("/")
async def root():
    return {"message": "LinkedIn Scraper API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=int(os.getenv("PORT", "8000")), 
        reload=True
    )