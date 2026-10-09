import re
import uuid
from typing import Any, Dict, List, Optional

import tiktoken
from pydantic import BaseModel

from app.core.config import settings
from app.providers.parsers.base import ParsedSection
from app.services.text_processor import TextProcessor

_SENTENCE_ENDINGS_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"\'])')

try:
    _GLOBAL_TOKENIZER = tiktoken.get_encoding("cl100k_base")
except Exception:
    _GLOBAL_TOKENIZER = None


class ChunkResult(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int
    text: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    token_count: int
    metadata: Dict[str, Any] = {}


class DocumentChunker:
    """Paragraph and sentence-aware chunker with configurable size and overlap."""

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = _GLOBAL_TOKENIZER

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception:
                pass
        # Fast fallback estimation: ~4 chars per token
        return max(1, len(text) // 4)

    def split_into_sentences(self, text: str) -> List[str]:
        parts = _SENTENCE_ENDINGS_RE.split(text)
        return [p.strip() for p in parts if p.strip()]

    def chunk_section(
        self,
        section: ParsedSection,
        document_id: str,
        start_chunk_index: int = 0,
    ) -> List[ChunkResult]:
        cleaned_text = TextProcessor.clean_text(section.text)
        if not cleaned_text:
            return []

        # If the whole section fits in one chunk
        token_count = self.count_tokens(cleaned_text)
        if token_count <= self.chunk_size:
            chunk = ChunkResult(
                chunk_id=str(uuid.uuid4()),
                document_id=document_id,
                chunk_index=start_chunk_index,
                text=cleaned_text,
                page_number=section.page_number,
                section=section.section,
                token_count=token_count,
                metadata={
                    **section.metadata,
                    "page": section.page_number,
                    "section": section.section,
                },
            )
            return [chunk]

        # Break by paragraphs first
        paragraphs = cleaned_text.split("\n\n")
        units: List[str] = []
        for p in paragraphs:
            p_tokens = self.count_tokens(p)
            if p_tokens > self.chunk_size:
                # If paragraph itself is too large, break by sentences
                sentences = self.split_into_sentences(p)
                for s in sentences:
                    s_tokens = self.count_tokens(s)
                    if s_tokens > self.chunk_size:
                        # Hard split by character chunking if a single sentence is giant
                        step = self.chunk_size * 4
                        for j in range(0, len(s), step):
                            units.append(s[j : j + step])
                    else:
                        units.append(s)
            else:
                units.append(p)

        # Assemble units into chunks respecting chunk_size and chunk_overlap
        chunks: List[ChunkResult] = []
        current_chunk_tuples: List[tuple] = []
        current_tokens = 0
        chunk_idx = start_chunk_index

        i = 0
        while i < len(units):
            unit = units[i]
            unit_tokens = self.count_tokens(unit)

            if not current_chunk_tuples or (current_tokens + unit_tokens <= self.chunk_size):
                current_chunk_tuples.append((unit, unit_tokens))
                current_tokens += unit_tokens
                i += 1
            else:
                chunk_text = "\n\n".join(u for u, _ in current_chunk_tuples)
                chunks.append(
                    ChunkResult(
                        chunk_id=str(uuid.uuid4()),
                        document_id=document_id,
                        chunk_index=chunk_idx,
                        text=chunk_text,
                        page_number=section.page_number,
                        section=section.section,
                        token_count=current_tokens,
                        metadata={
                            **section.metadata,
                            "page": section.page_number,
                            "section": section.section,
                        },
                    )
                )
                chunk_idx += 1

                # Calculate overlap backwards using already computed token counts
                overlap_tuples: List[tuple] = []
                overlap_tokens = 0
                for rev_u, rev_tok in reversed(current_chunk_tuples):
                    if overlap_tokens + rev_tok <= self.chunk_overlap:
                        overlap_tuples.insert(0, (rev_u, rev_tok))
                        overlap_tokens += rev_tok
                    else:
                        break

                # Ensure strictly forward progress: overlap must not contain all items
                if len(overlap_tuples) >= len(current_chunk_tuples):
                    overlap_tuples = overlap_tuples[1:]
                    overlap_tokens = sum(tok for _, tok in overlap_tuples)

                current_chunk_tuples = overlap_tuples
                current_tokens = overlap_tokens

        if current_chunk_tuples:
            chunk_text = "\n\n".join(u for u, _ in current_chunk_tuples)
            chunks.append(
                ChunkResult(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document_id,
                    chunk_index=chunk_idx,
                    text=chunk_text,
                    page_number=section.page_number,
                    section=section.section,
                    token_count=current_tokens,
                    metadata={
                        **section.metadata,
                        "page": section.page_number,
                        "section": section.section,
                    },
                )
            )

        return chunks

    def chunk_document(
        self,
        sections: List[ParsedSection],
        document_id: str,
    ) -> List[ChunkResult]:
        all_chunks: List[ChunkResult] = []
        current_idx = 0
        for section in sections:
            section_chunks = self.chunk_section(section, document_id, start_chunk_index=current_idx)
            all_chunks.extend(section_chunks)
            current_idx += len(section_chunks)
        return all_chunks
