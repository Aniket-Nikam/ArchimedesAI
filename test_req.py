import requests

payload = {"query": "Transformer attention mechanisms", "user_id": 1}
response = requests.post("http://localhost:8000/api/research/", json=payload, stream=True)

print("Status Code:", response.status_code)
try:
    for line in response.iter_lines():
        if line:
            print(line.decode("utf-8"))
except Exception as e:
    print("Caught exception:", e)

