from app.emergency.pdf_generator import generate_pdf

try:
    url = generate_pdf("earthquake", "critical", ["drop", "cover", "hold"], "school", 3)
    print("SUCCESS, url:", url)
except Exception as e:
    import traceback
    traceback.print_exc()
