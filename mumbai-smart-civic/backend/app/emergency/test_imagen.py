import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

try:
    print("Listing available models that support generate_images...")
    models = genai.list_models()
    for m in models:
        if 'generateContent' in m.supported_generation_methods or 'generateImage' in m.supported_generation_methods:
            pass # print(m.name, m.supported_generation_methods)
            
    print("Testing Imagen 3...")
    result = genai.generate_images(
        prompt="A comic style infographic for illiterate people showing safety steps for an earthquake.",
        number_of_images=1,
        model="models/imagen-3.0-generate-001",
        aspect_ratio="3:4"
    )
    
    img = result.images[0]
    img.image.save("test_imagen_output.png")
    print("SUCCESS: Image generated!")
except Exception as e:
    print("FAILED:", str(e))
    
    print("\nTrying with models/imagen-3.0-fast-generate-001...")
    try:
        result2 = genai.generate_images(
            prompt="A comic style infographic for illiterate people showing safety steps for an earthquake.",
            number_of_images=1,
            model="models/imagen-3.0-fast-generate-001",
            aspect_ratio="3:4"
        )
        result2.images[0].image.save("test_imagen_output.png")
        print("SUCCESS with fast model!")
    except Exception as e2:
        print("FAILED (fast model):", str(e2))
