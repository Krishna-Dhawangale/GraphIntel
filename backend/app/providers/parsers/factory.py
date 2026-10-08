import os
from typing import Dict, Type

from app.core.exceptions import BadRequestException
from app.providers.parsers.base import DocumentParser
from app.providers.parsers.csv_parser import CSVParser
from app.providers.parsers.docx_parser import DOCXParser
from app.providers.parsers.html_parser import HTMLParser
from app.providers.parsers.json_parser import JSONParser
from app.providers.parsers.pdf_parser import PDFParser
from app.providers.parsers.txt_parser import TXTParser

PARSER_REGISTRY: Dict[str, Type[DocumentParser]] = {
    ".pdf": PDFParser,
    ".docx": DOCXParser,
    ".html": HTMLParser,
    ".htm": HTMLParser,
    ".txt": TXTParser,
    ".md": TXTParser,
    ".text": TXTParser,
    ".csv": CSVParser,
    ".json": JSONParser,
}

MIME_REGISTRY: Dict[str, Type[DocumentParser]] = {
    "application/pdf": PDFParser,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DOCXParser,
    "text/html": HTMLParser,
    "text/plain": TXTParser,
    "text/markdown": TXTParser,
    "text/csv": CSVParser,
    "application/json": JSONParser,
}


def get_parser(filename: str, content_type: str = "") -> DocumentParser:
    """Resolve and return appropriate DocumentParser based on file extension and MIME type."""
    ext = os.path.splitext(filename.lower())[1]
    if ext in PARSER_REGISTRY:
        return PARSER_REGISTRY[ext]()

    clean_content_type = content_type.split(";")[0].strip().lower()
    if clean_content_type in MIME_REGISTRY:
        return MIME_REGISTRY[clean_content_type]()

    supported = ", ".join(list(PARSER_REGISTRY.keys()))
    raise BadRequestException(
        f"Unsupported file format '{ext or content_type}'. Supported extensions: {supported}",
        error_code="UNSUPPORTED_MEDIA_TYPE",
    )
