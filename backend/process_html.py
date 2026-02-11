# Local/Native Imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai import responses
from backend.html_utils import (
    extract_media_links,
    extract_text_content,
    get_html_summary
)
from models import ProductExtractionRequest, ProductList
from backend.prompts import LLM_PROMPT

# Third-Party Imports
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os


# To run this back-end process, run the following commands:
# "uv sync"
# "uv run uvicorn backend.process_html:app --reload"
load_dotenv()

app = FastAPI()

# This allows us to communicate with our 
# frontend code.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        Images:
        {chr(10).join(media['images'][:50])}

        Videos:
        {chr(10).join(media['videos'][:20])}
        """
    
    return structured_content


# curl -X POST http://localhost:8000/products/ -H "Content-Type: application/json" -d '{"filePaths": ["data/rawData/ace.html", "data/rawData/adaysmarch.html", "data/rawData/article.html", "data/rawData/llbean.html", "data/rawData/nike.html"], "outputPath": "data/extracted_products.json"}'
@app.post("/products/")
async def extract_products(request: ProductExtractionRequest) -> dict:
    try:
        if not request.filePaths:
            raise HTTPException(status_code=400, detail="No file paths provided.")

        all_products = []
        processed_files = 0
        failures = []

        for path_str in request.filePaths:
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

        result = {
            "status": "success",
            "files_requested": len(request.filePaths),
            "files_processed": processed_files,
            "product_count": len(all_products),
            "products": [p.dict() for p in all_products],
            "failures": failures,
        }

        # Write results to the output file:
        try:
            output_path = Path(request.outputPath)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(result, f, indent=2)
            print(f"Results written to {request.outputPath}")
        except Exception as e:
            print(f"Failed to write output file: {e}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e), "status": "error"}, status_code=500)


@app.get("/products/")
async def get_products() -> dict:
    """
    Retrieve the extracted products from the JSON file.
    """
    try:
        products_file = Path("data/extracted_products.json")
        
        if not products_file.exists():
            return {
                "status": "success",
                "products": [],
                "message": "No products file found yet. Run the extraction endpoint first."
            }
        
        with open(products_file, "r") as f:
            data = json.load(f)
        
        return data
    except Exception as e:
        return JSONResponse({"error": str(e), "status": "error"}, status_code=500)