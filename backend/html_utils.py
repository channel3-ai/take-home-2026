"""
HTML Utilities for extracting media links and cleaning HTML content.
This module provides functions to process HTML files by extracting media links
(images, videos) and removing unnecessary noise for cleaner AI model inputs.
"""

from bs4 import BeautifulSoup
from typing import Dict, List, Tuple
from urllib.parse import urljoin
import re


def extract_media_links(html_content: str, base_url: str = "") -> Dict[str, List[str]]:
    """
    Extract all media links (images and videos) from HTML content.
    
    Args:
        html_content: The HTML content as a string.
        base_url: Base URL to resolve relative URLs (optional).
        
    Returns:
        A dictionary with 'images' and 'videos' keys containing lists of URLs.
        
    Example:
        >>> media = extract_media_links(html_text, "https://nike.com")
        >>> print(media['images'])
        >>> print(media['videos'])
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    media_links = {
        'images': [],
        'videos': []
    }
    
    # Extract image URLs:
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            # Resolve relative URLs:
            if base_url:
                src = urljoin(base_url, src)
            media_links['images'].append(src)
    
    # Extract images from picture elements:
    for picture in soup.find_all('picture'):
        for source in picture.find_all('source'):
            srcset = source.get('srcset')
            if srcset:
                # srcset can have multiple URLs, so we extract them:
                urls = [url.strip().split()[0] for url in srcset.split(',')]
                for url in urls:
                    if base_url:
                        url = urljoin(base_url, url)
                    if url not in media_links['images']:
                        media_links['images'].append(url)
    
    # Extract video URLs:
    for video in soup.find_all('video'):
        # Check video src attribute:
        src = video.get('src')
        if src:
            if base_url:
                src = urljoin(base_url, src)
            media_links['videos'].append(src)
        
        # Check source elements within video:
        for source in video.find_all('source'):
            src = source.get('src')
            if src:
                if base_url:
                    src = urljoin(base_url, src)
                if src not in media_links['videos']:
                    media_links['videos'].append(src)
    
    # Extract from data attributes and background images:
    for element in soup.find_all(True):
        # Check data attributes for image URLs:
        for attr_name, attr_value in element.attrs.items():
            if attr_value and isinstance(attr_value, str):
                if 'image' in attr_name.lower() or 'src' in attr_name.lower():
                    if any(ext in attr_value.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.mp4', '.webm', '.mov']):
                        resolved_url = urljoin(base_url, attr_value) if base_url else attr_value
                        if any(ext in attr_value.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']):
                            if resolved_url not in media_links['images']:
                                media_links['images'].append(resolved_url)
                        elif any(ext in attr_value.lower() for ext in ['.mp4', '.webm', '.mov']):
                            if resolved_url not in media_links['videos']:
                                media_links['videos'].append(resolved_url)
    
    return media_links


def remove_html_noise(html_content: str, preserve_text: bool = True) -> str:
    """
    Remove unnecessary noise from HTML while preserving meaningful content.
    Removes: scripts, styles, comments, meta tags (except description and keywords),
    analytics code, and unnecessary attributes.
    
    Args:
        html_content: The HTML content as a string.
        preserve_text: If True, extracts and returns all text content (default: True).
        
    Returns:
        Cleaned HTML content as a string.
        
    Example:
        >>> cleaned_html = remove_html_noise(html_text)
        >>> print(cleaned_html)
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script tags:
    for script in soup.find_all('script'):
        script.decompose()
    
    # Remove style tags:
    for style in soup.find_all('style'):
        style.decompose()
    
    # Remove comments:
    for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
        comment.extract()
    
    # Remove noscript tags:
    for noscript in soup.find_all('noscript'):
        noscript.decompose()
    
    # Remove iframe tags (except those with important content):
    for iframe in soup.find_all('iframe'):
        iframe.decompose()
    
    # Keep only useful meta tags:
    for meta in soup.find_all('meta'):
        name = meta.get('name', '').lower()
        property_attr = meta.get('property', '').lower()
        
        # Remove most meta tags except description and keywords:
        if name not in ['description', 'keywords'] and property_attr not in ['og:description', 'og:title']:
            meta.decompose()
    
    for tag in soup.find_all(True):
        # Remove event handlers:
        for attr in list(tag.attrs.keys()):
            if attr.startswith('on') or attr.startswith('data-') or attr in ['class', 'id', 'style']:
                del tag[attr]
    
    return str(soup.prettify())


def extract_text_content(html_content: str, remove_extra_whitespace: bool = True) -> str:
    """
    Extract clean text content from HTML, removing all tags and formatting.
    
    Args:
        html_content: The HTML content as a string
        remove_extra_whitespace: If True, collapses multiple whitespaces (default: True)
        
    Returns:
        Plain text content
        
    Example:
        >>> text = extract_text_content(html_text)
        >>> print(text)
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style tags before extracting text:
    for script in soup.find_all(['script', 'style']):
        script.decompose()
    
    # Get text content:
    text = soup.get_text()
    
    if remove_extra_whitespace:
        # Replace multiple spaces with single space:
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace from lines:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
    
    return text.strip()


def create_cleaned_html(html_content: str, include_media_info: bool = False, 
                       base_url: str = "") -> Tuple[str, Dict]:
    """
    Create a comprehensive cleaned version of HTML with optional media information..
    
    Args:
        html_content: The HTML content as a string.
        include_media_info: If True, includes extracted media links (default: False).
        base_url: Base URL to resolve relative URLs.
        
    Returns:
        A tuple of (cleaned_html, metadata_dict) where metadata_dict contains
        'media' key if include_media_info is True.
        
    Example:
        >>> cleaned_html, metadata = create_cleaned_html(html_text, include_media_info=True)
        >>> print(metadata['media']['images'])
    """
    metadata = {}
    
    if include_media_info:
        metadata['media'] = extract_media_links(html_content, base_url)
    
    cleaned_html = remove_html_noise(html_content)
    
    return cleaned_html, metadata


def get_html_summary(html_content: str) -> Dict[str, any]:
    """
    Generate a summary of HTML content including title, description, media count, etc.
    
    Args:
        html_content: The HTML content as a string.
        
    Returns:
        A dictionary containing summary information.
        
    Example:
        >>> summary = get_html_summary(html_text)
        >>> print(f"Title: {summary['title']}")
        >>> print(f"Images: {summary['image_count']}")
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    summary = {
        'title': soup.title.string if soup.title else 'No title',
        'description': '',
        'image_count': len(soup.find_all('img')),
        'video_count': len(soup.find_all('video')),
        'link_count': len(soup.find_all('a')),
        'text_length': len(extract_text_content(html_content)),
    }
    
    # Get meta description:
    meta_description = soup.find('meta', attrs={'name': 'description'})
    if meta_description:
        summary['description'] = meta_description.get('content', '')
    
    return summary
