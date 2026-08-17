import requests
import os
from reportlab.pdfgen import canvas

# Create dummy PDF
pdf_path = "dummy_resume.pdf"
c = canvas.Canvas(pdf_path)
c.drawString(100, 750, "Arpit's Resume")
c.drawString(100, 730, "Skills: Python, Machine Learning, React, FastAPI")
c.save()

# Upload
url = "http://localhost:8000/api/resume/upload"
with open(pdf_path, "rb") as f:
    files = {"file": ("dummy_resume.pdf", f, "application/pdf")}
    try:
        response = requests.post(url, files=files)
        print("Status Code:", response.status_code)
        print("Response:", response.json())
    except Exception as e:
        print("Error connecting:", e)
