from typing import List

import fitz  # PyMuPDF

from app.core.exceptions import UnprocessableEntityException
from app.core.logging import logger
from app.providers.parsers.base import DocumentParser, ParsedSection


class PDFParser(DocumentParser):
    def parse(self, content: bytes, filename: str) -> List[ParsedSection]:
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            sections: List[ParsedSection] = []

            for page_index in range(len(doc)):
                page = doc[page_index]
                text = page.get_text("text")
                if not text or not text.strip():
                    continue

                page_num = page_index + 1
                sections.append(
                    ParsedSection(
                        text=text.strip(),
                        page_number=page_num,
                        section=f"Page {page_num}",
                        metadata={
                            "page": page_num,
                            "total_pages": len(doc),
                            "format": "pdf",
                        },
                    )
                )

            doc.close()
            if not sections:
                sections.append(
                    ParsedSection(
                        text="",
                        page_number=1,
                        section="Empty Document",
                        metadata={"format": "pdf", "empty": True},
                    )
                )
            return sections
        except Exception as e:
            logger.error(f"Failed to parse PDF {filename}: {e}")
            raise UnprocessableEntityException(f"Failed to parse PDF document: {filename}")
