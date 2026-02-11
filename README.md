## Asad Shamsiev's Assignment

### Running the Backend

To run the backend service, please run the following commands:

```
uv sync
uv run uvicorn backend.process_html:app --reload
```

If you want to generate a JSON file with extracted Product data, please run the following command:

`curl -X POST http://localhost:8000/products/ -H "Content-Type: application/json" -d '{"filePaths": ["data/rawData/ace.html", "data/rawData/adaysmarch.html", "data/rawData/article.html", "data/rawData/llbean.html", "data/rawData/nike.html"], "outputPath": "data/extracted_products.json"}'`

### Running the Frontend
From the `product-registry` directory, run `npm start` to start the React app.

### System Design