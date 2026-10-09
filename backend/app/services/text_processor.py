import re
import unicodedata
from typing import List

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


class TextProcessor:
    """Handles high-performance text cleaning, normalization, paragraph preservation, and encoding cleanup."""

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""

        # Normalize unicode (NFKC: Canonical Decomposition, followed by Canonical Composition)
        normalized = unicodedata.normalize("NFKC", text)

        # Remove null bytes and unprintable control characters via fast compiled regex
        cleaned = _CONTROL_CHAR_RE.sub("", normalized)

        # Standardize line breaks
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

        # Replace excessive spaces and tabs on lines
        lines = [_MULTI_SPACE_RE.sub(" ", line).strip() for line in cleaned.split("\n")]

        # Re-join lines, collapsing more than two consecutive newlines into two (preserving paragraphs)
        collapsed = "\n".join(lines)
        return _MULTI_NEWLINE_RE.sub("\n\n", collapsed).strip()
