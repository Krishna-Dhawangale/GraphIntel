import pytest

from app.providers.embeddings.local_provider import LocalDeterministicEmbeddingProvider
from app.providers.vector_store.base import VectorRecord
from app.providers.vector_store.in_memory_store import InMemoryVectorStore


@pytest.mark.asyncio
async def test_local_embeddings():
    provider = LocalDeterministicEmbeddingProvider(dimension=384)
    assert provider.dimension == 384

    embeddings = await provider.get_embeddings(["Market intelligence", "Competitor analysis"])
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
    assert len(embeddings[1]) == 384


@pytest.mark.asyncio
async def test_vector_store_operations_and_isolation():
    store = InMemoryVectorStore()
    provider = LocalDeterministicEmbeddingProvider(dimension=384)

    # User 1 documents
    vec1 = await provider.get_embedding("Apple revenue was 90 billion")
    vec2 = await provider.get_embedding("Microsoft Azure cloud growth reached 30%")

    # User 2 document
    vec3 = await provider.get_embedding("Confidential internal strategy for User 2")

    records = [
        VectorRecord(
            id="chunk-1",
            vector=vec1,
            payload={
                "chunk_id": "chunk-1",
                "document_id": "doc-1",
                "user_id": "user-1",
                "text": "Apple revenue was 90 billion",
            },
        ),
        VectorRecord(
            id="chunk-2",
            vector=vec2,
            payload={
                "chunk_id": "chunk-2",
                "document_id": "doc-2",
                "user_id": "user-1",
                "text": "Microsoft Azure cloud growth reached 30%",
            },
        ),
        VectorRecord(
            id="chunk-3",
            vector=vec3,
            payload={
                "chunk_id": "chunk-3",
                "document_id": "doc-3",
                "user_id": "user-2",
                "text": "Confidential strategy",
            },
        ),
    ]

    await store.upsert(records)

    # Query by user-1
    query_vec = await provider.get_embedding("What was the cloud growth rate?")
    results_user1 = await store.search(query_vec, top_k=5, filter_user_id="user-1")

    assert len(results_user1) == 2
    # Ensure user-2 data is NEVER returned to user-1
    for r in results_user1:
        assert r.payload["user_id"] == "user-1"
        assert r.payload["user_id"] != "user-2"

    # Test delete by document
    await store.delete_by_document(document_id="doc-1", user_id="user-1")
    results_after_delete = await store.search(query_vec, top_k=5, filter_user_id="user-1")
    assert len(results_after_delete) == 1
    assert results_after_delete[0].payload["document_id"] == "doc-2"
