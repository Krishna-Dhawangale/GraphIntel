from typing import List

from app.core.exceptions import UnprocessableEntityException
from app.core.logging import logger
from app.providers.parsers.base import DocumentParser, ParsedSection


class TXTParser(DocumentParser):
    def parse(self, content: bytes, filename: str) -> List[ParsedSection]:
        try:
            # Try utf-8 first, then common fallbacks
            for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
                try:
                    text = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                text = content.decode("utf-8", errors="replace")

            # Split into logical sections by double newlines
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            if not paragraphs:
                return [
                    ParsedSection(text=text.strip(), section="General", metadata={"format": "txt"})
                ]

            # Group into reasonable section blocks
            sections: List[ParsedSection] = []
            chunk_size = 5  # group 5 paragraphs per section
            for i in range(0, len(paragraphs), chunk_size):
                section_text = "\n\n".join(paragraphs[i : i + chunk_size])
                sections.append(
                    ParsedSection(
                        text=section_text,
                        section=f"Section {i // chunk_size + 1}",
                        metadata={
                            "format": "txt",
                            "paragraph_count": len(paragraphs[i : i + chunk_size]),
                        },
                    )
                )

            return sections
        except Exception as e:
            logger.error(f"Failed to parse TXT {filename}: {e}")
            raise UnprocessableEntityException(f"Failed to parse text document: {filename}")
