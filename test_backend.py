import requests
import json

# Test the sole /products/ endpoint.
url = "http://localhost:8000/products/"

print("Sending POST request to /products/ endpoint...")
try:
    response = requests.post(url)
    print(f"Status Code: {response.status_code}")
    print(f"\nResponse:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
