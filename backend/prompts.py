from models import VALID_CATEGORIES

"""
Our Product class has several fields. The idea is that
we will populate our Product objects' fields with the information that the
LLM is able to extract from the raw, unstructued HTML data that I am 
feeding it.
"""

categories: str = str(VALID_CATEGORIES)
LLM_PROMPT: str = '''
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
would be 25.00). For the specific currency, adhere to the ISO 4217 standard. If you
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