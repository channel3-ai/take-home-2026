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

### System Design: Backend
**General:**

Firstly, to scale the backend, I'd need to verify the efficacy and quality of the prompt. I don't think that five pages is a large enough sample size for ensuring that the prompt on which I've settled is good enough to run for fifty million pages. I'd need to run various different prompts on a larger sample size. I'd also need to time each prompt's efficacy, as differences in time are key. Sure, ten seconds might not mean too much for a sample size of five, but these ten seconds will exponentiate and destroy performance for the case of fifty million pages.

**What Will Scale:**
1. The Product schema is good. Based on the five pages that I perused (amongst various others), I think that the fields that we've captured in this BaseModel-inheriting class is enough to provide customers quality data that can power agentic-shopping workflows.
2. The Variant schema is also sufficient. These five pages are fairly similar, but fifty million pages will inevitably introduce variability in terms of product-differentiating qualities. Implementing this reusable key-value template allows the agent to scrape information that could be deemed useful. It's akin to a non-relational database in that we can append fields as needed. 
3. Cleaning the HTML files is also scalable. Many HTML pages, having been written by inexperienced programmers, are riddled with bloating comments, scripts, etc., which merely add noise and thereby degradate agent performance. Extirpating non-essential elements allows the models to sift through less data and thereby provide more pointed information.

**What Won't Scale:**
1. Obviously, we can't store these JSON files to the running computer's disk. We should use inexpensive object storage; Amazon S3 is the most obvious candidate. We should have a distributed-database system, one that stores object files across various clusters and provides redundant duplications so that we can ensure data availability.
2. We can't run this on one machine. If one page takes ten seconds to be extracted, then fifty million pages will take 5,787 days. Clearly, we need to distribute this load across numerous machines. We can turn our backend into a command-line program that can handle a variable amount of URLs at once. Then, we'll use sixteen different machines to run sixteen different processes of our task, each dealing with 1/16th of the load.
3. I doubt that there's a one-size-fits-all model, so certain pages will incur errors from the model. We can send these failing pages to a dead-letter Kafka queue that holds the links that'll need to be reprocessed later. We can try more curtailed prompts to account for these hairy cases. These curtailed prompts can be inputted into different models, too: We're not limited to ChatGPT 5.2.
4. The logging and duplicate-prevention schemes are not good enough. We could enhance the former so that we're alarmed if model-response time is subpar or if we're burning through tokens too quickly. As for the latter, we need some distributed cache to ensure that we're not wasting tokens on pages that we've already parsed. From my experience, Redis fits this use case.

### System Design: Frontend
**Powering Agentic-Shopping Workflows:**
There are a few endpoints that have come to mind:

`/api/{product_guid}/`: This returns the Product information that is associated with the unique identifier to which the Product corresponds. This would be the JSON object that we generated with our FastAPI backend. This type of raw data would allow users to build frontend applications atop of our store of data. It might seem self-defeating, as we'd want users to use our UIs, but the age of "vibe coding" has extirpated all barriers to entry and have allowed people to visualise data in ways that match their workflows. My current firm has realised this, so it's no longer fixated on keeping users wedded to the illustrious Terminal.

`/api/categories`: This would return the Google Taxonomy; it allows people to see the categories under which we've categorised our large pool of products.

`/api/recommend/`: Given various inputs (e.g., price, size, product style, brand family, etc.), return products that match the specified criteria. This would allow users to pointedly find products that adhere to exacting criteria.

There are various other endpoints, too. Natural-language search is another great idea, as is an endpoint that allows a user (or an agent) to compare the merits of two different products via their product GUIDs. However, to keep it light, I've limited myself to the three endpoints above.

**Tools:**
We can have a UI that allows users to run test queries. At my current firm, we use Trino, which is a query engine that allows us to efficiently sift through large data sets. Trino offers a UI that allows users to run ad hoc queries that provide users a taste of how the querying system works. We could have the same, albeit it'd be a Postman-esque application that allows users to look at example data, which would be delivered in JSON format.

Furthermore, we could provide a natural-language-based querying system. I used to work at Zillow. Whilst I was at the firm, Rich Barton started the transition from a traditional list-based system to a language-based one. Sure, we can let users query our systems with GUIDs and names, but we can also allow them to input wide-encompassing queries that provide the granularity that the traditional REST paradigm does not allow.

Finally, alongside traditional REST documentation, provide example payloads and responses that demonstrate how agents should invoke endpoints and interpret results. We could use Swagger for this.