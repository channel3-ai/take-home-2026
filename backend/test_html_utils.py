"""
Test script to verify HTML utilities work correctly.
Run this to ensure all functions are working properly.
"""

import sys
from pathlib import Path
from html_utils import (
    extract_media_links,
    remove_html_noise,
    extract_text_content,
    create_cleaned_html,
    get_html_summary
)


def test_extract_media():
    """Test media extraction"""
    print("\n📸 Testing media extraction...")
    
    html = """
    <html>
        <body>
            <img src="photo1.jpg" alt="Photo 1">
            <img src="https://example.com/photo2.png">
            <picture>
                <source srcset="image1.webp 1x, image2.webp 2x">
            </picture>
            <video src="video.mp4"></video>
            <video>
                <source src="video2.webm" type="video/webm">
            </video>
        </body>
    </html>
    """
    
    media = extract_media_links(html)
    
    assert len(media['images']) >= 3, "Should find at least 3 images"
    assert len(media['videos']) >= 2, "Should find at least 2 videos"
    
    print(f"  ✓ Found {len(media['images'])} images")
    print(f"  ✓ Found {len(media['videos'])} videos")
    return True


def test_remove_noise():
    """Test HTML noise removal"""
    print("\n🧹 Testing HTML noise removal...")
    
    html = """
    <html>
        <head>
            <script>alert('test');</script>
            <style>body { color: red; }</style>
            <meta name="keywords" content="test">
            <meta name="tracking" content="analytics">
        </head>
        <body onclick="doSomething()">
            <p>Important content</p>
            <!-- This is a comment -->
        </body>
    </html>
    """
    
    cleaned = remove_html_noise(html)
    
    # Check that noise was removed
    assert '<script>' not in cleaned, "Scripts should be removed"
    assert '<style>' not in cleaned, "Styles should be removed"
    assert '<!--' not in cleaned, "Comments should be removed"
    assert 'onclick' not in cleaned, "Event handlers should be removed"
    
    # Check that content is preserved
    assert 'Important content' in cleaned, "Content should be preserved"
    
    print("  ✓ Scripts removed")
    print("  ✓ Styles removed")
    print("  ✓ Comments removed")
    print("  ✓ Content preserved")
    return True


def test_extract_text():
    """Test text extraction"""
    print("\n📝 Testing text extraction...")
    
    html = """
    <html>
        <body>
            <h1>Title</h1>
            <p>This is a paragraph.</p>
            <p>This is another paragraph.</p>
            <script>var x = 1;</script>
            <style>p { color: blue; }</style>
        </body>
    </html>
    """
    
    text = extract_text_content(html)
    
    assert 'Title' in text, "Title should be in text"
    assert 'paragraph' in text, "Paragraph text should be extracted"
    assert 'var x' not in text, "Script content should not be in text"
    assert '{' not in text, "CSS should not be in text"
    
    print(f"  ✓ Extracted {len(text)} characters")
    print(f"  ✓ Scripts excluded")
    print(f"  ✓ Styles excluded")
    return True


def test_get_summary():
    """Test summary generation"""
    print("\n📊 Testing summary generation...")
    
    html = """
    <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="This is a test page">
        </head>
        <body>
            <img src="img1.jpg">
            <img src="img2.png">
            <video src="video.mp4"></video>
            <a href="link1">Link 1</a>
            <a href="link2">Link 2</a>
            <p>This page has content for testing purposes.</p>
        </body>
    </html>
    """
    
    summary = get_html_summary(html)
    
    assert summary['title'] == 'Test Page', "Title should be extracted"
    assert summary['image_count'] == 2, "Should count 2 images"
    assert summary['video_count'] == 1, "Should count 1 video"
    assert summary['link_count'] == 2, "Should count 2 links"
    assert summary['text_length'] > 0, "Should have text content"
    
    print(f"  ✓ Title: {summary['title']}")
    print(f"  ✓ Images: {summary['image_count']}")
    print(f"  ✓ Videos: {summary['video_count']}")
    print(f"  ✓ Links: {summary['link_count']}")
    print(f"  ✓ Text length: {summary['text_length']}")
    return True


def test_create_cleaned_html():
    """Test comprehensive cleaning"""
    print("\n✨ Testing comprehensive cleaning...")
    
    html = """
    <html>
        <body>
            <img src="photo.jpg">
            <script>console.log('test');</script>
            <p>Content here</p>
        </body>
    </html>
    """
    
    cleaned_html, metadata = create_cleaned_html(
        html, 
        include_media_info=True,
        base_url="https://example.com"
    )
    
    assert '<script>' not in cleaned_html, "Scripts should be removed"
    assert 'Content here' in cleaned_html, "Content should be preserved"
    assert 'media' in metadata, "Metadata should include media"
    assert len(metadata['media']['images']) > 0, "Should find images"
    
    print(f"  ✓ Cleaned HTML generated")
    print(f"  ✓ Metadata included")
    print(f"  ✓ Media found: {len(metadata['media']['images'])} images")
    return True


def test_with_real_file():
    """Test with actual HTML file if it exists"""
    print("\n🧪 Testing with real HTML file...")
    
    html_file = Path("../data/rawData/nike.html")
    
    if not html_file.exists():
        print(f"  ⚠ Skipped (file not found: {html_file})")
        return True
    
    try:
        html = html_file.read_text(encoding="utf-8")
        
        # Test each function
        media = extract_media_links(html, base_url="https://www.nike.com")
        summary = get_html_summary(html)
        text = extract_text_content(html)
        cleaned, metadata = create_cleaned_html(html, include_media_info=True)
        
        print(f"  ✓ Successfully processed {html_file.name}")
        print(f"    - Found {len(media['images'])} images, {len(media['videos'])} videos")
        print(f"    - Title: {summary['title']}")
        print(f"    - Extracted {len(text)} characters of text")
        print(f"    - Reduced size by {100 * (1 - len(cleaned)/len(html)):.1f}%")
        
        return True
    except Exception as e:
        print(f"  ✗ Error processing file: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("=" * 80)
    print("🧪 HTML Utilities Test Suite")
    print("=" * 80)
    
    tests = [
        test_extract_media,
        test_remove_noise,
        test_extract_text,
        test_get_summary,
        test_create_cleaned_html,
        test_with_real_file,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except AssertionError as e:
            print(f"  ✗ Test failed: {e}")
            results.append(False)
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append(False)
    
    # Summary:
    print("\n" + "=" * 80)
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print(f"✅ All {total} tests passed!")
        return 0
    else:
        print(f"⚠️ {passed}/{total} tests passed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
