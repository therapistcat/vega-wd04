import requests
import json

url = "http://localhost:8000/api/v1/vapi/webhook"
headers = {
    "Authorization": "Bearer mumbai_vapi_service_2025",
    "Content-Type": "application/json"
}

payload = {
    "type": "call.started",
    "call": {
        "id": "verify_test_call_999",
        "customer": {"number": "+910000000000"}
    },
    "transcript": "Complaint Summary: Testing backend stability and webhook storage."
}

try:
    response = requests.post(url, headers=headers, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")
