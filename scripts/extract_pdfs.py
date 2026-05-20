"""
Extract and clean text from Osho PDFs.

Handles:
- Watermark removal (OceanofPDF, Scan to Download, Bookey)
- Skipping garbage pages (copyright, TOC, blank pages)
- Stripping page numbers and headers/footers
- Outputs clean .txt files to corpus/texts/
"""
import fitz  # PyMuPDF
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
PDF_DIR = os.path.join(PROJECT_DIR, "corpus", "pdfs")
TEXT_DIR = os.path.join(PROJECT_DIR, "corpus", "texts")

# Create output directory
os.makedirs(TEXT_DIR, exist_ok=True)

# ── Watermark patterns to strip ──
WATERMARK_PATTERNS = [
    r"OceanofPDF\.com",
    r"oceanofpdf\.com",
    r"Scan to Download",
    r"Written by Bookey",
    r"Check more about .+ Summary",
    r"Listen .+ Audiobook",
    r"www\.osho\.com\S*",
    r"OSHO is a registered trademark",
    r"© \d{4}.*?Foundation",
    r"Copyright ©.*?reserved\.",
]

# ── Pages to skip (by content keywords) ──
SKIP_KEYWORDS = [
    "table of contents",
    "also by osho",
    "about the author",
    "about osho",
    "osho international meditation resort",
    "for more information",
    "isbn",
    "library of congress",
    "published by",
    "printed in",
    "cover design",
    "bookey",  # Fake summary PDFs
]

# ── Per-book configuration ──
BOOK_CONFIG = {
    "The Book of Secrets by Osho.pdf": {
        "name": "the_book_of_secrets",
        "skip_pages_before": 15,   # Skip title, copyright, TOC (pages 1-15)
        "skip_pages_after": 1625,  # Skip back matter
        "min_text_length": 100,    # Skip pages with less than 100 chars
    },
    "_OceanofPDF.com_Courage_The_Joy_of_Living_Dangerously_-_Osho.pdf": {
        "name": "courage",
        "skip_pages_before": 8,    # Skip title, copyright, TOC
        "skip_pages_after": 185,   # Skip back matter
        "min_text_length": 100,
    },
    "114445864-Awareness-Osho.pdf": {
        "name": "awareness",
        "skip_pages_before": 5,
        "skip_pages_after": 212,
        "min_text_length": 50,
    },
    "_OceanofPDF.com_From_Bondage_to_Freedom_-_Osho.pdf": {
        "name": "from_bondage_to_freedom",
        "skip_pages_before": 5,
        "min_text_length": 50,
    },
    "_OceanofPDF.com_The_Magic_of_Self-Respect__Awakening_to_yo_-_Osho.pdf": {
        "name": "magic_of_self_respect",
        "skip_pages_before": 5,
        "min_text_length": 50,
    },
    "_OceanofPDF.com_Trust_-_Osho.pdf": {
        "name": "trust",
        "skip_pages_before": 5,
        "min_text_length": 50,
    },
    # These are Bookey summaries, NOT real Osho books — skip them
    "Freedom PDF.pdf": None,
    "Intimacy by Osho PDF.pdf": None,
}


def clean_text(text: str) -> str:
    """Remove watermarks, extra whitespace, and garbage patterns."""
    # Remove watermark patterns
    for pattern in WATERMARK_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    
    # Remove standalone page numbers (lines that are just a number)
    text = re.sub(r"^\s*\d{1,4}\s*$", "", text, flags=re.MULTILINE)
    
    # Remove excessive blank lines (keep max 2)
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def should_skip_page(text: str) -> bool:
    """Check if a page is garbage (TOC, copyright, etc.)."""
    text_lower = text.lower().strip()
    
    # Skip empty/near-empty pages
    if len(text_lower) < 30:
        return True
    
    # Skip pages that are mostly skip keywords
    for keyword in SKIP_KEYWORDS:
        if keyword in text_lower and len(text_lower) < 500:
            return True
    
    return False


def extract_pdf(pdf_path: str, config: dict) -> str:
    """Extract clean text from a single PDF."""
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    skip_before = config.get("skip_pages_before", 0)
    skip_after = config.get("skip_pages_after", total_pages)
    min_length = config.get("min_text_length", 50)
    
    all_text = []
    skipped = 0
    extracted = 0
    
    for page_num in range(total_pages):
        # Skip front/back matter
        if page_num < skip_before or page_num >= skip_after:
            skipped += 1
            continue
        
        page = doc[page_num]
        text = page.get_text()
        
        # Skip pages with too little text (likely images or blanks)
        if len(text.strip()) < min_length:
            skipped += 1
            continue
        
        # Clean the text
        text = clean_text(text)
        
        # Skip garbage pages
        if should_skip_page(text):
            skipped += 1
            continue
        
        all_text.append(text)
        extracted += 1
    
    doc.close()
    
    print(f"  Extracted: {extracted} pages | Skipped: {skipped} pages")
    return "\n\n".join(all_text)


def main():
    print("=" * 60)
    print("OSHO PDF EXTRACTION PIPELINE")
    print("=" * 60)
    
    for filename in sorted(os.listdir(PDF_DIR)):
        if not filename.endswith(".pdf"):
            continue
        
        config = BOOK_CONFIG.get(filename)
        
        # Skip fake/summary PDFs
        if config is None:
            print(f"\n⚠️  SKIPPING: {filename} (not authentic Osho content)")
            continue
        
        pdf_path = os.path.join(PDF_DIR, filename)
        output_path = os.path.join(TEXT_DIR, f"{config['name']}.txt")
        
        print(f"\n📖 Processing: {filename}")
        print(f"   Output: {output_path}")
        
        text = extract_pdf(pdf_path, config)
        
        if len(text) < 100:
            print(f"  ❌ WARNING: Very little text extracted! PDF may be image-based.")
            print(f"     Extracted only {len(text)} characters.")
            continue
        
        # Save cleaned text
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        # Stats
        word_count = len(text.split())
        char_count = len(text)
        print(f"  ✅ Saved: {word_count:,} words | {char_count:,} characters")
    
    print(f"\n{'=' * 60}")
    print("DONE! Clean texts saved to corpus/texts/")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
