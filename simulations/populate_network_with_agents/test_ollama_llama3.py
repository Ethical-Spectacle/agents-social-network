import requests
import json

def test_ollama():
    url = "http://localhost:11434/api/generate"
    
    prompt = "tell me your favourite color and tell me why."
    
    payload = {
        "model": "llama3",  # Using the correct model name
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = json.loads(response.text)
            generated_text = result['response']
            print("Ollama response:")
            print(generated_text)
            print("\nOllama with llama3 is up and working!")
        else:
            print(f"Error: Received status code {response.status_code}")
            print("Ollama might be running but is not responding as expected.")
    
    except requests.exceptions.ConnectionError:
        print("Connection Error: Could not connect to Ollama.")
        print("Make sure Ollama is running and the address is correct.")
    
    except requests.exceptions.Timeout:
        print("Timeout Error: The request to Ollama timed out.")
        print("Ollama might be overloaded or not responding.")
    
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    print("Testing Ollama connection with llama3...")
    test_ollama()
