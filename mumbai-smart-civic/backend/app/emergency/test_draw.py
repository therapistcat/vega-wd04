from reportlab.pdfgen import canvas
from pathlib import Path

path = "app/static/assets/posters/earthquake.png"
print(f"Testing drawImage on {path}")

c = canvas.Canvas("test_img.pdf")
try:
    c.drawImage(path, 0, 0, 100, 100)
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
