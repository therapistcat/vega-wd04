import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    result = client.models.generate_images(
        model='imagen-3.0-generate-001',
        prompt='A comic style infographic for illiterate people showing safety steps for an earthquake.',
        config=dict(
            number_of_images=1,
            output_mime_type="image/jpeg",
        )
    )
    print("SUCCESS: Image generated!")
except Exception as e:
    print("FAILED EXCEPTION:", str(e))
