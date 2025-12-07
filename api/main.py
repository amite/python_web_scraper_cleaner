from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from typing import Optional, Dict, Any
import importlib.util
import sys
import os

# Import the scraper functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import trafilatura_scraper functions
spec = importlib.util.spec_from_file_location("trafilatura_scraper", os.path.join(parent_dir, "trafilatura_scraper.py"))
if spec is None:
    raise ImportError("Could not create module specification for trafilatura_scraper")
if spec.loader is None:
    raise ImportError("Module specification has no loader for trafilatura_scraper")
trafilatura_scraper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trafilatura_scraper)

app = FastAPI(
    title="Trafilatura Scraper API",
    description="API for scraping articles using Trafilatura",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api.log'),
        logging.StreamHandler()
    ]
)

class ScrapeRequest(BaseModel):
    url: str
    include_raw_text: bool = True
    include_metadata: bool = True

class ScrapeResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    text_content: Optional[str] = None
    error: Optional[str] = None
    url: str

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Trafilatura Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "/scrape": "POST - Scrape a URL",
            "/health": "GET - Health check"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "trafilatura-scraper-api"}

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_article(request: ScrapeRequest):
    """Scrape an article from a URL using Trafilatura"""
    try:
        logging.info(f"Received scrape request for URL: {request.url}")

        # Call the scraper function
        article_data, text_content = trafilatura_scraper.scrape_article_with_trafilatura(request.url)

        if article_data is None:
            logging.error(f"Scraping failed for {request.url}: {text_content}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scraping failed: {text_content}"
            )

        logging.info(f"Successfully scraped article from {request.url}")

        # Prepare response
        response_data = {
            "success": True,
            "data": article_data,
            "text_content": text_content if request.include_raw_text else None,
            "error": None,
            "url": request.url
        }

        return response_data

    except Exception as e:
        error_msg = f"Error scraping URL {request.url}: {str(e)}"
        logging.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)