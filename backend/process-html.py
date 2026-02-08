from dotenv import load_dotenv
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
import openai
import os
from pathlib import Path

# To run this back-end process, run the following command:
# "python3 -m uvicorn main:app --reload"
load_dotenv()

app = FastAPI()

api_key: str = os.environ.get("OPEN_ROUTER_API_KEY")

@app.post("/process-html/")
async def process_html(file_path: str = Form(...), prompt: str = Form(...)):
    path = Path(file_path)
    if not path.is_file():
        return JSONResponse({"error": "File not found."}, status_code=404)

    html_text = path.read_text(encoding="utf-8")
    full_prompt = f"{prompt}\n\nHTML Content:\n{html_text}"

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": full_prompt}]
    )

    return JSONResponse({"result": response.choices[0].message.content})