"""
Product extraction from HTML using HTML reducer + LLM.

This module extracts structured Product data from HTML files by:
1. Reducing HTML size using HTML_reducer (removes fluff, preserves product info)
2. Using LLM to extract structured data into Product schema
3. Automatically logging token usage via ai.responses wrapper
"""

import asyncio
import logging
import json
import re
from pathlib import Path
from typing import List

from HTML_reducer import reduce_html
import ai
from models import Product, VALID_CATEGORIES

logger = logging.getLogger(__name__)

# Constants
MODEL = "openai/gpt-5-nano"
MAX_RETRIES = 2

SYSTEM_MESSAGE = (
    "You are a product data extraction expert. Extract structured product information "
    "from e-commerce pages. CRITICAL: For the category field, you MUST use an EXACT "
    "category name from Google Product Taxonomy that exists in the taxonomy file. "
    "The category must match exactly - character for character. Do not add subcategories "
    "that don't exist. If you're unsure, use a more general category that definitely exists. "
    "Do not invent new category paths. Ensure all required fields are populated."
)

EXTRACTION_PROMPT_TEMPLATE = """Extract product information from this e-commerce product page HTML.

{reduced_html}

Extract the following information:
- name: Product name
- price: Current price (float) and currency (3-letter code like USD, GBP, EUR)
- compare_at_price: Original price if on sale (optional, can be None)
- description: Full product description
- key_features: List of key features/benefits (3-10 items)
- image_urls: List of ALL full-resolution image URLs (extract from img tags and JSON-LD)
- video_url: Video URL if available (optional, can be None)
- category: MUST be an EXACT match from Google Product Taxonomy. The category must exist EXACTLY as written in the taxonomy.
- brand: Brand name
- colors: List of available colors
- variants: List of variants with variant_type (e.g., "size", "color", "fit") and variant_value (e.g., "Large", "Red")

CRITICAL for category: 
- You MUST use an exact category name that exists in Google Product Taxonomy
- The category must match EXACTLY - character for character, including spaces and ">" symbols
- Do NOT create new category paths or add subcategories that don't exist
- If unsure, use a more general category that definitely exists
- Common top-level categories include: Hardware, Apparel & Accessories, Electronics, Home & Garden, etc.

Sample valid categories (these are examples - find the best match for this product):
{sample_categories}

For variants, structure them as objects with variant_type and variant_value fields. Example:
[
  {{"variant_type": "size", "variant_value": "Large"}},
  {{"variant_type": "color", "variant_value": "Red"}}
]"""


def _get_category_samples(max_examples: int = 25) -> str:
    """Get diverse category examples from taxonomy for LLM prompt."""
    samples = []
    top_level_seen = set()
    
    # Get top-level categories
    for category in sorted(VALID_CATEGORIES):
        top_level = category.split(' > ')[0]
        if top_level not in top_level_seen:
            samples.append(category)
            top_level_seen.add(top_level)
            if len(top_level_seen) >= 10:
                break
    
    # Add specific subcategories
    for category in sorted(VALID_CATEGORIES):
        if ' > ' in category and category not in samples:
            samples.append(category)
            if len(samples) >= max_examples:
                break
    
    return '\n'.join(f'- "{cat}"' for cat in samples[:max_examples])


def _calculate_reduction_stats(original: str, reduced: str) -> tuple[int, int, float]:
    """Calculate HTML reduction statistics."""
    original_size = len(original.encode('utf-8'))
    reduced_size = len(reduced.encode('utf-8'))
    reduction_pct = 100 * (1 - reduced_size / original_size) if original_size > 0 else 0
    return original_size, reduced_size, reduction_pct


def _is_category_validation_error(error: str) -> bool:
    """Check if error is a category validation error."""
    return "Category" in error and "is not a valid category" in error


def _extract_invalid_category(error: str) -> str | None:
    """Extract invalid category from error message."""
    match = re.search(r"Category '([^']+)'", error)
    return match.group(1) if match else None


async def extract_product_from_html(html_content: str, file_path: str = "") -> Product:
    """
    Extract product information from HTML using reducer + LLM.
    
    The ai.responses wrapper automatically calls _log_usage to log
    token usage and cost extrapolation for each query.
    
    Args:
        html_content: Raw HTML string
        file_path: Optional file path for logging
    
    Returns:
        Product object with extracted data
    
    Raises:
        ValueError: If product extraction fails
    """
    logger.info(f"Reducing HTML for {file_path or 'input'}...")
    reduced_html = reduce_html(html_content)
    
    original_size, reduced_size, reduction_pct = _calculate_reduction_stats(html_content, reduced_html)
    logger.info(
        f"HTML reduced: {original_size:,} → {reduced_size:,} bytes "
        f"({reduction_pct:.1f}% reduction)"
    )
    
    sample_categories = _get_category_samples()
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(
        reduced_html=reduced_html,
        sample_categories=sample_categories
    )
    
    logger.info("Extracting product data with LLM...")
    
    for attempt in range(MAX_RETRIES):
        try:
            product = await ai.responses(
                model=MODEL,
                input=[
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": prompt}
                ],
                text_format=Product
            )
            
            logger.info(f"✓ Successfully extracted product: {product.name}")
            return product
            
        except Exception as e:
            error_str = str(e)
            
            if _is_category_validation_error(error_str):
                invalid_cat = _extract_invalid_category(error_str)
                if invalid_cat and attempt < MAX_RETRIES - 1:
                    logger.warning(f"Invalid category '{invalid_cat}' detected. Retrying with correction...")
                    prompt += (
                        f"\n\nCORRECTION: The category '{invalid_cat}' does not exist in the taxonomy. "
                        "Please find a valid category. For reference, valid categories start with "
                        "top-level categories like: Hardware, Apparel & Accessories, Electronics, "
                        "Home & Garden, etc. Use a more general category if the specific one doesn't exist."
                    )
                    continue
            
            logger.error(f"✗ Failed to extract product: {e}", exc_info=True)
            raise ValueError(f"Product extraction failed: {e}") from e
    
    raise ValueError("Product extraction failed after retries")


async def extract_all_products(data_dir: Path = Path("data")) -> List[Product]:
    """
    Extract products from HTML files in the specified directory.
    
    Args:
        data_dir: Directory containing HTML files
    
    Returns:
        List of extracted Product objects
    """
    html_file = data_dir / "llbean.html"
    
    if not html_file.exists():
        logger.warning(f"File not found: {html_file}")
        return []
    
    logger.info(f"\n{'='*70}")
    logger.info(f"Processing: {html_file.name}")
    logger.info(f"{'='*70}")
    
    products = []
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        product = await extract_product_from_html(html_content, str(html_file))
        products.append(product)
        
        logger.info(f"✓ Successfully extracted: {product.name}")
        logger.info(f"  Category: {product.category.name}")
        logger.info(f"  Brand: {product.brand}")
        logger.info(f"  Price: {product.price.price} {product.price.currency}")
        logger.info(f"  Images: {len(product.image_urls)} found")
        logger.info(f"  Variants: {len(product.variants)} found")
        
    except Exception as e:
        logger.error(f"✗ Failed to extract from {html_file.name}: {e}", exc_info=True)
    
    return products


def save_products_to_json(products: List[Product], output_file: Path = Path("extracted_products.json")) -> None:
    """
    Save extracted products to JSON file.
    
    Args:
        products: List of Product objects
        output_file: Path to output JSON file
    """
    products_data = [p.model_dump() for p in products]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(products_data, f, indent=2, default=str)
    
    logger.info(f"Saved {len(products)} products to {output_file}")


def _print_summary(products: List[Product]) -> None:
    """Print extraction summary statistics."""
    logger.info(f"\n{'='*70}")
    logger.info("EXTRACTION SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Total products extracted: {len(products)}")
    
    if products:
        logger.info("\nProducts by category:")
        categories = {}
        for p in products:
            cat = p.category.name
            categories[cat] = categories.get(cat, 0) + 1
        for cat, count in sorted(categories.items()):
            logger.info(f"  {cat}: {count}")
    else:
        logger.warning("No products were extracted successfully")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    products = asyncio.run(extract_all_products())
    save_products_to_json(products)
    _print_summary(products)
