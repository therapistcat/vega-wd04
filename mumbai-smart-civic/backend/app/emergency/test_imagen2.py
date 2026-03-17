import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=api_key)
    print("Testing Imagen 3 via google.genai...")
    
    result = client.models.generate_images(
        model='imagen-3.0-generate-001',
        prompt='A comic style infographic for illiterate people showing safety steps for an earthquake.',
        config=types.GenerateImagesConfig(
            number_of_images=1,
            output_mime_type="image/jpeg",
            aspect_ratio="3:4"
        )
    )
    
    for generated_image in result.generated_images:
        with open("test_imagen_output.jpg", "wb") as f:
            f.write(generated_image.image.image_bytes)
    
    print("SUCCESS: Image generated! test_imagen_output.jpg")
except Exception as e:
    print("FAILED:", str(e))
