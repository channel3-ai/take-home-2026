# test_Product_Retrieval.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastapi.testclient import TestClient
from backend.api import app
from backend.models import Product

client = TestClient(app)

def test_get_products():
    response = client.get("/products")
    
    assert response.status_code == 200
    
    data = response.json()
    assert "version" in data
    assert "products" in data
    assert isinstance(data["products"], list)
    assert len(data["products"]) > 0
    
    # Test first product has required fields
    product = data["products"][0]
    assert "name" in product
    assert "price" in product
    assert "description" in product
    assert "key_features" in product
    assert "image_urls" in product
    assert "category" in product
    assert "brand" in product
    assert "colors" in product
    assert "variants" in product

def test_get_products_schema():
    response = client.get("/products")
    product = response.json()["products"][0]
    
    # Validate product structure matches Pydantic model
    assert isinstance(product["name"], str)
    assert isinstance(product["price"], dict)
    assert isinstance(product["description"], str)
    assert isinstance(product["key_features"], list)
    assert isinstance(product["image_urls"], list)
    assert isinstance(product["category"], dict)  # Category is an object
    assert isinstance(product["brand"], str)
    assert isinstance(product["colors"], list)
    assert isinstance(product["variants"], list)