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
    # filePaths is a list of the paths to the HTML files that we'd like to process.
    # outputPath is the destination to which we write the processed output.
    filePaths: list[str]
    outputPath: str

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

class Price(BaseModel):
    price: float
    currency: str

    # If a product is on sale, then compare_at_price represents 
    # its original price.
    compare_at_price: float | None = None

class Variant(BaseModel):
    # T-shirts, for example, differ by colour, fit (e.g., traditional vs. slim),
    # size, etc. Power drills, however, are mass-produced products
    # that do not differ from one another. Thus, their product pages
    # would not (likely) yield any Variants.
    key: str | None = None

    # For example, if key is equal to "fit," then 
    # this could be "slim" or "traditional."
    value: str | None = None

    # "Authentic" match-day football kits cost nearly twice
    # as much as replicas, for example, so pricing the Variant
    # is important.
    price: Price
    image_urls: list[str]

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