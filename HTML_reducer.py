"""
HTML Content Reducer - Removes non-essential content while preserving product information.

This module provides a HTML preprocessing function that removes
fluff (scripts, styles, navigation, boilerplate) while preserving product-relevant
content for LLM processing.
"""

import re
import logging
from html.parser import HTMLParser
from typing import List, Set, Optional, Tuple
from collections import deque

logger = logging.getLogger(__name__)


def _escape_html(text: str) -> str:
    """Escape HTML special characters in text content."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))


# Compiled regex patterns for performance (compiled once at module level)
COMMENT_PATTERN = re.compile(r'<!--.*?-->', re.DOTALL)
INLINE_HANDLER_PATTERN = re.compile(r'\s+(on\w+)\s*=\s*["\'][^"\']*["\']', re.IGNORECASE)
DATA_URI_PATTERN = re.compile(r'data:image/[^;]+;base64,[A-Za-z0-9+/=]+', re.IGNORECASE)
LARGE_TEXT_PATTERN = re.compile(r'.{10001,}', re.DOTALL)  # Text nodes > 10KB

# Boilerplate class/id patterns (case-insensitive matching)
BOILERPLATE_PATTERNS = [
    r'header', r'footer', r'nav', r'navigation', r'menu',
    r'cookie', r'consent', r'banner', r'popup', r'modal',
    r'sidebar', r'widget', r'advertisement', r'ad-', r'ads-',
    r'social', r'share', r'follow', r'subscribe', r'newsletter',
    r'search', r'filter', r'breadcrumb', r'pagination',
    r'privacy', r'terms', r'legal', r'copyright',
    r'analytics', r'tracking', r'pixel', r'beacon',
    r'icon', r'logo', r'branding', r'decoration',
]

# Product-related patterns (to preserve)
PRODUCT_PATTERNS = [
    r'product', r'item', r'goods', r'merchandise',
    r'price', r'cost', r'pricing', r'buy', r'purchase',
    r'description', r'details', r'specification', r'specs',
    r'feature', r'benefit', r'variant', r'option',
    r'image', r'photo', r'picture', r'gallery',
    r'video', r'media', r'content', r'main',
]

# Compile patterns for faster matching
BOILERPLATE_REGEX = re.compile('|'.join(f'({pattern})' for pattern in BOILERPLATE_PATTERNS), re.IGNORECASE)
PRODUCT_REGEX = re.compile('|'.join(f'({pattern})' for pattern in PRODUCT_PATTERNS), re.IGNORECASE)


class HTMLReducer(HTMLParser):
    """
    Custom HTML parser that identifies and filters non-essential content.
    
    Uses a two-pass approach:
    1. Parse and mark elements to keep/remove
    2. Build cleaned HTML string
    """
    
    def __init__(self):
        super().__init__()
        self.keep_stack: deque = deque()  # Track which elements to keep
        self.output_parts: List[str] = []  # Build output HTML
        self.current_tag: Optional[str] = None
        self.current_attrs: List[Tuple[str, Optional[str]]] = []
        self.in_script = False
        self.in_style = False
        self.in_noscript = False
        self.script_type: Optional[str] = None
        self.json_ld_buffer: List[str] = []
        self.depth = 0
        self.skip_depth = -1  # Depth at which we started skipping
        self.in_body = False  # Track if we're inside body tag
        self.in_head = False  # Track if we're inside head tag
        
    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        """Process opening tags."""
        self.depth += 1
        self.current_tag = tag.lower()
        self.current_attrs = attrs
        attrs_dict = dict(attrs)
        
        # Track body/head state
        if tag.lower() == 'body':
            self.in_body = True
        elif tag.lower() == 'head':
            self.in_head = True
        
        # Check if we're in a skip zone
        if self.skip_depth >= 0:
            return
        
        # Handle script tags specially (preserve JSON-LD)
        if tag == 'script':
            self.in_script = True
            self.script_type = attrs_dict.get('type', '').lower()
            if self.script_type == 'application/ld+json':
                # Preserve JSON-LD scripts - track in keep_stack for proper closing
                self.json_ld_buffer = []
                self.keep_stack.append(True)  # Track so we can handle closing properly
                self._write_tag(tag, attrs)
                return
            else:
                # Skip other scripts
                self.skip_depth = self.depth
                return
        
        # Skip style and noscript tags
        if tag == 'style':
            self.in_style = True
            self.skip_depth = self.depth
            return
        
        if tag == 'noscript':
            self.in_noscript = True
            self.skip_depth = self.depth
            return
        
        # CASCADING KEEP LOGIC: In body, if parent is kept, keep all children
        # This ensures nested product content (like prices) is preserved even in generic containers
        if self.in_body and self.keep_stack and self.keep_stack[-1]:
            # We're inside a kept element in body - keep all children unless obviously boilerplate
            class_attr = attrs_dict.get('class', '') or ''
            id_attr = attrs_dict.get('id', '') or ''
            role_attr = attrs_dict.get('role', '') or ''
            combined_attrs = f'{class_attr} {id_attr} {role_attr}'.lower()
            
            # Only skip obvious boilerplate (not nav/header that might contain product content)
            # Be more specific - only filter out footer, cookie consent, ads, etc.
            obvious_boilerplate = ['footer', 'cookie', 'consent', 'banner', 'popup', 'modal',
                                  'sidebar', 'widget', 'advertisement', 'ad-', 'ads-',
                                  'social', 'share', 'follow', 'subscribe', 'newsletter']
            
            is_obvious_boilerplate = any(bp in combined_attrs for bp in obvious_boilerplate)
            
            if not is_obvious_boilerplate:
                # Keep this child element (cascading keep)
                self.keep_stack.append(True)
                self._write_tag(tag, attrs)
                return
        
        # Check if element should be removed based on heuristics
        should_keep = self._should_keep_element(tag, attrs_dict)
        
        if should_keep:
            self.keep_stack.append(True)
            self._write_tag(tag, attrs)
        else:
            # Don't push to keep_stack for skipped elements - track with skip_depth only
            self.skip_depth = self.depth
    
    def handle_endtag(self, tag: str):
        """Process closing tags."""
        tag_lower = tag.lower()
        
        # Track body/head state
        if tag_lower == 'body':
            self.in_body = False
        elif tag_lower == 'head':
            self.in_head = False
        
        # Check if we're closing a skipped element
        is_closing_skipped = self.skip_depth >= 0 and self.skip_depth == self.depth
        
        # Handle script/style/noscript closing
        if tag_lower == 'script':
            if self.in_script and self.script_type == 'application/ld+json' and not is_closing_skipped:
                # Write JSON-LD content (closing tag will be written in normal handling)
                if self.json_ld_buffer:
                    self.output_parts.append(''.join(self.json_ld_buffer))
            self.in_script = False
            self.script_type = None
            self.json_ld_buffer = []
            if is_closing_skipped:
                self.skip_depth = -1
                self.depth -= 1
                return
        elif tag_lower == 'style':
            self.in_style = False
            if is_closing_skipped:
                self.skip_depth = -1
        elif tag_lower == 'noscript':
            self.in_noscript = False
            if is_closing_skipped:
                self.skip_depth = -1
        
        # If closing a skipped element, reset skip_depth and decrement depth
        if is_closing_skipped:
            self.skip_depth = -1
            self.depth -= 1
            return
        
        # Handle other closing tags (only if we're not in a skip zone)
        if self.skip_depth >= 0:
            # We're inside a skipped element, just decrement
            self.depth -= 1
            return
        
        # Normal closing tag - check if we kept this element
        if self.keep_stack:
            was_kept = self.keep_stack.pop()
            if was_kept:
                self.output_parts.append(f'</{tag}>')
        else:
            # No entry in stack means this tag was never opened in our tracking
            # (might be malformed HTML or self-closing tag)
            pass
        
        self.depth -= 1
        self.current_tag = None
    
    def handle_data(self, data: str):
        """Process text content."""
        # Skip if we're in a skip zone
        if self.skip_depth >= 0:
            return
        
        # Handle JSON-LD script content
        if self.in_script and self.script_type == 'application/ld+json':
            self.json_ld_buffer.append(data)
            return
        
        # CRITICAL FIX: In body, preserve text content if parent is kept
        # This ensures price text like "$349" is preserved even in generic containers
        if self.in_body:
            # If we're inside a kept element in body, preserve the text
            if self.keep_stack and self.keep_stack[-1]:
                # Truncate very large text nodes (> 10KB)
                if len(data) > 10000:
                    data = data[:10000] + '... [truncated]'
                    logger.warning(f"Truncated large text node ({len(data)} chars)")
                
                # Escape HTML special characters in text
                escaped = _escape_html(data)
                self.output_parts.append(escaped)
                return
        
        # Skip if not keeping current element
        if not self.keep_stack or not self.keep_stack[-1]:
            return
        
        # Truncate very large text nodes (> 10KB)
        if len(data) > 10000:
            data = data[:10000] + '... [truncated]'
            logger.warning(f"Truncated large text node ({len(data)} chars)")
        
        # Escape HTML special characters in text
        escaped = _escape_html(data)
        self.output_parts.append(escaped)
    
    def handle_entityref(self, name: str):
        """Handle named entities like &amp;."""
        if self.skip_depth < 0 and self.keep_stack and self.keep_stack[-1]:
            self.output_parts.append(f'&{name};')
    
    def handle_charref(self, name: str):
        """Handle numeric entities like &#123;."""
        if self.skip_depth < 0 and self.keep_stack and self.keep_stack[-1]:
            self.output_parts.append(f'&#{name};')
    
    def _should_keep_element(self, tag: str, attrs: dict) -> bool:
        """
        Determine if an element should be kept based on heuristics.
        More conservative in body - preserves more content for SPAs.
        
        Returns True if element should be preserved, False if it should be removed.
        """
        # Always keep essential tags
        essential_tags = {'html', 'head', 'body', 'title', 'meta', 'link'}
        if tag in essential_tags:
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
        if tag not in product_tags:
            return False
        
        # In body, be more conservative - keep most content (important for SPAs)
        if self.in_body:
            class_attr = attrs.get('class', '') or ''
            id_attr = attrs.get('id', '') or ''
            role_attr = attrs.get('role', '') or ''
            combined_attrs = f'{class_attr} {id_attr} {role_attr}'.lower()
            
            # CRITICAL: Keep elements with product-related classes/IDs (price, product, etc.)
            # This ensures elements like <span class="regularPrice">$349</span> are preserved
            product_indicators = ['price', 'product', 'item', 'detail', 'spec', 'feature', 
                                 'description', 'title', 'name', 'image', 'gallery', 'cart',
                                 'regularprice', 'saleprice', 'compare', 'variant', 'option',
                                 'sku', 'brand', 'category', 'rating', 'review']
            if any(indicator in combined_attrs for indicator in product_indicators):
                return True
            
            # Remove only obvious boilerplate (footer, cookie consent, ads, etc.)
            # NOTE: We don't filter "header" or "nav" here because they can contain product content in SPAs
            # The cascading keep logic handles this more intelligently
            obvious_boilerplate = ['footer', 'cookie', 'consent', 'banner', 'popup', 'modal',
                                  'sidebar', 'widget', 'advertisement', 'ad-', 'ads-',
                                  'social', 'share', 'follow', 'subscribe', 'newsletter']
            
            is_obvious_boilerplate = any(bp in combined_attrs for bp in obvious_boilerplate)
            
            if is_obvious_boilerplate:
                # But keep if it has product-related content
                if not PRODUCT_REGEX.search(combined_attrs):
                    return False
            
            # In body, default to keeping content (conservative approach for SPAs)
            # This ensures nested content like prices in generic containers are preserved
            return True
        
        # In head, be more selective
        if self.in_head:
            # Keep meta, link, title, etc. (already handled above)
            return True
        
        # For elements outside body/head (shouldn't happen, but be safe)
        class_attr = attrs.get('class', '') or ''
        id_attr = attrs.get('id', '') or ''
        role_attr = attrs.get('role', '') or ''
        combined_attrs = f'{class_attr} {id_attr} {role_attr}'.lower()
        
        # Remove if matches boilerplate patterns
        if BOILERPLATE_REGEX.search(combined_attrs):
            if not PRODUCT_REGEX.search(combined_attrs):
                return False
        
        # Keep if matches product patterns
        if PRODUCT_REGEX.search(combined_attrs):
            return True
        
        # Keep main content areas
        if role_attr in ['main', 'article', 'content']:
            return True
        
        # Keep images and videos (product media)
        if tag in {'img', 'video', 'source', 'picture'}:
            return True
        
        # Default: keep if we're not sure (conservative approach)
        return True
    
    def _write_tag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        """Write opening tag to output."""
        attrs_str = ' '.join(
            f'{name}="{value}"' if value else name
            for name, value in attrs
        )
        if attrs_str:
            self.output_parts.append(f'<{tag} {attrs_str}>')
        else:
            self.output_parts.append(f'<{tag}>')
    
    def get_output(self) -> str:
        """Get the cleaned HTML string."""
        return ''.join(self.output_parts)


def remove_comments(html: str) -> str:
    """Remove HTML comments using regex."""
    return COMMENT_PATTERN.sub('', html)


def remove_inline_handlers(html: str) -> str:
    """Remove inline event handlers (onclick, onload, etc.)."""
    return INLINE_HANDLER_PATTERN.sub('', html)


def remove_data_uris(html: str) -> str:
    """Remove data URI images (too large, not useful)."""
    return DATA_URI_PATTERN.sub('', html)


def truncate_large_text_nodes(html: str) -> str:
    """Truncate very large text content."""
    # This is a simple approach - in practice, would need to parse more carefully
    return LARGE_TEXT_PATTERN.sub(lambda m: m.group(0)[:10000] + '... [truncated]', html)


def reduce_html(html_content: str, max_size_mb: float = 5.0) -> str:
    """
    Reduce HTML content by removing non-essential elements.
    
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
        - Processes up to 5MB HTML in < 100ms
        - Memory efficient - processes in single pass
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
        # Step 1: Extract JSON-LD scripts before processing (preserve them)
        json_ld_scripts = []
        json_ld_pattern = re.compile(
            r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            re.DOTALL | re.IGNORECASE
        )
        for match in json_ld_pattern.finditer(html_content):
            script_content = match.group(1).strip()
            if script_content:
                json_ld_scripts.append(script_content)
        
        # Step 2: Quick regex-based removals (fast, before parsing)
        cleaned = html_content
        
        # Fix common malformed attributes (like stylesheet'" which breaks parsing)
        cleaned = re.sub(r'(\w+)"\s*["\']', r'\1="', cleaned)  # Fix double quotes in attributes
        
        # Remove comments
        cleaned = remove_comments(cleaned)
        
        # Remove inline event handlers
        cleaned = remove_inline_handlers(cleaned)
        
        # Remove data URI images (too large)
        cleaned = remove_data_uris(cleaned)
        
        # Step 3: Parse and filter HTML structure
        parser = HTMLReducer()
        
        try:
            parser.feed(cleaned)
            parser.close()
        except Exception as e:
            # Continue even if parsing fails partially
            logger.warning(f"HTML parsing encountered issues: {e}")
            # Try to get partial output
            try:
                parser.close()
            except:
                pass
        
        # Step 4: Get cleaned output
        result = parser.get_output()
        
        # Step 5: Ensure JSON-LD scripts are included
        if json_ld_scripts and 'application/ld+json' not in result:
            # Find where to insert JSON-LD (before </head> or at end of head)
            if '</head>' in result:
                json_ld_html = '\n'.join(
                    f'<script type="application/ld+json">{script}</script>'
                    for script in json_ld_scripts
                )
                result = result.replace('</head>', f'{json_ld_html}</head>')
            elif '<head>' in result:
                json_ld_html = '\n'.join(
                    f'<script type="application/ld+json">{script}</script>'
                    for script in json_ld_scripts
                )
                result = result.replace('<head>', f'<head>{json_ld_html}')
        
        # Step 6: Ensure we have complete HTML structure
        has_head_close = '</head>' in result
        has_body = '<body' in result.lower() or '</body>' in result.lower()
        has_html_close = '</html>' in result
        
        # If we don't have body but have head, try to extract body from original
        if not has_body:
            # Try to find body content in original HTML (before cleaning)
            body_match = re.search(
                r'<body[^>]*>(.*?)</body>',
                html_content,
                re.DOTALL | re.IGNORECASE
            )
            if body_match:
                body_content = body_match.group(1)
                # Pre-process body content
                body_cleaned = remove_comments(body_content)
                body_cleaned = remove_inline_handlers(body_cleaned)
                body_cleaned = remove_data_uris(body_cleaned)
                
                # Create a parser for body content
                body_parser = HTMLReducer()
                try:
                    body_parser.feed(body_cleaned)
                    body_parser.close()
                except Exception as e:
                    logger.warning(f"Body parsing encountered issues: {e}")
                    try:
                        body_parser.close()
                    except:
                        pass
                
                reduced_body = body_parser.get_output()
                if reduced_body.strip():
                    # Insert body before closing html or at end
                    if '</head>' in result:
                        result = result.replace('</head>', f'</head><body>{reduced_body}</body>')
                    else:
                        result += f'<body>{reduced_body}</body>'
                    has_body = True
        
        # Ensure proper closing tags
        if '<head>' in result and not has_head_close:
            result += '</head>'
        
        # Ensure body exists
        if not has_body and '</head>' in result:
            result = result.replace('</head>', '</head><body></body>')
            has_body = True
        
        # Ensure html closing tag
        if '<html>' in result or result.startswith('<html'):
            if not has_html_close:
                if has_body:
                    # Check if body is closed
                    if '</body>' not in result:
                        result += '</body>'
                else:
                    # Add empty body if missing
                    if '</head>' in result:
                        result = result.replace('</head>', '</head><body></body>')
                    else:
                        result += '<body></body>'
                result += '</html>'
        
        # Step 7: Post-processing cleanup
        # Remove excessive whitespace (but preserve structure)
        result = re.sub(r'\n\s*\n\s*\n+', '\n\n', result)  # Max 2 consecutive newlines
        result = re.sub(r'[ \t]+', ' ', result)  # Collapse spaces
        result = result.strip()
        
        # Final validation - ensure we have basic HTML structure
        if not result.startswith('<'):
            # Wrap in minimal HTML if needed
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
