import re
import unicodedata
from typing import List


class TextProcessor:
    """Handles text cleaning, normalization, paragraph preservation, and encoding cleanup."""

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""

        # Normalize unicode (NFKC: Canonical Decomposition, followed by Canonical Composition)
        normalized = unicodedata.normalize("NFKC", text)

        # Remove null bytes and unprintable control characters, but keep newlines and tabs
        cleaned = "".join(
            ch
            for ch in normalized
            if ch in ("\n", "\r", "\t") or unicodedata.category(ch)[0] != "C"
        )

        # Standardize line breaks
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

        # Replace excessive spaces and tabs on a line with a single space
        lines: List[str] = []
        for line in cleaned.split("\n"):
            line_clean = re.sub(r"[ \t]+", " ", line).strip()
            lines.append(line_clean)

        # Re-join lines, collapsing more than two consecutive newlines into two (preserving paragraphs)
        collapsed = "\n".join(lines)
        collapsed = re.sub(r"\n{3,}", "\n\n", collapsed)

        return collapsed.strip()
