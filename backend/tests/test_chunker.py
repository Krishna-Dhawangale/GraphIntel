from app.providers.parsers.base import ParsedSection
from app.services.chunker import DocumentChunker
from app.services.text_processor import TextProcessor


def test_text_cleaning():
    dirty_text = "  GraphIntel   Market    Intelligence \r\n\r\n\n\n\n  Next-Gen  Platform.  "
    cleaned = TextProcessor.clean_text(dirty_text)
    assert "GraphIntel Market Intelligence" in cleaned
    assert "Next-Gen Platform." in cleaned
    # Ensure paragraphs preserved without excessive blank lines
    assert "\n\n\n" not in cleaned


def test_chunker_basic():
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)
    section = ParsedSection(
        text="This is sentence one. This is sentence two. This is sentence three. This is sentence four.",
        page_number=1,
        section="Summary",
    )
    chunks = chunker.chunk_section(section, document_id="doc-123")
    assert len(chunks) >= 1
    for c in chunks:
        assert c.document_id == "doc-123"
        assert c.page_number == 1
        assert c.token_count > 0
        assert c.text


def test_chunker_long_text():
    chunker = DocumentChunker(chunk_size=30, chunk_overlap=5)
    # Long text with multiple paragraphs
    long_text = "\n\n".join(
        [f"Paragraph {i} contains market data regarding sector trends." for i in range(15)]
    )
    section = ParsedSection(text=long_text, page_number=2, section="Sectors")
    chunks = chunker.chunk_section(section, document_id="doc-456")
    assert len(chunks) > 1
    for idx, c in enumerate(chunks):
        assert c.chunk_index == idx
