# Local
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai import responses
from backend.html_utils import (
    extract_media_links,
    extract_text_content,
    get_html_summary
)
from models import Product, ProductExtractionRequest, ProductList
from backend.prompts import LLM_PROMPT

# Third-Party
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import os


# To run this back-end process, run the following command:
# "uv sync"
# "uv run uvicorn process_html:app --reload"
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


# curl -X POST http://localhost:8000/products/ -H "Content-Type: application/json" -d '{"paths": ["data/rawData/ace.html", "data/rawData/article.html", "adaysmarch.html", "llbean.html", "nike.html"]}'
@app.post("/products/")
async def extract_products(request: ProductExtractionRequest) -> dict:
    try:
        if not request.paths:
            raise HTTPException(status_code=400, detail="No file paths provided.")

        all_products = []
        processed_files = 0
        failures = []

        for path_str in request.paths:
            path = Path(path_str)

            if not path.exists():
                failures.append({"path": path_str, "error": "File not found"})
                continue

            try:
                html_content = path.read_text(encoding="utf-8")
            except Exception as e:
                failures.append({"path": path_str, "error": str(e)})
                continue

            cleaned = _clean_html_for_ai(html_content, path.stem)

            prompt = f"""{LLM_PROMPT}
            PRODUCT DATA:
            {cleaned}
            """

            try:
                print(f"Calling model for {path.name}...")
                result = await responses(
                    model="openai/gpt-5",
                    input=prompt,
                    text_format=ProductList,
                )
                print(f"Finished {path.name}")

                all_products.extend(result.products)
                processed_files += 1

            except Exception as e:
                print(f"Failed {path.name}: {e}")
                failures.append({"path": path_str, "error": str(e)})

        return {
            "status": "success",
            "files_requested": len(request.paths),
            "files_processed": processed_files,
            "product_count": len(all_products),
            "products": [p.dict() for p in all_products],
            "failures": failures,
        }

    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e), "status": "error"}, status_code=500)