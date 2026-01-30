from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from models import Product
from pathlib import Path
import json

BASE_DIR = Path(__file__).parent
PRODUCTS_FILE = BASE_DIR / "products.json"

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProductResponse(BaseModel):
    version: str
    products: list[Product]

@app.get("/products", response_model=ProductResponse)
async def get_products():
    with open(PRODUCTS_FILE, "r") as f:
        data = json.load(f)
    return data