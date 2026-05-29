from pathlib import Path

def parse_file(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return _parse_pdf(path)
    return _parse_text(path)

def _parse_pdf(path: str) -> str:
    import pdfplumber
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
    text = "\n".join(pages)
    # Fall back to OCR if PDF is scanned (no extractable text)
    if len(text.strip()) < 100:
        text = _ocr_pdf(path)
    return text

def _ocr_pdf(path: str) -> str:
    try:
        import pytesseract
        from pdf2image import convert_from_path
        pages = convert_from_path(path, dpi=200)
        results = []
        for page in pages:
            t = pytesseract.image_to_string(page, lang="deu+eng")
            if t.strip():
                results.append(t)
        return "\n".join(results)
    except Exception as e:
        return ""

def _parse_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
