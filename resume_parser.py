"""Resume Parser — extracts text from PDF, DOCX, TXT files and ZIP archives."""
import io
import os
import zipfile
import tempfile
from pathlib import Path
from typing import List, Tuple

import fitz  # PyMuPDF
from docx import Document


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file."""
    text_parts = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts).strip()


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file."""
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(para.text for para in doc.paragraphs).strip()


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text from a plain text file."""
    return file_bytes.decode("utf-8", errors="ignore").strip()


EXTRACTORS = {
    ".pdf": extract_text_from_pdf,
    ".docx": extract_text_from_docx,
    ".doc": extract_text_from_docx,
    ".txt": extract_text_from_txt,
}


def parse_single_file(filename: str, file_bytes: bytes) -> Tuple[str, str]:
    """Parse a single resume file. Returns (filename, extracted_text)."""
    ext = Path(filename).suffix.lower()
    extractor = EXTRACTORS.get(ext)
    if extractor is None:
        return filename, ""
    try:
        text = extractor(file_bytes)
        # Normalize whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return filename, "\n".join(lines)
    except Exception as e:
        print(f"[WARN] Failed to parse {filename}: {e}")
        return filename, ""


def parse_zip(zip_bytes: bytes) -> List[Tuple[str, str]]:
    """Extract and parse all resumes from a ZIP archive."""
    results = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = Path(info.filename).name
            # Skip hidden / macOS resource forks
            if name.startswith(".") or name.startswith("__"):
                continue
            ext = Path(name).suffix.lower()
            if ext not in EXTRACTORS:
                continue
            file_bytes = zf.read(info.filename)
            fname, text = parse_single_file(name, file_bytes)
            if text:
                results.append((fname, text))
    return results


def parse_uploads(files: List[Tuple[str, bytes]]) -> List[dict]:
    """
    Main entry point. Accepts a list of (filename, bytes).
    Returns a list of dicts: {"filename": str, "text": str}.
    Handles both individual files and ZIP archives.
    """
    parsed = []
    for filename, file_bytes in files:
        if filename.lower().endswith(".zip"):
            zip_results = parse_zip(file_bytes)
            for name, text in zip_results:
                parsed.append({"filename": name, "text": text})
        else:
            name, text = parse_single_file(filename, file_bytes)
            if text:
                parsed.append({"filename": name, "text": text})
    return parsed
