import os
import re
from typing import Set

from app.core.config import settings
from app.core.exceptions import BadRequestException

ALLOWED_EXTENSIONS: Set[str] = {".pdf", ".txt", ".md", ".docx", ".json", ".csv"}

ALLOWED_MIME_TYPES: Set[str] = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/json",
    "text/json",
    "text/csv",
    "application/csv",
    "application/octet-stream",  # Often sent for markdown/plain text
}


def sanitize_filename(filename: str) -> str:
    """
    Sanitize uploaded filename to prevent directory traversal and null-byte injection.
    """
    if not filename:
        raise BadRequestException("Filename cannot be empty", error_code="INVALID_FILENAME")

    # Remove null bytes
    cleaned = filename.replace("\x00", "")

    # Extract base name to remove any path components (../, /etc/, C:\)
    cleaned = os.path.basename(cleaned)
    # Also strip Windows drive letters or slashes if any slipped through
    cleaned = re.sub(r"^[a-zA-Z]:", "", cleaned)
    cleaned = cleaned.replace("\\", "/").split("/")[-1]

    # Replace suspicious characters with underscore, keeping letters, numbers, dots, dashes, underscores
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", cleaned)

    # Ensure extension is valid
    _, ext = os.path.splitext(cleaned)
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise BadRequestException(
            f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            error_code="INVALID_FILE_EXTENSION",
        )

    if not cleaned or cleaned.startswith("."):
        cleaned = f"uploaded_file{ext}"

    # Truncate if excessively long
    if len(cleaned) > 200:
        base, ext = os.path.splitext(cleaned)
        cleaned = f"{base[:190]}{ext}"

    return cleaned


def validate_file_upload(filename: str, content_type: str, file_size: int):
    """
    Validates file extension, content-type and size.
    """
    # Validate extension and sanitize
    safe_name = sanitize_filename(filename)

    # Validate size
    if file_size > settings.max_upload_size_bytes:
        raise BadRequestException(
            f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB}MB",
            error_code="FILE_TOO_LARGE",
        )

    # Validate MIME type
    if content_type and content_type.lower() not in ALLOWED_MIME_TYPES:
        # Check if text extension
        ext = os.path.splitext(safe_name)[1].lower()
        if ext not in [".txt", ".md", ".csv", ".json"]:
            raise BadRequestException(
                f"Unsupported content type '{content_type}'",
                error_code="INVALID_CONTENT_TYPE",
            )

    return safe_name
