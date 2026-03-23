"""Direct test of Sarvam API - Debug 400 error"""

import requests
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Get API key
api_key = os.getenv("SARVAM_API_KEY")
print(f"API Key loaded: {api_key[:20]}...")
print()

# Test different request formats
test_cases = [
    {
        "name": "Format 1: Standard Chat",
        "payload": {
            "model": "Sarvam-2B",
            "messages": [{"role": "user", "content": "Say hello"}],
            "temperature": 0.5,
            "max_tokens": 100
        }
    },
    {
        "name": "Format 2: Minimal",
        "payload": {
            "model": "Sarvam-2B",
            "messages": [{"role": "user", "content": "Say hello"}]
        }
    },
    {
        "name": "Format 3: With top_p",
        "payload": {
            "model": "Sarvam-2B",
            "messages": [{"role": "user", "content": "Say hello"}],
            "temperature": 0.5,
            "top_p": 0.9
        }
    },
    {
        "name": "Format 4: Simple text",
        "payload": {
            "model": "Sarvam-2B",
            "prompt": "Say hello",
            "temperature": 0.5,
            "max_tokens": 100
        }
    }
]

for test in test_cases:
    print("=" * 70)
    print(f"Testing: {test['name']}")
    print("=" * 70)
    print(f"Payload: {test['payload']}")
    print()
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            "https://api.sarvam.ai/v1/chat/completions",
            json=test['payload'],
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS!")
            result = response.json()
            if "choices" in result:
                print(f"Response: {result['choices'][0]['message']['content']}")
            print()
            break  # Found working format
        else:
            print(f"❌ Error {response.status_code}")
            print(f"Response: {response.text[:200]}")
            print()
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        print()

print("=" * 70)
print("DIAGNOSIS COMPLETE")
print("=" * 70)
print()
print("If all formats failed:")
print("1. Your API key might be invalid")
print("2. Check https://www.sarvam.ai for your actual API key")
print("3. Make sure it's in your .env file")
print()
print("If one format worked:")
print("We found the correct format!")