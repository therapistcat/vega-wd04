import os
import google.generativeai as genai

api_key = "AIzaSyC1NA0bP8yZ8eI5GSC3PwhcE7C0wp_wQik"
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash') # Use 1.5 flash as it is reliable for code

prompt = """
Write the complete SVG code for a professional, high-quality instructional vector icon representing "EARTHQUAKE SAFETY: DROP TO THE GROUND".
The icon should:
1. Show a simplified human figure dropping to hands and knees.
2. Use a modern, flat-design style with bold rounded corners.
3. Use a professional color palette (e.g., Orange and White).
4. Be sized 400x300.
5. Include subtle gradients or shadows to make it look "premium" and "proper".
6. Be completely visual (NO TEXT).

Output ONLY the raw SVG code.
"""

try:
    response = model.generate_content(prompt)
    svg_code = response.text.strip()
    if '```svg' in svg_code:
        svg_code = svg_code.split('```svg')[1].split('```')[0].strip()
    elif '```' in svg_code:
        svg_code = svg_code.split('```')[1].split('```')[0].strip()
        
    with open("test_gemini_svg.svg", "w", encoding="utf-8") as f:
        f.write(svg_code)
    print("SUCCESS: Gemini generated SVG code!")
    print("SVG Length:", len(svg_code))
except Exception as e:
    print("FAILED:", str(e))
