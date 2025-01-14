# test_ollama.py
import requests
import json
import logging

logging.basicConfig(level=logging.DEBUG)

def test_ollama_connection():
    hosts = [
        "http://host.docker.internal:11434",
        "http://localhost:11434",
        "http://0.0.0.0:11434",
        "http://172.17.0.1:11434"
    ]
    
    for host in hosts:
        try:
            print(f"\nTesting {host}...")
            response = requests.get(f"{host}/api/tags")
            print(f"Status code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            if response.status_code == 200:
                print(f"✅ Success with {host}")
                
                # Test generate endpoint
                print("\nTesting generate endpoint...")
                test_prompt = "Say hello"
                response = requests.post(
                    f"{host}/api/generate",
                    json={
                        "model": "llama3.1:latest",
                        "prompt": test_prompt,
                        "stream": False
                    }
                )
                print(f"Generate status code: {response.status_code}")
                print(f"Generate response: {response.text[:200]}...")
                return host
        except Exception as e:
            print(f"❌ Error with {host}: {str(e)}")
    
    return None

if __name__ == "__main__":
    print("🔍 Testing Ollama connectivity...")
    working_host = test_ollama_connection()
    if working_host:
        print(f"\n✨ Found working Ollama host: {working_host}")
    else:
        print("\n❌ Could not connect to Ollama on any host")