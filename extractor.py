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
    "The category must match exactly - character for character, including the full hierarchical path "
    "with '>' separators (e.g., 'Hardware > Tools', NOT just 'Tools'). "
    "Categories MUST include ALL parent categories separated by ' > '. "
    "Do not add subcategories that don't exist. If you're unsure, use a more general category that definitely exists. "
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
- image_urls: ALL product images from <img> tags, JSON-LD, __NEXT_DATA__, __SERVER_DATA__, and any embedded JSON
  * Extract ALL images recursively from nested JSON structures (search all objects and arrays)
  * CRITICAL: Search window.__SERVER_DATA__, window.__INITIAL_STATE__, window.__NEXT_DATA__, and ALL window.* objects for image data - these often contain the most complete product data
  * CRITICAL: Extract images from ALL sources including:
    - <img> tags with src attributes
    - <meta> tags with property="og:image" or name="og:image" content attributes
    - JSON-LD structured data (schema.org Product images)
    - window.__SERVER_DATA__ and all nested objects/arrays within it
    - window.__INITIAL_STATE__ and all nested objects/arrays within it
    - window.__NEXT_DATA__ and all nested objects/arrays within it
    - Any embedded JSON in <script> tags
  * CRITICAL: Search recursively through ALL nested structures - images may be deeply nested in product objects, variant arrays, question/answer structures, etc.
  * CRITICAL: ALWAYS prefer the LARGEST/BIGGEST product images available - prioritize high resolution over small thumbnails
  * CRITICAL: When multiple image sizes are available, ALWAYS choose the largest dimensions (e.g., prefer larger width/height parameters, prefer higher resolution template names over default/low-resolution ones)
  * CRITICAL: If ONLY thumbnail images are found (e.g., small size parameters), STILL extract them - thumbnails are better than no images
  * CRITICAL: The instruction to "prefer large images" means: if you find both large AND small images, choose large. But if you only find small/thumbnail images, extract them anyway - do NOT skip images just because they are thumbnails
  * For CDN images with size parameters: If you find images with small sizes, extract them. If you can find larger versions by modifying the URL (e.g., changing small size parameters to larger ones), extract the larger version. But if only small sizes exist, extract the small ones
  * Prefer highest resolution variants (full/max/large over thumb/mini/square/small) WHEN AVAILABLE
  * EXCLUDE: SVG files (icons/logos), UI icons, logos, shipping images, UI elements (but NOT product thumbnails - extract product thumbnails if that's all that exists)
  * EXCLUDE: Placeholder images with text like "no image", "no photo", "image not available", "placeholder", "images unavailable"
  * CRITICAL: If you find ANY product images (even small ones, even in meta tags like og:image), extract them - do NOT skip images
  * CRITICAL: Extract images from meta tags (og:image, twitter:image) - these are often the primary product images
  * Extract ALL colorways, not just primary
- video_url: Video URL if available (optional)
- category: EXACT match from Google Product Taxonomy (character-for-character, including ">" symbols)
  * CRITICAL: Categories MUST use the full hierarchical path with ">" separators (e.g., "Hardware > Tools", NOT just "Tools")
  * CRITICAL: The category must include ALL parent categories - never use just a subcategory name
  * CRITICAL: If you see "Tools" in the page, you must find the full path like "Hardware > Tools" in the taxonomy
  * CRITICAL: The category must match EXACTLY from the provided taxonomy examples - character for character
  * CRITICAL: Always use the format "Parent > Child" or "Parent > Child > Grandchild" - never use a single word
- brand: Brand name
- colors: List of available colors
- variants: List with variant_type ("size", "color", "fit", "item") and variant_value

Variants - extract ALL from any available source (JSON-LD, embedded JSON scripts, HTML select/button elements):
- CRITICAL: Extract size variants separately from color variants - they are independent
- CRITICAL: Extract ALL size variants even if they have no images - sizes are independent of images
- CRITICAL: Extract ALL color variants even if they have no images - colors are independent of images
- CRITICAL: Variant JSON structure MUST be consistent - ALL variants must include the same fields:
  * variant_type: string (required)
  * variant_value: string (required)
  * sku: string | null (optional, include if found)
  * price: Price object | null (optional, include if variant-specific pricing found)
  * in_stock: boolean | null (optional, include if availability found)
  * image_urls: array of strings | null (REQUIRED for color variants, MUST be null or [] for size variants)
- CRITICAL: For color variants, the image_urls field is REQUIRED - it must be included in the JSON, even if empty [] or null
- CRITICAL: For size variants, image_urls should be null or omitted - sizes do not have variant-specific images
- Look for variant data in any JSON structures (questions/answers, productGroups, selectedProduct, skus, variants, options, etc.)
- CRITICAL: Search window.__SERVER_DATA__, window.__INITIAL_STATE__, and ALL window.* objects for variant data - these often contain the most complete variant information
- For size variants (REQUIRED for shoes, clothing, etc.):
  * Search __NEXT_DATA__ for: productGroups[].products[].sizes, selectedProduct.sizes, skuList[].size, availableSizes, sizeOptions
  * Search HTML for: <select> with size options, size buttons, size dropdowns, data-size attributes
  * Extract ALL sizes as separate variant objects: {{"variant_type": "size", "variant_value": "8", "image_urls": null}}, {{"variant_type": "size", "variant_value": "9", "image_urls": null}}, etc.
  * Common size formats: numeric (6, 7, 8), half sizes (6.5, 7.5), letter sizes (S, M, L), or combinations
- For color variants: Extract from color arrays, colorwayImages, availableColors, colorVariants, or similar structures
  * CRITICAL: Extract the HUMAN-READABLE color name/description, NOT product codes or SKU identifiers
  * CRITICAL: Extract ALL colors as color variants even if no images are found for them
  * CRITICAL: Each color variant MUST include image_urls field - set to [] if no images found, or to array of image URLs if found
  * Look for color descriptions in: colorDescription, colorName, colorwayDescription, colorwayName, title, name, label fields
  * CRITICAL: Search question/answer structures, colorwayImages, and similar nested data - colors may be in questions[] where type="COLOR" or in colorwayImages[] with descriptive fields
  * CRITICAL: When extracting from colorwayImages or similar nested structures, look for descriptive fields (colorDescription, colorwayDescription, colorName, etc.) rather than product codes or SKU identifiers
  * Prefer descriptive names over product codes or numeric identifiers
  * If you find both a code and a description, use the description for variant_value
  * Only use codes if no human-readable description exists anywhere in the structure
  * Each color should be a separate variant object with variant_type="color", variant_value="[human-readable color name]", and image_urls="[array of image URLs for this color]"

CRITICAL: Match images to color variants using recursive meta-recognition of structured data:
- CRITICAL: Your PRIMARY goal is to assign images to their corresponding color variants - do this FIRST before placing images in the main image_urls array
- CRITICAL: Use recursive meta-recognition to systematically match images to colors:
  1. FIRST: Search window.__SERVER_DATA__ for SKU objects that have both color information AND media/mediaIds arrays
     * In __SERVER_DATA__.product.skus[], find SKUs that belong to a specific color (via questions[].answers[] where type="COLOR")
     * Each SKU has a "media" or "mediaIds" array - these reference images in __SERVER_DATA__.product.media[]
     * Match the SKU's media IDs to entries in the media[] array to get full image URLs
     * Assign those image URLs to the color variant that the SKU belongs to
  2. SECOND: Search for colorwayImages arrays in __NEXT_DATA__ or similar structures
     * Each colorwayImage has a colorDescription/colorwayDescription and associated images (squarishImg, portraitImg, etc.)
     * Match each colorwayImage to its corresponding color variant
  3. THIRD: Match images based on URL patterns (color names in filenames/paths)
  4. FOURTH: Match images based on data structure nesting (images within color-specific objects)
- CRITICAL: Search window.__SERVER_DATA__, window.__INITIAL_STATE__, and ALL window.* objects for color-to-image mappings - these often contain complete variant data
- CRITICAL: Search question/answer structures (questions[], answers[]) for color variant data with associated image URLs - colors and images may be nested in these structures across different sites
- CRITICAL: In __SERVER_DATA__, look for the pattern: product.questions[] (where type="COLOR") → answers[] (with color name) → skus[] (with media/mediaIds) → product.media[] (with full image URLs)
- CRITICAL: Each color variant MUST have unique images - NEVER use the same image URLs for different colors
- CRITICAL: Assign images to color variants using these methods (in priority order):
  1. HIGHEST PRIORITY: If a SKU object has both a color identifier (via questions/answers) AND a media/mediaIds array, assign those images to the matching color variant
  2. HIGH PRIORITY: If image URL contains the color name (e.g., URL with "iron" → "Iron" color, URL with "navy" → "Navy" color), assign it to that color variant
  3. HIGH PRIORITY: If data structure explicitly links images to colors (e.g., colorwayImages[].colorDescription with squarishImg/portraitImg), assign those images to the matching color variant
  4. MEDIUM PRIORITY: If images are nested within a color-specific object/array in the data structure, assign them to that color
  5. MEDIUM PRIORITY: If the current page URL contains a color name (e.g., "/miller-cotton-lyocell-trousers-iron"), assign all images from this page to that specific color variant
- CRITICAL: For each color variant you extract, IMMEDIATELY search for its corresponding images using the methods above - do not wait until the end
- CRITICAL: If an image URL contains a color name in the filename or path (e.g., "iron", "navy", "black", "olive", "khaki", "brown"), ONLY assign it to the matching color variant - do NOT assign it to other colors or the main image_urls
- CRITICAL: If you cannot determine which color an image belongs to after exhaustive search, place it in the main product image_urls array, NOT in any color variant's image_urls
- CRITICAL: Do NOT duplicate images across multiple color variants - each image URL should appear in only ONE place (either one color variant OR the main image_urls array)
- CRITICAL: ALWAYS prefer the LARGEST/BIGGEST images for each color variant - prioritize high resolution images
- CRITICAL: If ONLY thumbnail images are found for a color variant, STILL extract them - thumbnails are better than no images
- CRITICAL: If you find images for ONE color, try to find images for ALL colors using the same pattern - look for URL patterns, data structures, or nested objects that might contain images for other colors
- CRITICAL: Search recursively through ALL nested data structures - variant images may be deeply nested in arrays, objects, or question/answer structures
- CRITICAL: Look for image URL patterns that might indicate different colors (e.g., URLs containing color names, color codes, or variant identifiers)
- CRITICAL: When matching images to colors, examine the URL structure carefully - color names in URLs (like "iron", "navy", "black") are strong indicators of which color variant the image belongs to

CRITICAL: Variant JSON examples:
- Size variant: {{"variant_type": "size", "variant_value": "Large", "sku": null, "price": null, "in_stock": true, "image_urls": null}}
- Color variant with images: {{"variant_type": "color", "variant_value": "Iron", "sku": null, "price": null, "in_stock": null, "image_urls": ["https://example.com/iron-1.jpg", "https://example.com/iron-2.jpg"]}}
- Color variant without images: {{"variant_type": "color", "variant_value": "Navy", "sku": null, "price": null, "in_stock": null, "image_urls": []}}

CRITICAL: Try to find images for each color variant, but if images cannot be found after exhaustive search, STILL include the color variant with image_urls set to [] (empty array, NOT null)
CRITICAL: Always extract ALL available colors as color variants in the variants array, even if you can't find variant-specific images
CRITICAL: If the current page only shows images for one color (e.g., the "Iron" color page), only assign those images to that specific color variant - do NOT assign them to all color variants
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
    """Filter out UI icons, logos, placeholder images, and non-product images."""
    filtered = []
    exclude_keywords = [
        'icon', 'logo', 'header', 'cart', 'user', 'arrow', 'dropdown', 
        'nav', 'loading', 'spinner', 'placeholder', 'decoration', 'ui',
        'resources/images', 'heart-inactive', 'hammer-icon', 'angle-down',
        'circle-user', 'cart-shopping', 'store-location', 'truck', 'shipping',
        'freeshipping', 'delivery', 'badge', 'promo', 'banner', 'advertisement',
        'ad-', 'marketing', 'campaign', 'no-image', 'noimage', 'no-photo', 'nophoto',
        'image-not-available', 'image-not-found', 'not-available', 'unavailable',
        'missing-image', 'missingimage', 'default-image', 'defaultimage'
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
        
        # Skip placeholder images (check URL for placeholder indicators)
        placeholder_patterns = [
            'no.image', 'noimage', 'no-photo', 'nophoto', 'not-available', 'unavailable',
            'missing', 'default-image', 'placeholder-image', 'image-placeholder',
            'no-image', 'image-not-found', 'image-not-available'
        ]
        if any(pattern in url_lower for pattern in placeholder_patterns):
            continue
        
        filtered.append(url)
    
    return filtered


def _deduplicate_variant_images(product: Product) -> None:
    """
    Deduplicate image URLs across variants.
    
    If the same image URL appears in multiple variants, keep it only in the first variant
    that contains it. This ensures each image URL appears in exactly one variant.
    
    Args:
        product: Product object to deduplicate (modified in place)
    """
    seen_image_urls = set()
    removed_count = 0
    
    for variant in product.variants:
        if variant.image_urls:
            # Filter out image URLs that have already been seen in other variants
            original_count = len(variant.image_urls)
            variant.image_urls = [
                url for url in variant.image_urls
                if url not in seen_image_urls
            ]
            
            # Track the URLs we're keeping for this variant
            for url in variant.image_urls:
                seen_image_urls.add(url)
            
            removed = original_count - len(variant.image_urls)
            if removed > 0:
                removed_count += removed
                logger.debug(
                    f"Removed {removed} duplicate image URL(s) from variant "
                    f"{variant.variant_type}={variant.variant_value}"
                )
    
    if removed_count > 0:
        logger.info(f"Deduplicated {removed_count} duplicate image URL(s) across variants")


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
    prompt = EXTRACTION_PROMPT_TEMPLATE.replace('{reduced_html}', reduced_html).replace('{sample_categories}', sample_categories)
    
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
            
            # Check if product extraction returned None
            if product is None:
                error_msg = "LLM returned None instead of a Product object"
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"{error_msg}. Retrying...")
                    continue
                else:
                    raise ValueError(error_msg)
            
            # Filter out UI icons and non-product images
            if product.image_urls:
                original_count = len(product.image_urls)
                product.image_urls = _filter_product_images(product.image_urls)
                filtered_count = len(product.image_urls)
                if original_count != filtered_count:
                    logger.info(f"Filtered {original_count - filtered_count} non-product images")
            
            # Deduplicate image URLs across variants
            _deduplicate_variant_images(product)
            
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
