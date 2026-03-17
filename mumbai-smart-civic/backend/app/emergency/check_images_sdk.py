import os
from google import genai

# New API key from user
api_key = "AIzaSyC1NA0bP8yZ8eI5GSC3PwhcE7C0wp_wQik"

def check_models():
    client = genai.Client(api_key=api_key)
    print("Checking models for image generation support...")
    try:
        models = client.models.list()
        found = False
        for m in models:
            # Look for models with 'generate_images' or similar capability
            if 'generate_images' in str(m) or 'imagen' in m.name.lower():
                print(f"FOUND: {m.name}")
                found = True
        if not found:
            print("No explicit image generation models found in the list.")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    check_models()
