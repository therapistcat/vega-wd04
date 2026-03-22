import os
import google.generativeai as genai

# Using the new key provided by the user
api_key = "AIzaSyC1NA0bP8yZ8eI5GSC3PwhcE7C0wp_wQik"
genai.configure(api_key=api_key)

print("Listing all models and their supported methods for the NEW key:")
try:
    for m in genai.list_models():
        print(f"Model: {m.name}")
        print(f"  Methods: {m.supported_generation_methods}")
        if 'generateImage' in m.supported_generation_methods or 'generateImages' in m.supported_generation_methods:
            print(f"  *** FOUND IMAGE GENERATION SUPPORT ON {m.name} ***")
except Exception as e:
    print(f"Error listing models: {e}")
