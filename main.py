import json
from urllib.request import Request, urlopen

request_data = {
    "model": "qwen2.5:3b",
    "prompt": "Explain what a rejected bank payment is.",
    "stream": False
}

json_text = json.dumps(request_data)

request_bytes = json_text.encode("utf-8")

request = Request(
    "http://localhost:11434/api/generate",
    data=request_bytes,
    headers={"Content-Type": "application/json"},
    method="POST"
)

with urlopen(request) as response:
    response_bytes = response.read()

response_text = response_bytes.decode("utf-8")

response_data = json.loads(response_text)

ai_answer = response_data["response"]
print(ai_answer)