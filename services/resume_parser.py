from pathlib import Path

from docx import Document
from PyPDF2 import PdfReader


def extract_text_from_file(path):
    path = Path(path)
    extension = path.suffix.lower()

    if extension == ".pdf":
        return extract_pdf_text(path)
    if extension == ".docx":
        return extract_docx_text(path)
    if extension == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    return ""


def extract_pdf_text(path):
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def extract_docx_text(path):
    document = Document(str(path))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    return "\n".join(paragraphs)
