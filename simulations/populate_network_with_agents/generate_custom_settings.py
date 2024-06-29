import requests
import json
import sys
import argparse
from difflib import SequenceMatcher

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def generate_custom_setting(previous_settings):
    url = "http://localhost:11434/api/generate"

    prompt = f"""Generate custom settings for an AI agent. The settings should include two parts:
    1. Instructions: Describe the agent's behavior, communication style, and any specific traits or characteristics.
    2. Toxicity Settings: Define the agent's tolerance for different types of content and behavior.

    Please provide these two elements in a JSON format like this:
    {{
        "instructions": "Detailed instructions for the agent's behavior and communication style",
        "toxicitySettings": "Specific guidelines for the agent's content tolerance and ethical boundaries"
    }}

    Be creative and diverse in your generations. Ensure this setting is SIGNIFICANTLY DIFFERENT from these previous settings:
    {json.dumps(previous_settings, indent=2)}

    Generate a completely new and unique setting. The instructions should define a distinct personality or role, while the toxicity settings should outline the agent's approach to sensitive topics or potentially harmful content.

    Example (do not use this exact setting):
    {{
        "instructions": "You are a Gen Z texter. You can use abbreviations and common slang. You can ask questions, provide answers, or just chat. You should not say anything offensive, toxic, ignorant, or malicious.",
        "toxicitySettings": "You are moderate and not overly sensitive, yet do not tolerate any form of hate speech, racism, or discrimination. You are open to learning and growing."
    }}

    Create a new, unique setting different from this example and the previous settings."""

    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        generated_text = result['response']

        try:
            start = generated_text.find('{')
            end = generated_text.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = generated_text[start:end]
                setting = json.loads(json_str)
                return setting
            else:
                print("Could not find a valid JSON object in the generated text.")
                return None
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON from the generated text: {e}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error making request to Ollama: {e}")
        return None

def is_setting_unique(new_setting, previous_settings, threshold=0.7):
    for prev_setting in previous_settings:
        instructions_similarity = similarity(new_setting['instructions'], prev_setting['instructions'])
        toxicity_similarity = similarity(new_setting['toxicitySettings'], prev_setting['toxicitySettings'])
        if instructions_similarity > threshold or toxicity_similarity > threshold:
            return False
    return True

def save_settings_to_file(settings, filename='custom_settings.json'):
    with open(filename, 'w') as f:
        json.dump(settings, f, indent=2)
    print(f"Settings saved to {filename}")

def main(num_settings):
    print(f"Generating {num_settings} custom setting(s)...")
    settings = []

    for i in range(num_settings):
        print(f"\nGenerating setting {i+1}/{num_settings}")
        attempts = 0
        while attempts < 5:  # Limit attempts to avoid infinite loop
            setting = generate_custom_setting(settings)
            if setting and 'instructions' in setting and 'toxicitySettings' in setting:
                if is_setting_unique(setting, settings):
                    settings.append(setting)
                    print(f"Setting {i+1} generated successfully.")
                    break
                else:
                    print("Generated setting too similar to previous ones. Retrying...")
            else:
                print(f"Failed to generate setting {i+1}. Retrying...")
            attempts += 1
        
        if attempts == 5:
            print(f"Failed to generate a unique setting after 5 attempts for setting {i+1}.")

    if settings:
        save_settings_to_file(settings)
        print(f"\nSuccessfully generated and saved {len(settings)} setting(s) to custom_settings.json")
    else:
        print("\nFailed to generate any valid settings.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate custom AI assistant settings.")
    parser.add_argument('num_settings', type=int, help="Number of custom settings to generate")
    args = parser.parse_args()

    if args.num_settings < 1:
        print("Please specify a positive number of settings to generate.")
        sys.exit(1)

    main(args.num_settings)
