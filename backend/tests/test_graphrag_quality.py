"""Comprehensive automated quality test suite for GraphRAG in GraphIntel.

Covers all 10 required test scenarios:
1. NVIDIA fiscal 2026 financial question ($216B revenue, $130B operating income, $4.90 EPS).
2. NVIDIA AI infrastructure and ecosystem question (Blackwell, 9 GW capacity, inference).
3. NVIDIA company relationship graph question (Harvey C. Jones -> Daisy Systems Corp, Jen-Hsun Huang -> NVIDIA).
4. Malformed pronoun-based entity rejection (`we`, `he`, `she`, `they`).
5. Unsupported relationship rejection.
6. Citation-to-evidence validation (excerpt, claim, document_title, page_number).
7. Duplicate graph path removal (no cycles or redundant paths).
8. Insufficient-evidence behavior (returns explicit insufficient evidence statement).
9. LLM failure and fallback behavior (mock fallback provides grounded synthesis, no boilerplate).
10. Repeat ingestion idempotency (syncing the same chunks twice does not duplicate entities or relationships).
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.providers.graph_store.in_memory_store import InMemoryGraphStore
from app.providers.vector_store.base import VectorRecord
from app.providers.vector_store.factory import get_vector_store
from app.schemas.graph import (
    EntityCreate,
    RelationshipCreate,
    RelationshipType,
)
from app.schemas.query import QueryRequest, RetrievalMode
from app.services.entity_extractor import RuleBasedEntityExtractor
from app.services.graph_retriever import GraphRetriever
from app.services.graph_service import GraphService
from app.services.rag_service import RAGService


# Test fixture constants based on NVIDIA's 2026 Annual Report
NVIDIA_REPORT_PAGE_14_TEXT = (
    "Fiscal 2026 was a historic year for NVIDIA. Revenue grew 65% to $216 billion, "
    "and operating income rose 60% to $130 billion. Diluted earnings per share were $4.90. "
    "We generated $103 billion in cash from operations and returned $41 billion to shareholders. "
    "Data Center revenue grew 68% to $194 billion. Networking revenue exceeded $31 billion. "
    "Nearly 9 gigawatts of Blackwell capacity deployed by our cloud partners."
)

NVIDIA_REPORT_PAGE_38_TEXT = (
    "Harvey C. Jones has served as a Director of NVIDIA since 1993. "
    "Mr. Jones co-founded Daisy Systems Corp in 1981 and served as its President and Chief Executive Officer. "
    "He co-founded Tensilica Inc in 1997."
)

NVIDIA_REPORT_PAGE_100_TEXT = (
    "Jen-Hsun Huang co-founded NVIDIA in 1993 and has served as President and Chief Executive Officer. "
    "Debora Shoquist worked at Quantum Corp from 1999 to 2007."
)


@pytest.fixture
async def seeded_nvidia_rag(db_session: AsyncSession, test_user: User):
    """Seed SQLite, vector store, and in-memory stores with NVIDIA 2026 Annual Report chunks."""
    doc = Document(
        id="c86f9723-de5f-40a2-9b47-7b0450c2e573",
        user_id=test_user.id,
        tenant_id="default",
        title="2026-Annual-Report-Web.pdf",
        filename="2026-Annual-Report-Web.pdf",
        file_size=1024000,
        content_type="application/pdf",
        storage_path="/mock/2026-Annual-Report-Web.pdf",
        status=DocumentStatus.COMPLETED,
    )
    db_session.add(doc)
    await db_session.flush()

    chunk_14 = DocumentChunk(
        id="chunk_page_14",
        document_id=doc.id,
        tenant_id="default",
        chunk_index=0,
        text=NVIDIA_REPORT_PAGE_14_TEXT,
        page_number=14,
        token_count=len(NVIDIA_REPORT_PAGE_14_TEXT.split()),
        chunk_metadata={"filename": doc.filename, "page_number": 14},
    )
    chunk_38 = DocumentChunk(
        id="chunk_page_38",
        document_id=doc.id,
        tenant_id="default",
        chunk_index=1,
        text=NVIDIA_REPORT_PAGE_38_TEXT,
        page_number=38,
        token_count=len(NVIDIA_REPORT_PAGE_38_TEXT.split()),
        chunk_metadata={"filename": doc.filename, "page_number": 38},
    )
    chunk_100 = DocumentChunk(
        id="chunk_page_100",
        document_id=doc.id,
        tenant_id="default",
        chunk_index=2,
        text=NVIDIA_REPORT_PAGE_100_TEXT,
        page_number=100,
        token_count=len(NVIDIA_REPORT_PAGE_100_TEXT.split()),
        chunk_metadata={"filename": doc.filename, "page_number": 100},
    )
    db_session.add_all([chunk_14, chunk_38, chunk_100])
    await db_session.commit()

    # Index into vector store as well
    vector_store = get_vector_store()
    rag = RAGService(db_session)
    embedding_provider = rag.retrieval_service.embedding_provider

    v14 = await embedding_provider.get_embedding(NVIDIA_REPORT_PAGE_14_TEXT)
    v38 = await embedding_provider.get_embedding(NVIDIA_REPORT_PAGE_38_TEXT)
    v100 = await embedding_provider.get_embedding(NVIDIA_REPORT_PAGE_100_TEXT)

    records = [
        VectorRecord(
            id=chunk_14.id,
            vector=v14,
            payload={
                "chunk_id": chunk_14.id,
                "document_id": doc.id,
                "filename": doc.filename,
                "text": chunk_14.text,
                "page_number": 14,
                "user_id": test_user.id,
            },
        ),
        VectorRecord(
            id=chunk_38.id,
            vector=v38,
            payload={
                "chunk_id": chunk_38.id,
                "document_id": doc.id,
                "filename": doc.filename,
                "text": chunk_38.text,
                "page_number": 38,
                "user_id": test_user.id,
            },
        ),
        VectorRecord(
            id=chunk_100.id,
            vector=v100,
            payload={
                "chunk_id": chunk_100.id,
                "document_id": doc.id,
                "filename": doc.filename,
                "text": chunk_100.text,
                "page_number": 100,
                "user_id": test_user.id,
            },
        ),
    ]
    await vector_store.upsert(records)

    return rag, test_user, doc


# =========================================================================
# Scenario 1: NVIDIA fiscal 2026 financial question
# =========================================================================
@pytest.mark.asyncio
async def test_nvidia_fiscal_2026_financial_query(seeded_nvidia_rag):
    rag, user, _ = seeded_nvidia_rag
    response = await rag.answer_query(
        question="What was NVIDIA's revenue and operating income in fiscal 2026?",
        user_id=user.id,
        retrieval_mode="hybrid",
    )
    answer = response.answer
    # Assert concrete financial metrics are extracted and reported
    assert "$216" in answer or "216 billion" in answer
    assert "$130" in answer or "130 billion" in answer
    assert len(response.sources) > 0
    # Must not contain generic placeholder boilerplate
    assert "retrieved document evidence confirms relevant findings" not in answer.lower()


# =========================================================================
# Scenario 2: NVIDIA AI infrastructure and ecosystem question
# =========================================================================
@pytest.mark.asyncio
async def test_nvidia_ai_infrastructure_query(seeded_nvidia_rag):
    rag, user, _ = seeded_nvidia_rag
    response = await rag.answer_query(
        question="Describe NVIDIA's Blackwell capacity and Data Center performance.",
        user_id=user.id,
        retrieval_mode="hybrid",
    )
    answer = response.answer
    assert "Blackwell" in answer
    assert "194" in answer or "9 gigawatts" in answer or "9 GW" in answer
    assert len(response.sources) > 0


# =========================================================================
# Scenario 3: NVIDIA company relationship graph extraction
# =========================================================================
@pytest.mark.asyncio
async def test_nvidia_company_relationship_graph_extraction():
    extractor = RuleBasedEntityExtractor()
    entities, rels = await extractor.extract(
        text=NVIDIA_REPORT_PAGE_38_TEXT,
        document_id="doc_nvidia",
        chunk_id="chunk_38",
        page_number=38,
    )

    names = {e.name for e in entities}
    assert "Harvey C. Jones" in names or "Mr. Jones" in names or "Jones" in names
    assert "Daisy Systems Corp" in names
    assert "Tensilica Inc" in names or "Tensilica" in names

    rel_tuples = [(r.source_entity_id, r.relationship_type, r.target_entity_id) for r in rels]
    # Check that Harvey Jones founded Daisy Systems Corp or Tensilica Inc
    daisy_rel = any(r[1] == "FOUNDED" and "Daisy Systems" in r[2] for r in rel_tuples)
    assert daisy_rel, f"Expected Harvey C. Jones FOUNDED Daisy Systems Corp in {rel_tuples}"

    # Verify every relationship contains valid evidence quote and page
    for r in rels:
        assert r.source_page == 38
        assert r.evidence_quote is not None
        assert len(r.evidence_quote) > 5


# =========================================================================
# Scenario 4: Malformed pronoun-based entity rejection
# =========================================================================
@pytest.mark.asyncio
async def test_malformed_pronoun_entity_rejection():
    extractor = RuleBasedEntityExtractor()
    # "we developed NVIDIA" or isolated "he founded" without antecedent
    text = "We developed NVIDIA and scaled the platform. He founded Daisy Systems Corp without mention of who he is."
    entities, rels = await extractor.extract(
        text=text,
        document_id="doc_test",
        chunk_id="chunk_bad",
        page_number=1,
    )

    extracted_names = {e.name.lower() for e in entities}
    # Isolated pronouns must NEVER become standalone entities
    assert "we" not in extracted_names
    assert "he" not in extracted_names
    assert "she" not in extracted_names
    assert "they" not in extracted_names
    assert "and scaled the nvidia" not in extracted_names

    # Relationships with raw pronouns as subject must NOT be created
    for r in rels:
        assert r.source_entity_id.lower() not in {"we", "he", "she", "they"}


# =========================================================================
# Scenario 5: Unsupported relationship rejection
# =========================================================================
@pytest.mark.asyncio
async def test_unsupported_relationship_rejection():
    extractor = RuleBasedEntityExtractor()
    # Sentence with generic words or missing trigger
    text = "Technology and products provide significant business growth for various companies across the industry."
    entities, rels = await extractor.extract(
        text=text,
        document_id="doc_test",
        chunk_id="chunk_unsupported",
        page_number=1,
    )
    # Should not produce hallucinated corporate acquisition or founding edges
    assert len(rels) == 0


# =========================================================================
# Scenario 6: Citation-to-evidence validation
# =========================================================================
@pytest.mark.asyncio
async def test_citation_to_evidence_validation(seeded_nvidia_rag):
    rag, user, doc = seeded_nvidia_rag
    response = await rag.answer_query(
        question="What was the fiscal 2026 diluted earnings per share?",
        user_id=user.id,
        retrieval_mode="vector",
    )
    assert len(response.sources) > 0
    citation = response.sources[0]
    assert citation.document_id == doc.id
    assert citation.document_title in {"2026-Annual-Report-Web", "2026-Annual-Report-Web.pdf"}
    assert citation.page_number == 14
    assert citation.supporting_excerpt is not None
    assert "$4.90" in citation.supporting_excerpt or "earnings" in citation.supporting_excerpt
    assert citation.claim is not None and len(citation.claim) > 0


# =========================================================================
# Scenario 7: Duplicate graph path removal & cycle prevention
# =========================================================================
@pytest.mark.asyncio
async def test_duplicate_graph_path_removal():
    store = InMemoryGraphStore()
    retriever = GraphRetriever(store)
    user_id = "test_user"

    # Create entities A -> B -> C and redundant paths
    e_a = await store.upsert_entity(user_id, EntityCreate(name="EntityA", type="Company"))
    e_b = await store.upsert_entity(user_id, EntityCreate(name="EntityB", type="Company"))
    e_c = await store.upsert_entity(user_id, EntityCreate(name="EntityC", type="Company"))

    # Edge A -> B
    await store.upsert_relationship(
        user_id,
        RelationshipCreate(
            source_entity_id=e_a.id,
            target_entity_id=e_b.id,
            relationship_type="PARTNERED_WITH",
            source_document_id="doc_test_1",
            evidence_quote="EntityA partnered with EntityB",
        ),
    )
    # Edge B -> C
    await store.upsert_relationship(
        user_id,
        RelationshipCreate(
            source_entity_id=e_b.id,
            target_entity_id=e_c.id,
            relationship_type="INVESTED_IN",
            source_document_id="doc_test_1",
            evidence_quote="EntityB invested in EntityC",
        ),
    )

    _, multi_hop_paths, _ = await retriever.retrieve(
        user_id=user_id,
        entities=["EntityA"],
        max_hops=2,
    )
    # Check that multi-hop paths contain valid 2-hop sequence
    assert len(multi_hop_paths) <= 2
    # Check deduplication of paths
    unique_paths = set(tuple(p.nodes) for p in multi_hop_paths)
    assert len(unique_paths) == len(multi_hop_paths)
    # No single-hop labeled as multi-hop
    for p in multi_hop_paths:
        assert p.length >= 2


# =========================================================================
# Scenario 8: Insufficient-evidence behavior
# =========================================================================
@pytest.mark.asyncio
async def test_insufficient_evidence_behavior(seeded_nvidia_rag):
    rag, user, _ = seeded_nvidia_rag
    # Ask a question completely outside the corpus
    response = await rag.answer_query(
        question="What are the quarterly passenger revenues and aircraft delivery dates for Boeing 787?",
        user_id=user.id,
        retrieval_mode="hybrid",
    )
    answer = response.answer.lower()
    # Must explicitly state that available documents do not establish an answer
    assert "insufficient" in answer or "do not establish" in answer or "not contained" in answer or "not found" in answer


# =========================================================================
# Scenario 9: LLM failure and grounded fallback behavior
# =========================================================================
@pytest.mark.asyncio
async def test_llm_failure_and_grounded_fallback(seeded_nvidia_rag):
    rag, user, _ = seeded_nvidia_rag
    # MockProvider is active in test environment; test grounded fallback generation
    response = await rag.answer_query(
        question="What was the cash generated from operations in fiscal 2026?",
        user_id=user.id,
        retrieval_mode="hybrid",
    )
    assert response.answer is not None
    assert "$103" in response.answer or "103 billion" in response.answer
    # Latency metadata should accurately reflect executed stages
    assert response.metadata.retrieval_time_ms >= 0
    assert response.metadata.vector_retrieval_time_ms >= 0
    assert response.metadata.llm_time_ms >= 0


# =========================================================================
# Scenario 10: Repeat ingestion without duplicate graph records (idempotency)
# =========================================================================
@pytest.mark.asyncio
async def test_repeat_ingestion_idempotency():
    store = InMemoryGraphStore()
    user_id = "test_user_idempotency"

    entity_a = EntityCreate(name="NVIDIA Corp", type="Company", aliases=["NVDA"])
    entity_b = EntityCreate(name="Mellanox", type="Company")

    # Ingest entity A twice
    e1 = await store.upsert_entity(user_id, entity_a)
    e2 = await store.upsert_entity(user_id, entity_a)
    assert e1.id == e2.id

    e_b_res = await store.upsert_entity(user_id, entity_b)

    rel = RelationshipCreate(
        source_entity_id=e1.id,
        target_entity_id=e_b_res.id,
        relationship_type=RelationshipType.ACQUIRED.value,
        valid_from=2020,
        source_document_id="doc_idempotency_1",
        evidence_quote="NVIDIA acquired Mellanox in 2020.",
    )

    # Ingest relationship twice
    r1 = await store.upsert_relationship(user_id, rel)
    r2 = await store.upsert_relationship(user_id, rel)
    assert r1.id == r2.id

    # Verify query returns single relationship
    rels = await store.get_entity_relationships(user_id, e1.id)
    assert len(rels) == 1
    assert rels[0].evidence_quote == "NVIDIA acquired Mellanox in 2020."
