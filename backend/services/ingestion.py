import io
import re
from pypdf import PdfReader
from core.settings import settings
from services.embeddings import encode

def extract_pages(pdf_bytes: bytes) -> list[tuple[int, str]]:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes), strict=False)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise ValueError("This PDF is password protected.") from exc
        pages = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text(extraction_mode="layout") or page.extract_text() or ""
            text = re.sub(r"[\t\r]+", " ", text)
            text = re.sub(r"[ ]{2,}", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            if text:
                pages.append((index, text))
        if not pages:
            raise ValueError("No selectable text was found. Scanned PDFs need OCR before upload.")
        if sum(len(text) for _, text in pages) < 100:
            raise ValueError("The PDF contains too little selectable text to analyze.")
        return pages
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not read this PDF: {exc}") from exc

def make_chunks(pages: list[tuple[int, str]]) -> list[dict]:
    size = settings.RAG_CHUNK_SIZE
    overlap = min(settings.RAG_CHUNK_OVERLAP, size // 2)
    result = []
    for page_number, text in pages:
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                boundary = max(text.rfind(". ", start, end), text.rfind("\n", start, end))
                if boundary > start + size // 2:
                    end = boundary + 1
            chunk = text[start:end].strip()
            if len(chunk) > 40:
                result.append({"page_number": page_number, "text": chunk})
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
    return result

def embed_chunks(chunks: list[dict]) -> list[dict]:
    vectors = encode([item["text"] for item in chunks])
    return [{**item, "embedding": vector} for item, vector in zip(chunks, vectors)]
