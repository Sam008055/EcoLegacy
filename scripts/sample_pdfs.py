"""Sample first few pages of each PDF to identify watermarks and garbage content."""
import fitz
import os

PDF_DIR = os.path.join(os.path.dirname(__file__), "..", "corpus", "pdfs")

for filename in os.listdir(PDF_DIR):
    if not filename.endswith(".pdf"):
        continue
    
    path = os.path.join(PDF_DIR, filename)
    doc = fitz.open(path)
    
    print(f"\n{'='*60}")
    print(f"FILE: {filename}")
    print(f"Total pages: {len(doc)}")
    print(f"{'='*60}")
    
    # Show pages 1, 2, 3, and 10
    for i in [0, 1, 2, 9]:
        if i < len(doc):
            text = doc[i].get_text()
            print(f"\n--- Page {i+1} ---")
            print(text[:600])
            print("...")
    
    doc.close()
