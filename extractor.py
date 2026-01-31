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
import sys
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

Extract:
- name: Product name
- price: Current price (float) and currency (3-letter code)
- compare_at_price: Original price if on sale (optional)
- description: Full product description
- key_features: List of key features/benefits (3-10 items)
- image_urls: ALL product images from <img> tags, JSON-LD, __NEXT_DATA__, __SERVER_DATA__
  * Extract ALL images recursively from nested JSON (colorwayImages, props.pageProps, selectedProduct, productGroups, etc.)
  * Prefer highest resolution (full/max over thumb/mini/square)
  * EXCLUDE: SVG, icons, logos, shipping images, UI elements
  * Extract ALL colorways, not just primary
- video_url: Video URL if available (optional)
- category: EXACT match from Google Product Taxonomy (character-for-character, including ">" symbols)
- brand: Brand name
- colors: List of available colors
- variants: List with variant_type ("size", "color", "fit", "item") and variant_value

Variants - extract ALL from JSON-LD, __NEXT_DATA__, __SERVER_DATA__, HTML select/button:
- LL Bean (__SERVER_DATA__): Extract from product.questions[].answers[].title where type is "COLOR"/"SIZE"/"ITEM". Match SKU media to color variants.
- Nike/Next.js (__NEXT_DATA__): Extract sizes from selectedProduct.sizes[].label or productGroups[].products[].sizes[].label. Extract colors from colorwayImages[].colorDescription with squarishImg/portraitImg.
- Without structured data: Match images to colors by URL/filename patterns (e.g., "dark_brown", "iron", "navy").
- Color variants MUST include image_urls field with matching images.
- Extract ALL variants: if 8 colors and 6 sizes exist, extract all 14 variants.

Category examples:
{sample_categories}

Variant structure example:
[
  {{"variant_type": "size", "variant_value": "10"}},
  {{"variant_type": "size", "variant_value": "11"}},
  {{"variant_type": "color", "variant_value": "Black", "image_urls": ["https://example.com/black.jpg"]}}
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


def _filter_product_images(image_urls: list[str]) -> list[str]:
    """Filter out UI icons, logos, and non-product images."""
    filtered = []
    exclude_keywords = [
        'icon', 'logo', 'header', 'cart', 'user', 'arrow', 'dropdown', 
        'nav', 'loading', 'spinner', 'placeholder', 'decoration', 'ui',
        'resources/images', 'heart-inactive', 'hammer-icon', 'angle-down',
        'circle-user', 'cart-shopping', 'store-location', 'truck', 'shipping',
        'freeshipping', 'delivery', 'badge', 'promo', 'banner', 'advertisement',
        'ad-', 'marketing', 'campaign'
    ]
    
    for url in image_urls:
        url_lower = url.lower()
        
        # Skip SVG files (most are icons/logos)
        if url_lower.endswith('.svg'):
            continue
        
        # Skip if contains exclude keywords (check as whole words, not substrings)
        # Use word boundaries to avoid matching "user" inside "trousers"
        should_exclude = False
        for keyword in exclude_keywords:
            # Match keyword as whole word (with word boundaries) to avoid false positives
            # e.g., "user" should not match inside "trousers"
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, url_lower):
                should_exclude = True
                break
        if should_exclude:
            continue
        
        # Skip API endpoints (not actual images)
        if '/api/' in url_lower:
            continue
        
        # Skip analytics/tracking URLs
        if 'analytics' in url_lower or 'tracking' in url_lower:
            continue
        
        # Skip shipping/delivery related images
        if '/freeshipping/' in url_lower or '/shipping/' in url_lower or '/delivery/' in url_lower:
            continue
        
        # Skip marketing/promo images
        if '/promo/' in url_lower or '/banner/' in url_lower or '/advertisement/' in url_lower or '/marketing/' in url_lower:
            continue
        
        filtered.append(url)
    
    return filtered


def _match_images_to_color_variants(product: Product) -> Product:
    """
    Match all product images to their corresponding color variants.
    
    For each color variant, finds all images in product.image_urls that match
    the color name in the URL/filename and updates the variant's image_urls.
    If a variant already has images from LLM extraction, we merge with additional matches.
    """
    if not product.variants or not product.image_urls:
        return product
    
    # Get all color variants
    color_variants = [v for v in product.variants if v.variant_type.lower() == 'color']
    
    if not color_variants:
        return product
    
    # Create a mapping of color names to their normalized search patterns
    color_patterns = {}
    for variant in color_variants:
        color_name = variant.variant_value.lower().strip()
        # Create search patterns: original name, with underscores, with hyphens, without spaces
        patterns = [
            color_name,
            color_name.replace(' ', '_'),
            color_name.replace(' ', '-'),
            color_name.replace(' ', ''),
            color_name.replace('_', '-'),
            color_name.replace('-', '_'),
        ]
        # Add variations for common color names
        if 'khaki' in color_name:
            if 'light' in color_name:
                patterns.extend(['light_khaki', 'light-khaki', 'lightkhaki'])
            else:
                patterns.extend(['khaki'])
        if 'brown' in color_name:
            if 'dark' in color_name:
                patterns.extend(['dark_brown', 'dark-brown', 'darkbrown'])
            else:
                patterns.extend(['brown'])
        if 'heather' in color_name:
            patterns.append(color_name.replace(' heather', '').replace('heather', ''))
        if 'navy' in color_name:
            patterns.extend(['navy', 'navy_blue', 'navy-blue'])
        if 'blue' in color_name and 'navy' not in color_name:
            patterns.extend(['blue'])
        if 'olive' in color_name:
            patterns.extend(['olive'])
        if 'oyster' in color_name:
            patterns.extend(['oyster'])
        if 'iron' in color_name:
            patterns.extend(['iron'])
        if 'black' in color_name:
            patterns.extend(['black'])
        if 'white' in color_name:
            patterns.extend(['white'])
        
        color_patterns[variant.variant_value] = patterns
    
    # Track which images have been matched
    matched_images = set()
    
    # Match images to colors
    for variant in color_variants:
        if variant.variant_type.lower() != 'color':
            continue
        
        color_name = variant.variant_value
        patterns = color_patterns.get(color_name, [color_name.lower()])
        matching_images = []
        
        # Start with any images already linked by LLM
        existing_images = set(variant.image_urls or [])
        matching_images.extend(existing_images)
        matched_images.update(existing_images)
        
        # Find additional matching images
        for image_url in product.image_urls:
            if image_url in matched_images:
                continue  # Skip if already matched to another color
            
            url_lower = image_url.lower()
            # Check if any pattern matches in the URL (use word boundaries to avoid substring matches)
            matched = False
            for pattern in patterns:
                if not pattern or len(pattern) <= 2:
                    continue
                # Use word boundaries to prevent "black" matching "dark-brown"
                # Check for exact word match or at word boundary
                # Try exact word match first (most specific)
                word_pattern = r'\b' + re.escape(pattern) + r'\b'
                if re.search(word_pattern, url_lower):
                    matching_images.append(image_url)
                    matched_images.add(image_url)
                    matched = True
                    break
                # Fallback: check if pattern appears at start/end of filename segment
                # (e.g., "iron" in "miller-cotton-lyocell-iron.jpg")
                # Make sure it's not a substring match (e.g., "black" in "dark-brown")
                # Check if it's followed/preceded by separator (hyphen, underscore, or dot)
                separator_pattern = r'[-_]' + re.escape(pattern) + r'[-_.]|' + re.escape(pattern) + r'[-_.]'
                if re.search(separator_pattern, url_lower):
                    matching_images.append(image_url)
                    matched_images.add(image_url)
                    matched = True
                    break
            if matched:
                continue
        
        # Update variant with all matching images (deduplicated)
        if matching_images:
            # Remove duplicates while preserving order
            seen = set()
            unique_images = []
            for img in matching_images:
                if img not in seen:
                    seen.add(img)
                    unique_images.append(img)
            variant.image_urls = unique_images
            logger.info(
                f"Matched {len(unique_images)} images to color variant '{color_name}' "
                f"(was {len(existing_images)} before)"
            )
        else:
            logger.warning(
                f"No images matched for color variant '{color_name}' "
                f"(patterns: {patterns[:3]}...)"
            )
    
    return product


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
            
            # Filter out UI icons and non-product images
            if product.image_urls:
                original_count = len(product.image_urls)
                product.image_urls = _filter_product_images(product.image_urls)
                filtered_count = len(product.image_urls)
                if original_count != filtered_count:
                    logger.info(f"Filtered {original_count - filtered_count} non-product images")
            
            # Match all images to color variants
            product = _match_images_to_color_variants(product)
            
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
    Extract products from all HTML files in the specified directory.
    
    Args:
        data_dir: Directory containing HTML files
    
    Returns:
        List of extracted Product objects
    """
    if not data_dir.exists():
        logger.warning(f"Directory not found: {data_dir}")
        return []
    
    # Find all HTML files in the directory
    html_files = list(data_dir.glob("*.html"))
    
    if not html_files:
        logger.warning(f"No HTML files found in {data_dir}")
        return []
    
    logger.info(f"\n{'='*70}")
    logger.info(f"Found {len(html_files)} HTML file(s) to process")
    logger.info(f"{'='*70}")
    
    products = []
    
    for html_file in sorted(html_files):
        logger.info(f"\n{'='*70}")
        logger.info(f"Processing: {html_file.name}")
        logger.info(f"{'='*70}")
        
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
            continue
    
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
    
    # Check for command-line argument (file path)
    if len(sys.argv) > 1:
        # Process single file
        file_path = Path(sys.argv[1])
        
        # Handle both relative and absolute paths
        if not file_path.is_absolute():
            # Try data/ directory first, then current directory
            if (Path("data") / file_path.name).exists():
                file_path = Path("data") / file_path.name
            elif not file_path.exists():
                # If just filename provided, try data/ directory
                file_path = Path("data") / file_path
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            sys.exit(1)
        
        async def extract_single_file():
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            product = await extract_product_from_html(html_content, str(file_path))
            return [product]
        
        products = asyncio.run(extract_single_file())
    else:
        # Process all files in data directory
        products = asyncio.run(extract_all_products())
    
    save_products_to_json(products)
    _print_summary(products)
