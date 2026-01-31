"""
HTML Content Reducer using BeautifulSoup - Removes non-essential content while preserving product information.

This module provides a HTML preprocessing function that removes
fluff (scripts, styles, navigation, boilerplate) while preserving product-relevant
content for LLM processing.
"""

import re
import logging
from bs4 import BeautifulSoup, Comment, NavigableString
from typing import Set, List

logger = logging.getLogger(__name__)

# Boilerplate patterns to remove
BOILERPLATE_PATTERNS = [
    'footer', 'cookie', 'consent', 'banner', 'popup', 'modal',
    'sidebar', 'widget', 'advertisement', 'ad-', 'ads-',
    'social', 'share', 'follow', 'subscribe', 'newsletter',
    'privacy', 'terms', 'legal', 'copyright',
    'analytics', 'tracking', 'pixel', 'beacon',
]

# Product-related patterns to preserve
PRODUCT_INDICATORS = [
    'price', 'product', 'item', 'detail', 'spec', 'feature',
    'description', 'title', 'name', 'image', 'gallery', 'cart',
    'regularprice', 'saleprice', 'compare', 'variant', 'option',
    'sku', 'brand', 'category', 'rating', 'review'
]


def _get_element_attrs(element) -> str:
    """Get combined class, id, and role attributes as lowercase string."""
    attrs = []
    if element.get('class'):
        attrs.extend(element.get('class', []))
    if element.get('id'):
        attrs.append(element.get('id'))
    if element.get('role'):
        attrs.append(element.get('role'))
    return ' '.join(str(attr) for attr in attrs).lower()


def _has_product_indicator(element) -> bool:
    """Check if element has product-related classes/IDs."""
    combined = _get_element_attrs(element)
    return any(indicator in combined for indicator in PRODUCT_INDICATORS)


def _is_obvious_boilerplate(element) -> bool:
    """Check if element is obvious boilerplate (footer, ads, etc.)."""
    combined = _get_element_attrs(element)
    return any(pattern in combined for pattern in BOILERPLATE_PATTERNS)


def _should_keep_element(element, in_body: bool = False) -> bool:
    """Determine if element should be kept based on heuristics."""
    tag_name = element.name.lower() if element.name else ''
    
    # Always keep essential tags
    if tag_name in ['html', 'head', 'body', 'title', 'meta', 'link']:
        return True
    
    # Always keep product-relevant tags
    product_tags = {
        'main', 'article', 'section', 'div', 'span',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'ul', 'ol', 'li', 'dl', 'dt', 'dd',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'img', 'video', 'source', 'picture',
        'strong', 'em', 'b', 'i', 'a',
    }
    if tag_name not in product_tags:
        return False
    
    # In body, be more conservative - keep most content (important for SPAs)
    if in_body:
        # Keep if has product indicators
        if _has_product_indicator(element):
            return True
        
        # Remove only obvious boilerplate
        if _is_obvious_boilerplate(element):
            return False
        
        # Default to keeping in body (conservative approach for SPAs)
        return True
    
    return True


def _remove_inline_handlers(soup: BeautifulSoup):
    """Remove inline event handlers (onclick, onload, etc.) from all elements."""
    for element in soup.find_all(True):
        attrs_to_remove = []
        for attr in list(element.attrs.keys()):
            if attr.startswith('on') and len(attr) > 2:
                attrs_to_remove.append(attr)
        for attr in attrs_to_remove:
            del element[attr]


def _remove_data_uris(soup: BeautifulSoup):
    """Remove data URI images (too large, not useful)."""
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if src and src.startswith('data:image'):
            img.decompose()


def _truncate_large_text(text: str, max_length: int = 10000) -> str:
    """Truncate very large text nodes."""
    if len(text) > max_length:
        logger.warning(f"Truncated large text node ({len(text)} chars)")
        return text[:max_length] + '... [truncated]'
    return text


def _process_body_content(body):
    """
    Process body content with cascading keep logic.
    If parent is kept, keep all children unless obviously boilerplate.
    """
    elements_to_remove = []
    
    def should_remove_element(element):
        """Check if element should be removed, considering parent context."""
        # If element has product indicators, always keep
        if _has_product_indicator(element):
            return False
        
        # If element is obvious boilerplate, remove it
        if _is_obvious_boilerplate(element):
            # But check if it has product children
            has_product_child = any(
                _has_product_indicator(child) 
                for child in element.find_all(True)
            )
            return not has_product_child
        
        # Default: keep (conservative approach)
        return False
    
    # First pass: mark elements for removal
    for element in body.find_all(True):
        if element in elements_to_remove:
            continue
        
        if should_remove_element(element):
            elements_to_remove.append(element)
    
    # Remove marked elements
    for element in elements_to_remove:
        element.decompose()


def _process_head_content(head):
    """Process head content - keep essential tags only."""
    elements_to_remove = []
    
    for element in head.find_all(True):
        tag_name = element.name.lower() if element.name else ''
        
        # Keep essential head tags
        if tag_name in ['meta', 'link', 'title', 'script']:
            # Keep JSON-LD scripts, remove others
            if tag_name == 'script':
                script_type = element.get('type', '').lower()
                if script_type != 'application/ld+json':
                    elements_to_remove.append(element)
            continue
        
        # Remove everything else in head
        elements_to_remove.append(element)
    
    for element in elements_to_remove:
        element.decompose()


def reduce_html(html_content: str, max_size_mb: float = 5.0) -> str:
    """
    Reduce HTML content by removing non-essential elements using BeautifulSoup.
    
    This function removes scripts, styles, navigation, boilerplate, and other
    non-product content while preserving product information, structured data
    (JSON-LD), and semantic HTML structure.
    
    Args:
        html_content: Raw HTML string to process
        max_size_mb: Maximum input size in MB (for memory management)
    
    Returns:
        Cleaned HTML string with only product-relevant content
    
    Raises:
        ValueError: If input exceeds max_size_mb
    
    Performance:
        - Processes up to 5MB HTML efficiently
        - Handles malformed HTML gracefully
    """
    # Validate input size
    size_mb = len(html_content.encode('utf-8')) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise ValueError(
            f"HTML content ({size_mb:.2f}MB) exceeds maximum size ({max_size_mb}MB)"
        )
    
    if not html_content or not html_content.strip():
        return html_content
    
    try:
        # Parse HTML with BeautifulSoup (handles malformed HTML gracefully)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Remove script tags (except JSON-LD and product data scripts)
        for script in soup.find_all('script'):
            script_type = script.get('type', '').lower()
            script_id = script.get('id', '').lower()
            script_content = script.string or ''
            
            # Keep JSON-LD scripts
            if script_type == 'application/ld+json':
                continue
            
            # Keep application/json scripts (often contain product/variant data in SPAs)
            if script_type == 'application/json':
                continue
            
            # Keep __NEXT_DATA__ and similar product data scripts
            if '__next_data__' in script_id or 'product' in script_id or 'variant' in script_id:
                continue
            
            # Keep __SERVER_DATA__ scripts (LL Bean and similar sites)
            if '__SERVER_DATA__' in script_content or '__SERVER_DATA__' in script_id:
                continue
            
            # Remove all other scripts
            script.decompose()
        
        # Remove style and noscript tags
        for tag in soup.find_all(['style', 'noscript']):
            tag.decompose()
        
        # Remove inline event handlers
        _remove_inline_handlers(soup)
        
        # Remove data URI images
        _remove_data_uris(soup)
        
        # Process body content with cascading keep logic
        body = soup.find('body')
        if body:
            _process_body_content(body)
        
        # Process head content (keep meta, link, title, JSON-LD scripts)
        head = soup.find('head')
        if head:
            _process_head_content(head)
        
        # Truncate large text nodes (but preserve script content, especially JSON)
        for text_node in soup.find_all(string=True):
            if isinstance(text_node, NavigableString) and text_node.parent:
                # Don't truncate script content (especially JSON data like __NEXT_DATA__)
                parent = text_node.parent
                if parent and parent.name == 'script':
                    script_type = parent.get('type', '').lower()
                    script_id = parent.get('id', '').lower()
                    # Preserve JSON scripts completely (they contain product data including images)
                    if script_type in ['application/json', 'application/ld+json'] or '__next_data__' in script_id:
                        continue
                truncated = _truncate_large_text(str(text_node))
                text_node.replace_with(truncated)
        
        # Get cleaned HTML
        result = str(soup)
        
        # Post-processing cleanup
        result = re.sub(r'\n\s*\n\s*\n+', '\n\n', result)  # Max 2 consecutive newlines
        result = re.sub(r'[ \t]+', ' ', result)  # Collapse spaces
        result = result.strip()
        
        # Ensure we have basic HTML structure
        if not result.startswith('<'):
            result = f'<html><head></head><body>{result}</body></html>'
        
        return result
        
    except Exception as e:
        logger.error(f"Error reducing HTML: {e}", exc_info=True)
        # Return original if reduction fails (fail-safe)
        return html_content


def get_reduction_stats(original: str, reduced: str) -> dict:
    """
    Get statistics about HTML reduction.
    
    Returns:
        Dictionary with size reduction statistics
    """
    original_size = len(original.encode('utf-8'))
    reduced_size = len(reduced.encode('utf-8'))
    reduction_pct = (1 - reduced_size / original_size) * 100 if original_size > 0 else 0
    
    return {
        'original_size_bytes': original_size,
        'reduced_size_bytes': reduced_size,
        'reduction_percent': round(reduction_pct, 2),
        'bytes_saved': original_size - reduced_size,
    }
