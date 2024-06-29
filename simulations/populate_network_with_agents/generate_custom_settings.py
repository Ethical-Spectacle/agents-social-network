import requests
import json
import sys
import argparse
from difflib import SequenceMatcher

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def generate_custom_setting(previous_settings):
    url = "http://localhost:11434/api/generate"

    prompt = f"""Generate a custom setting for an AI assistant. The setting should include two parts:
    1. A unique persona description (e.g., "You are a chat buddy who talks like a cowboy.")
    2. A behavioral constraint (e.g., "You are not comfortable with anyone talking about politics.")

    Please provide these two elements in a JSON format like this:
    {{
        "persona": "Your persona description here",
        "constraint": "Your behavioral constraint here"
    }}

    Be creative and diverse in your generations. Ensure this setting is SIGNIFICANTLY DIFFERENT from these previous settings:
    {json.dumps(previous_settings, indent=2)}

    Generate a completely new and unique setting with a theme not used before."""

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
        persona_similarity = similarity(new_setting['persona'], prev_setting['persona'])
        constraint_similarity = similarity(new_setting['constraint'], prev_setting['constraint'])
        if persona_similarity > threshold or constraint_similarity > threshold:
            return False
    return True

def main(num_settings):
    print(f"Generating {num_settings} custom setting(s)...")
    settings = []

    for i in range(num_settings):
        print(f"\nGenerating setting {i+1}/{num_settings}")
        attempts = 0
        while attempts < 5:  # Limit attempts to avoid infinite loop
            setting = generate_custom_setting(settings)
            if setting and 'persona' in setting and 'constraint' in setting:
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
        with open('custom_settings.json', 'w') as f:
            json.dump(settings, f, indent=2)
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
