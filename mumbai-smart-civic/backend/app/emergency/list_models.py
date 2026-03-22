import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("Supported methods:")
methods = set()
models = []
for m in genai.list_models():
    for method in m.supported_generation_methods:
        methods.add(method)
    if 'generateImage' in m.supported_generation_methods or 'generateImages' in m.supported_generation_methods:
        models.append(m.name)
        
print("Image models:", models)
print("All available methods:", methods)
