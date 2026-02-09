from typing import Any
from pathlib import Path
from pydantic import BaseModel, field_validator

# The following code brings in all of the categories against which 
# I must match the Product objects that I am hydrating.
CATEGORIES_FILE: Path = Path(__file__).parent / "categories.txt"
VALID_CATEGORIES: set = set()
if CATEGORIES_FILE.exists():
    with open(CATEGORIES_FILE, "r") as f:
        for line in f:
            line: str = line.strip()
            if line and not line.startswith("#"):
                VALID_CATEGORIES.add(line)

class ProductExtractionRequest(BaseModel):
    paths: list[str]

# This class represents a category from Google's Product Taxonomy:
# https://www.google.com/basepages/producttype/taxonomy.en-US.txt
class Category(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name_exists(cls, v: str) -> str:
        if v not in VALID_CATEGORIES:
            raise ValueError(f"Category '{v}' is not a valid category in categories.txt.")
        return v
    
class Variant(BaseModel):
    # The idea is that this is simply a list of key-value pairs.
    # We want to gather as much information as possible from the HTML
    # pages. Given that websites differ in the amount of product information
    # that they expose via their HTML code, I'm intentionally making this
    # "schemaless" so that we can add distinguishing factors as we are 
    # able to do so.
    configurations: dict[str, str] | None = None

class Price(BaseModel):
    price: float
    currency: str

    # If a product is on sale, then compare_at_price represents 
    # the original price.
    compare_at_price: float | None = None

# This is the final product schema that I need to output. 
class Product(BaseModel):
    name: str
    price: Price
    description: str
    key_features: list[str]
    image_urls: list[str]
    video_url: str | None
    category: Category
    brand: str
    colors: list[str]
    variants: list[Variant]

class ProductList(BaseModel):
    products: list[Product]