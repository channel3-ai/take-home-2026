## Channel3 Take Home Assignment

# Take-Home Engineering Assignment

## MVP Setup & Running Instructions

### Prerequisites
- Python 3.12+
- Node.js 18+
- uv (Python package manager)

### First Time Setup

**Backend:**
```bash
cd backend
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
```

### Running the Application

You'll need two terminals running simultaneously:

**Terminal 1 - Backend API:**
```bash
cd backend
uvicorn api:app --reload
```
Backend runs at `http://localhost:8000`

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```
Frontend runs at `http://localhost:5173`

### Data Ingestion (One-Time)

To process HTML files and generate product data:

```bash
cd backend
uv run python main.py
```

This reads HTML files from `backend/data/*.html`, calls the GPT-4o-mini API to extract structured product information, and generates `products.json`.

### Running Tests

From the root directory:
```bash
pytest backend/tests
```

Unit tests validate the FastAPI endpoints and ensure the product retrieval logic works correctly.

---

## Current MVP Architecture

### Backend
- **Ingestion (`main.py`)**: Processes HTML files from `backend/data/` using OpenAI's GPT-4o-mini API to extract structured product data into a Pydantic `Product` model, outputting `products.json`
    - **Category Matching**: Uses TF-IDF (Term Frequency-Inverse Document Frequency) vectorization and cosine similarity to match extracted categories against a predefined category taxonomy, ensuring consistent categorization across products
- **Data Model**: Products stored without explicit IDs in MVP (array index used for routing)
- **API (`api.py`)**: Simple FastAPI server with a single `GET /products` endpoint that returns the generated product data
- **Storage**: File-based JSON storage (no database for MVP simplicity)
- **Testing**: pytest-based unit tests covering API endpoints

### Frontend
- **Framework**: React + TypeScript + Vite
- **UI Library**: shadcn/ui components with Tailwind CSS
- **Features**: 
  - Responsive product grid (mobile & desktop)
  - Product detail pages (PDP)
  - Image display, pricing, variants, and descriptions
  - React Router for navigation
- **API Integration**: Fetches from FastAPI backend on page load

### Data Flow
1. HTML files → `main.py` → LLM extraction → `products.json`
2. FastAPI serves `products.json` via `/products` endpoint
3. React frontend fetches and displays products

---

## Scaling to Web-Scale Production

### Backend: 5 Products → 50 Million Products

**Current MVP Assumptions That Won't Scale:**
- ❌ File-based JSON storage - no indexing, slow reads, not concurrent-safe
- ❌ Loading entire product catalog in memory per request
- ❌ Synchronous LLM API calls during ingestion (would take years for 50M products)
- ❌ Single-server architecture - no horizontal scaling
- ❌ No caching layer
- ❌ Sequential HTML processing

**Proposed Production Architecture (Azure-based):**

**Ingestion Pipeline:**
1. **Azure Event Hub**: Receives HTML file URLs as events (streaming ingestion)
2. **Azure Functions** (consumption plan): Serverless workers that:
   - Pull events from Event Hub
   - Fetch HTML content
   - Call GPT-4o-mini API (with rate limiting & retry logic)
   - Write structured products to Cosmos DB
3. **Parallelization**: Process 1000s of products concurrently
4. **Dead Letter Queue**: Handle failed extractions for manual review

**Data Storage:**
- **Azure Cosmos DB** (NoSQL): 
  - **Document ID**: Generate unique product IDs using UUIDs as Cosmos DB requires an `id` field for each document
  - **Partition Key**: Use `/category` as partition key for efficient queries and even data distribution (alternative: `/brand` or composite `/category-brand`)
  - No traditional primary keys (NoSQL) - partition key + id uniquely identifies documents
  - Global distribution for low-latency reads
  - Automatic indexing on key fields (price, brand, category)
  - TTL policies for stale products
- **Azure Blob Storage**: Store original HTML + images

**API Layer:**
- **Azure API Management**: Gateway with rate limiting, caching, authentication
- **Azure Kubernetes Service (AKS)** or **App Service**: 
  - Containerized FastAPI instances (horizontal auto-scaling)
  - Load balanced across multiple regions
- **Redis Cache** (Azure Cache for Redis): Cache popular products, search results
- **CDN** (Azure Front Door): Cache product images globally

**API Design:**
```
GET /products?page=1&limit=20&category=shoes&brand=nike
GET /products/{id}
GET /products/search?q=running+shoes
POST /products (admin only - trigger ingestion)
```

**Architecture Pattern:**
Adopt **MVC with Service/Repository layers**:
- **Controllers**: Handle HTTP requests/responses
- **Services**: Business logic (pricing calculations, availability checks)
- **Repositories**: Data access abstraction (Cosmos DB queries)
- **Benefits**: Testability, maintainability, team scalability

**Assumptions That Will Scale:**
- ✅ Pydantic models for validation (schema enforcement)
- ✅ RESTful API design principles
- ✅ Separation of ingestion and serving (different services)

**Alternative Cloud Options:**
- **AWS**: EventBridge + Lambda + DynamoDB + CloudFront
- **GCP**: Pub/Sub + Cloud Functions + Firestore + Cloud CDN

---

### Frontend: Powering Agentic Shopping Apps

**Developer API for AI Shopping Agents:**

```
# Product Search & Discovery
GET /api/v1/products/search
  - Natural language queries
  - Filters: price_range, categories, brands, ratings
  - Semantic search (vector embeddings)

# Product Recommendations
GET /api/v1/recommendations/{user_id}
  - Personalized suggestions
  - "Similar products" based on embeddings

# Product Comparison
POST /api/v1/products/compare
  - Side-by-side feature comparison
  - AI-generated summaries

# Structured Product Data
GET /api/v1/products/{id}/schema
  - Returns schema.org markup
  - LLM-friendly structured data

# Inventory & Pricing
GET /api/v1/products/{id}/availability
  - Real-time stock levels
  - Dynamic pricing
```

**Developer Tools:**

1. **SDK/Client Libraries**: Python, JavaScript, Go clients with type safety
2. **GraphQL API**: Flexible queries for mobile/agentic apps (reduce over-fetching)
3. **Webhooks**: Real-time product updates, price changes, back-in-stock alerts
4. **Embeddings API**: 
   ```
   POST /api/v1/embeddings
   ```
   Returns vector representations for semantic search
5. **AI Assistant API**:
   ```
   POST /api/v1/assistant/chat
   ```
   Conversational product discovery (powered by LLM with RAG over product catalog)
6. **Developer Portal**: 
   - API documentation (OpenAPI/Swagger)
   - Sandbox environment
   - Analytics dashboard
   - Rate limit monitoring

**Enhanced Frontend Features for Scale:**
- **Authentication**: OAuth 2.0 (Azure AD B2C or Auth0)
- **Shopping Cart**: Redis-backed session storage
- **Payments**: Stripe/PayPal integration
- **Customer Support**: Live chat (Intercom/Zendesk), AI chatbot
- **Feedback/Reviews**: Ratings, moderation pipeline
- **Personalization**: User preferences, browsing history
- **Hosting**: Azure Static Web Apps + CDN, custom domain (e.g., `shop.example.com`)
- **Analytics**: Application Insights, user behavior tracking
- **A/B Testing**: Feature flags for experimentation

**Scaling Frontend:**
- Static site generation (SSG) for product pages → faster loads
- Edge rendering for personalized content
- Progressive Web App (PWA) for offline support
- Image optimization pipeline (WebP, lazy loading, responsive images)

---

## Summary

The MVP demonstrates core competencies in full-stack development, API design, and LLM integration. The proposed production architecture leverages cloud-native services (event-driven ingestion, NoSQL databases, serverless compute) to handle web-scale traffic while providing developers with powerful APIs to build next-generation shopping experiences powered by AI agents.