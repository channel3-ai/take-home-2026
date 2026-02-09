# Local
from pathlib import Path
from ai import responses
from html_utils import (
    extract_media_links,
    extract_text_content,
    get_html_summary
)
from models import Product
from prompts import LLM_PROMPT

# Third-Party
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import List


# To run this back-end process, run the following command:
# "python3 -m uvicorn main:app --reload"
load_dotenv()

app = FastAPI()

api_key: str = os.environ.get("OPEN_ROUTER_API_KEY")

def _clean_html_for_ai(html_content: str, source_name: str = "") -> str:
    """
    This cleans a HTML file and prepares an AI-friendly input for
    an LLM.
    """
    text_content = extract_text_content(html_content)
    media = extract_media_links(html_content)
    summary = get_html_summary(html_content)
    
    structured_content = f"""
        SOURCE: {source_name if source_name else "Unknown"}
        ========================================
        TITLE: {summary['title']}
        DESCRIPTION: {summary['description'] if summary['description'] else 'N/A'}

        CONTENT:
        {text_content[:3000]}

        MEDIA ASSETS:
        - Images: {len(media['images'])} found
        - Videos: {len(media['videos'])} found
        """
    
    return structured_content


def _combine_html_files(html_files_dict: dict) -> str:
    """
    This combines multiple cleaned HTML files into a single prompt-friendly string.
    It accepts a dict of {source_name: html_content} pairs as its argument.
    """
    # We separate the cleaned HTML files with 80 equality signs so that
    # we can cleanly distinguish them from one another.
    combined = "PRODUCT CATALOG DATA\n" + "=" * 80 + "\n\n"
    
    for source_name, html_content in html_files_dict.items():
        cleaned = _clean_html_for_ai(html_content, source_name)
        combined += cleaned + "\n\n"
    
    return combined


@app.post("/products/")
async def extract_products() -> dict:
    """
    Extract product information from all HTML files in the data/rawData directory.
    Sends all files to OpenAI and returns a list of Product objects.
    
    Returns:
        dict with 'status' and 'products' (list of Product objects)
    """
    try:
        data_dir = Path("../data/rawData")
        
        if not data_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Data directory not found: {data_dir}."
            )
        
        # Load all HTML files
        html_files = list(data_dir.glob("*.html"))
        
        if not html_files:
            raise HTTPException(
                status_code=404,
                detail="No HTML files found in data directory."
            )
        
        print(f"Found {len(html_files)} HTML files to process.")
        
        html_files_dict = {}
        for html_file in html_files:
            try:
                html_content = html_file.read_text(encoding="utf-8")
                html_files_dict[html_file.stem] = html_content
            except Exception as e:
                print(f"Warning: Could not read {html_file.name}: {e}.")
        
        if not html_files_dict:
            raise HTTPException(
                status_code=400,
                detail="Could not read any HTML files."
            )
        
        # Combine all HTML files into a single prompt
        combined_content = _combine_html_files(html_files_dict)
        
        # Create prompt for OpenAI using the LLM_PROMPT from prompts.py
        prompt = f"""{LLM_PROMPT}
        PRODUCT DATA:
        {combined_content}
        """
        
        # After we clean the raw HTML input, we send it to an LLM
        # and form the resultant JSON array into Product objects.
        products = await responses(
            model="google/gemini-2.5-flash-lite",
            input=prompt,
            text_format=List[Product],
            temperature=0.3,
            max_tokens=4000
        )
        
        return {
            "status": "success",
            "product_count": len(products),
            "files_processed": len(html_files_dict),
            "products": [product.dict() for product in products]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            {"error": str(e), "status": "error"},
            status_code=500
        )