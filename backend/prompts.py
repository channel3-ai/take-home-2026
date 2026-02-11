from models import VALID_CATEGORIES

"""
Our Product class has several fields. The idea is that
we will populate our Product objects' fields with the information that the
LLM is able to extract from the raw, unstructued HTML data that I am 
feeding it.
"""

categories: str = str(VALID_CATEGORIES)
# This was my first try; it wasn't very successful!
INEFFECTUAL_LLM_PROMPT: str = '''
I am going to feed you raw, unstructured HTML data; a text file that
lists all of the categories under which a product can fit; and a schema against which you
must create JSON objects. In simple terms, we are going to transform raw data into consistent,
serialisable Product objects that we can add to our existing store of Product objects.
There are guidelines by which you must abide:
1. Everything must be written in human-friendly syntax. This means that you are to abide by the
ASCII character set. Do not include any inklings of HTML code into our string-based fields. 
2. Do not hallucinate. If something is not explicitly stated on the product's page, then you 
should not guess to try to "fill in the blanks." You are to only populate Product objects with
data that is found within the HTML data that I am sending you.
3. Using the knowledge of the product that you've extracted from the HTML data, please categorise 
it under one of the following categories from Google's Product Taxonomy: 
''' + categories + '''
4. For the product's price, please use the standard decimal format (e.g., a twenty-five-dollar shirt
would be 25.00). Prices must be numeric values like 19.99 (no currency symbols).
For the specific currency, adhere to the ISO 4217 standard. If you
find that this product is discounted, then the discounted price is to populated
into the Product object's compare_at_price field, whereas the regular price is to 
populate its price field. 
5. Populate the Product object's variants field with the product's distinct 
qualities. For example, if we are looking at a slim-fit T-shirt, then you can 
add a Variant object that reflects this quality to the variants field. For example,
you insert {"fit": "slim"} (or a more elegant way of representing this configuration,
ensuring that it's consistent with the structure of the rest of the Product object's
fields).
'''

LLM_PROMPT: str = f'''
You are a Product Data Extraction Agent. Your task is to extract structured product information 
from raw HTML data and return it in a valid JSON format matching the ProductList schema below.

CRITICAL RULES:
1. ASCII ONLY: Do not use HTML tags or non-ASCII characters in string fields.
2. NO HALLUCINATION: Only extract data explicitly visible in the HTML. If a field is not found, 
   use the default value (empty list, null, or empty string as appropriate).
3. VALID CATEGORIES ONLY: Categorize products using ONLY these categories from Google's Product Taxonomy:
{categories}

JSON SCHEMA:
You must return a valid JSON object matching this exact structure:
{{
  "products": [
    {{
      "name": "Product name (required, string)",
      "price": {{
        "price": 19.99,
        "currency": "USD",
        "compare_at_price": null
      }},
      "description": "Clear product description without HTML tags (required, string)",
      "key_features": ["Feature 1", "Feature 2", "Feature 3"],
      "image_urls": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
      "video_url": null,
      "category": {{"name": "Category from the provided list"}},
      "brand": "Brand name if available (string)",
      "colors": ["color1", "color2"],
      "variants": [
        {{
          "key": "size",
          "value": "M",
          "price": {{
            "price": 19.99,
            "currency": "USD",
            "compare_at_price": null
          }},
          "image_urls": []
        }}
      ]
    }}
  ]
}}

FIELD-BY-FIELD EXTRACTION RULES:

- name: Extract the product's main name/title. Must be a non-empty string.

- price object:
  * price: Use standard decimal format (e.g., 25.00 for $25). Must be numeric.
  * currency: ISO 4217 code (e.g., "USD", "EUR", "GBP"). If not found, default to "USD".
  * compare_at_price: If product is on sale, use the ORIGINAL price here. Otherwise use null.

- description: Concise, clean product description. Remove all HTML markup. If multiple 
  descriptions exist, combine them into one coherent summary. Required field.

- key_features: Extract 3-5 main features/benefits as a list of short strings. For example:
  ["Durable fabric", "Moisture-wicking", "Available in 5 colors"]. If none found, use empty list.

- image_urls: Extract all product image URLs found. Return as a list of strings. 
  If no images found, return empty list [].

- video_url: Extract product video URL if present on the page. Otherwise, use null.

- category: Select the SINGLE best matching category from the provided list. Must be exact match.

- brand: Extract brand name if visible (e.g., "Nike", "Acme Corp"). If not found, use empty string "".

- colors: List all available colors as lowercase strings (e.g., ["black", "white", "navy"]).
  If no colors mentioned, use empty list.

- variants: Extract product variants (sizes, fits, colors, etc.) as a list. Each variant should have:
  * key: The attribute name (e.g., "size", "fit", "color")
  * value: The attribute value (e.g., "M", "slim", "black")
  * unit: The units of the value if it is available. Otherwise, leave this empty.
  * price: Variant-specific pricing (copy from main price if not different)
  * image_urls: Variant-specific images if available, else empty list
  If no variants exist, return empty list [].
Now, extract product data from the following HTML:
'''