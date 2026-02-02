# Channel3 Take-Home Assignment

This project extracts structured product data from e-commerce HTML pages using LLM-based extraction and displays them in a React frontend.

## Prerequisites

- **Python 3.12+** (required for backend)
- **Node.js 18+** and **npm** (required for frontend)
- **OpenRouter API Key** (get one at https://openrouter.ai)

## Setup Instructions

### 1. Clone and Navigate

```bash
cd take-home-2026
```

### 2. Backend Setup

1. **Install Python dependencies:**

   **Option A: Using `uv` (recommended):**
   ```bash
   uv sync
   ```

2. **Set up environment variables:**

   Create a `.env` file in the project root:
   ```bash
   echo "OPEN_ROUTER_API_KEY=your_api_key_here" > .env
   ```
   
   Replace `your_api_key_here` with your OpenRouter API key.

### 3. Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

## Running the Application

### Step 1: Extract Products (Backend)

Extract product data from HTML files in the `data/` directory:

**Extract all products:**
```bash
# From project root
python extractor.py
```

**Extract a single product:**
```bash
python extractor.py data/nike.html
# or
python extractor.py nike.html
```

This will:
- Process all HTML files in the `data/` directory
- Extract product information using LLM
- Save results to `extracted_products.json`
- Log token usage and estimated costs

**Note:** The extraction process uses an LLM and may take a few minutes for all products. Token usage and costs are logged during extraction.

### Step 2: Start the Backend API Server

From the project root:

```bash
python main.py
or 
uv run python main.py
```

The API will run at `http://localhost:8000`

**API Endpoints:**
- `GET /` - Health check
- `GET /products` - Get all extracted products (returns JSON array)

### Step 3: Start the Frontend Development Server

In a **new terminal**:

```bash
cd frontend
npm run dev
```

The frontend will run at `http://localhost:5173` (or another port if 5173 is busy)

### Step 4: View the Application

Open your browser and navigate to:
```
http://localhost:5173
```

You should see:
- **Catalog Page**: A grid of all extracted products with images, names, and prices
- **Product Detail Page**: Click any product to see detailed information including:
  - Product images (gallery view)
  - Title, brand, and price
  - Category
  - Variants (color, size, fit, etc.)
  - Description
  - Key features

## Project Structure

```
take-home-2026/
├── data/                    # HTML files to extract from
│   ├── nike.html
│   ├── llbean.html
│   ├── article.html
│   ├── ace.html
│   ├── adaysmarch.html
│   └── README.md
├── extractor.py            # Main extraction script
├── main.py                 # FastAPI backend server
├── models.py               # Product data models (Pydantic)
├── HTML_reducer.py         # HTML size reduction utility
├── ai.py                   # LLM client wrapper (OpenRouter)
├── categories.txt          # Google Product Taxonomy
├── extracted_products.json # Output file (generated after extraction)
├── .env                    # Environment variables (create this)
├── pyproject.toml         # Python dependencies
└── frontend/               # React frontend
    ├── src/
    │   ├── pages/          # CatalogPage, ProductDetailPage
    │   ├── components/     # ProductCard, ProductGrid, etc.
    │   └── types/          # TypeScript type definitions
    └── package.json
```

## Troubleshooting

1. **"OPEN_ROUTER_API_KEY not found" error:**
   - Ensure `.env` file exists in the project root
   - Verify the key is set correctly: `OPEN_ROUTER_API_KEY=your_key_here`
   - Make sure `python-dotenv` is installed (it's in dependencies)

2. **"No products found" error in frontend:**
   - Run `python extractor.py` first to generate `extracted_products.json`
   - Ensure the backend server is running on port 8000
   - Check that `extracted_products.json` exists in the project root

3. **Port already in use:**
   - **Backend**: Change port in `main.py` (line 102): `uvicorn.run(app, host="0.0.0.0", port=8001)`
   - **Frontend**: Vite will automatically use the next available port, or update `vite.config.ts`

4. **Python dependencies not found:**
   - Ensure you're using Python 3.12+
   - Try: `python3 -m pip install -e .`
   - Verify virtual environment is activated if using one

5. **Frontend build errors:**
   - Delete `node_modules` and `package-lock.json`, then run `npm install` again
   - Ensure Node.js version is 18+

6. **Category validation errors:**
   - Categories must match exactly from `categories.txt` (Google Product Taxonomy)
   - Check the error message for the invalid category name
   - The LLM should automatically use valid categories, but if errors occur, check `categories.txt`

## Quick Start Summary

```bash
# 1. Setup backend
echo "OPEN_ROUTER_API_KEY=your_key" > .env
pip install -e .  # or uv sync

# 2. Extract products
python extractor.py

# 3. Start backend (terminal 1)
python main.py

# 4. Start frontend (terminal 2)
cd frontend && npm install && npm run dev

# 5. Open browser
# Navigate to http://localhost:5173
```

## System Design

### Scaling to Web-Scale (5 to 50 Million Products)

**Backend Architecture:**

    In order to scale, the system requires a microservice architecture with:
        Distributed extraction workers: using a message queue to process HTML pages asynchronously, with horizontal scaling based on queue depth
        Distributed database: using PostgreSQL with read replicas for product queries, partitioned by brand/category for efficient sharding, and Elasticsearch for full-text search
        Caching layer: with Redis for hot product data and CDN for images
        LLM cost optimization: by batching similar products, using cheaper models for simple extractions, and implementing a confidence-scoring system that only uses expensive models when needed
        Incremental updates: via webhook monitoring or scheduled re-crawls, storing only deltas rather than re-extracting entire catalogs.

**What Will Scale:** The HTML reduction approach (reducing 80%+ of HTML size) scales well as it reduces LLM token costs. The generic extraction prompt (no site-specific logic) allows adding new e-commerce sites without code changes. The structured Product schema is database-friendly and supports efficient indexing. 

**What Won't Scale:** Synchronous extraction (one product at a time) must become asynchronous with running workers. Single JSON file storage must migrate to a distributed database. The current LLM-per-product approach becomes cost-prohibitive at scale—implement model routing (cheap models for simple products, expensive only when needed) and extraction confidence scoring. Manual HTML file processing must become automated crawling with rate limiting, retry logic, and change detection.

**Frontend API for Agentic Shopping Apps:**

    Provide a GraphQL API with the following capabilities: 
    Semantic product search: (`searchProducts(query: String, filters: ProductFilters)` with natural language queries like "comfortable running shoes under $100")
    Product recommendations: (`recommendProducts(productId: ID, context: UserContext)` returning similar products based on embeddings)
    Structured product data: with variants, pricing, availability, and images in a single query
    Real-time updates: via GraphQL subscriptions for price changes and stock updates
    Agent-friendly endpoints: like `extractProductFromUrl(url: String)` for on-demand extraction and `compareProducts(productIds: [ID])` for side-by-side comparisons.

**Developer Tools:**

    Beyond the API, provide: 
    SDK libraries: (Python, JavaScript, Go) with type-safe clients and retry logic
    Webhook system: for real-time product updates (price changes, new variants, stock alerts) 
    Extraction playground: (web UI) for testing extraction on custom URLs with live preview of extracted data
    Analytics dashboard: showing extraction quality metrics, coverage by site, and cost tracking
    CLI tools: for bulk extraction, data export, and schema validation 
    Embedding vectors: for each product to enable semantic search and recommendation features in downstream applications.