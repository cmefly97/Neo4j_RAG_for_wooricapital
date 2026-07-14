
## 파이썬 코드 예제

import requests

url = "https://namc-aigw.io.naver.com/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer <api_key>"
}
data = {
    "messages": [{ "role": "user", "content": "Hello!" }],
    "model": "HyperCLOVAX-SEED-32B-Think-Text"
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
