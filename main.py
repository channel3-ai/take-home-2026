"""
FastAPI server for product extraction API.
"""

import logging
import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from extractor import extract_product_from_html, extract_all_products
from models import Product

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Product Extraction API",
    description="API for extracting product information from HTML",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ExtractRequest(BaseModel):
    """Request model for HTML extraction."""
    html_content: str


class ExtractResponse(BaseModel):
    """Response model for extracted product."""
    success: bool
    product: Product | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    message: str


# API Routes
@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check."""
    return HealthResponse(
        status="healthy",
        message="Product Extraction API is running"
    )


@app.get("/products", response_model=List[Product])
async def get_all_products():
    """
    Get all extracted products from the JSON file.
    
    Returns:
        List of extracted Product objects
    """
    try:
        json_file = Path("extracted_products.json")
        if not json_file.exists():
            raise HTTPException(
                status_code=404,
                detail="No products found. Please run the extractor first: python extractor.py"
            )
        
        with open(json_file, 'r', encoding='utf-8') as f:
            products_data = json.load(f)
        
        # Convert dicts back to Product models
        products = [Product(**p) for p in products_data]
        return products
        
    except Exception as e:
        logger.error(f"Failed to get products: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
