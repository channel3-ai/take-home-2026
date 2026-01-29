import ai
import asyncio
import logging
import json
import numpy as np
from pathlib import Path
from pydantic import BaseModel
from models import Product, VALID_CATEGORIES
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from bs4 import BeautifulSoup

async def hello_world():
    class HelloWorldResponse(BaseModel):
        message: str
    response = await ai.responses(
        "gpt-5-nano",
        [{"role": "system", "content": "You are a helpful assistant that outputs everything in reverse."},
         {"role": "user", "content": "Say 'hello world'"}],
        text_format=HelloWorldResponse)
    logging.info(response.message)

category_vectorizer = TfidfVectorizer(ngram_range=(1, 3), max_features=5000)
category_texts = list(VALID_CATEGORIES)
category_vectors = category_vectorizer.fit_transform(category_texts)

def _find_relevant_categories(product_text: str, top_k: int = 20) -> list[str]:
    # Finds the top K most relevant categories for a product
    query_vec = category_vectorizer.transform([product_text])
    similarities = cosine_similarity(query_vec, category_vectors)[0]
    top_indices = np.argsort(similarities)[-top_k:][::-1]
    return [category_texts[i] for i in top_indices]

SYSTEM_PROMPT = """You are a backend data extraction engine. Your task is to extract structured product data from raw HTML of a product detail page.
You MUST output ONLY valid JSON that conforms exactly to the provided Product schema. All required fields MUST be present. Optional fields may be null if not found.
Rules:
- Do NOT invent information.
- Do NOT guess values that are not explicitly present. 
- If a field is missing, infer only when it is clearly implied by the page
- Use the AVAILABLE MEDIA URLs list provided: {media_context} and select up to 8 of the most relevant unique image and video URLs from that list.
- Prices must be numeric (no currency symbols).
- Currency must be a 3-letter ISO code (e.g. USD).
- Extract Variants which represent purchasable configurations (size, color, pack, etc.).
- Variants should be a list of dictionaries with consistent keys.
- For category: For category: Read the FULL product context including brand names, find the best single match, then select the EXACT matching path from this list (do not modify or shorten it): {categories_list}.
- All text (title, description, features) must be clean, human-readable do not use Unicode characters (™, ®, etc.). Replace any escape sequences with proper symbols.
- Description should be a clean, simple summary (no HTML tags).
Output ONLY the JSON object, no markdown, no code blocks, no explanations."""

def _clean_html(html: str, max_length: int = 100000) -> str:
    # method to remove scripts, styles, but keeps images
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'noscript', 'iframe']): # Remove noise
        tag.decompose()
    
    cleaned = str(soup) # Get cleaned HTML string
    
    if len(cleaned) > max_length: # Truncate if needed
        cleaned = cleaned[:max_length]
    
    return cleaned

def _extract_media_urls(html: str) -> dict[str, list[str]]:
    soup = BeautifulSoup(html, 'html.parser')
    
    images = set()
    videos = set()
    
    # Extract images
    for img in soup.find_all('img'):
        if src := img.get('src') or img.get('data-src'):
            images.add(src)
    
    # Extract videos
    for video in soup.find_all(['video', 'source']):
        if src := video.get('src') or video.get('data-src'):
            videos.add(src)
    
    return {"images": list(images), "videos": list(videos)}

async def html_ingest(html: str) -> Product:
    cleaned_html = _clean_html(html)
    media_urls = _extract_media_urls(html)

    soup = BeautifulSoup(html, 'html.parser')
    title = soup.find('title')
    title_text = title.get_text() if title else ""
    product_text = soup.get_text()[:1000]
    combined_text = title_text + product_text
    
    relevant_cats = _find_relevant_categories(combined_text, top_k=20)
    categories_list = "\n".join(relevant_cats)

    media_context = f"Images: {json.dumps(media_urls['images'])}\nVideos: {json.dumps(media_urls['videos'])}"
    system_prompt = SYSTEM_PROMPT.replace("{categories_list}", categories_list).replace("{media_context}", media_context)
    
    return await ai.responses(
        model="gpt-5-mini",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract product information from the following HTML files.\nHTML:\n{cleaned_html}"}
        ],
        text_format=Product
    )

async def ingest_all(html_files: list[Path]) -> list[Product]:
    htmls = [p.read_text(encoding="utf-8") for p in html_files]
    tasks = [html_ingest(html) for html in htmls]

    # For MVP, we'll run them all concurrently
    products = await asyncio.gather(*tasks)
    return products

def save_products(products: list[Product], path="final-products.json"):
    with open(path, "w") as f:
        json.dump(
            {
                "version": "v1",
                "products": [p.model_dump() for p in products]
            },
            f,
            indent=2
        )

async def main():
    html_files = Path("./data").glob("*.html")
    products = await ingest_all(list(html_files))
    save_products(products)
    logging.info(f"Saved {len(products)} products to products.json")

if __name__ == "__main__":
    asyncio.run(main())
    # logging.basicConfig(level=logging.INFO)
    # asyncio.run(hello_world())
