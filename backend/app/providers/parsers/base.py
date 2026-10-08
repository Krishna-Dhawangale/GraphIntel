from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ParsedSection(BaseModel):
    """Represents a parsed unit of a document (page, section, sheet, or block)."""

    text: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    metadata: Dict[str, Any] = {}


class DocumentParser(ABC):
    """Base abstract class for document parsers."""

    @abstractmethod
    def parse(self, content: bytes, filename: str) -> List[ParsedSection]:
        """Parse raw file bytes into structured sections."""
        pass
