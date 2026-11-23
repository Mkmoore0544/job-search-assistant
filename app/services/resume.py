from pathlib import Path

from pypdf import PdfReader
from docx import Document


MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def extract_resume_text(path: str) -> str:
    file_path = Path(path)
    if file_path.suffix.lower() == ".pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(file_path)).pages)
    if file_path.suffix.lower() == ".docx":
        return "\n".join(paragraph.text for paragraph in Document(str(file_path)).paragraphs)
    raise ValueError("Only PDF and DOCX resumes are supported.")
