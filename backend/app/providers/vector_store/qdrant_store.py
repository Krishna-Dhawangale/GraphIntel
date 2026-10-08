from typing import List, Optional

from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings
from app.core.logging import logger
from app.providers.vector_store.base import VectorRecord, VectorSearchResult, VectorStore


class QdrantVectorStore(VectorStore):
    def __init__(
        self,
        host: str = settings.QDRANT_HOST,
        port: int = settings.QDRANT_PORT,
        collection_name: str = settings.QDRANT_COLLECTION_NAME,
        api_key: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.client = AsyncQdrantClient(
            host=self.host,
            port=self.port,
            api_key=api_key or settings.QDRANT_API_KEY or None,
            timeout=10,
        )

    async def create_collection(self, dimension: int) -> bool:
        try:
            collections = await self.client.get_collections()
            existing_names = [c.name for c in collections.collections]
            if self.collection_name not in existing_names:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=dimension,
                        distance=models.Distance.COSINE,
                    ),
                )
                logger.info(f"Created Qdrant collection: {self.collection_name} (dim={dimension})")
            return True
        except Exception as e:
            logger.error(f"Failed to create/check Qdrant collection: {e}")
            return False

    async def upsert(self, records: List[VectorRecord]) -> bool:
        if not records:
            return True
        try:
            # Ensure collection exists using dimension of first record
            await self.create_collection(dimension=len(records[0].vector))

            points = [
                models.PointStruct(
                    id=record.id,
                    vector=record.vector,
                    payload=record.payload,
                )
                for record in records
            ]

            await self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upsert points to Qdrant: {e}")
            raise

    async def search(
        self,
        query_vector: List[float],
        top_k: int,
        filter_user_id: str,
        filter_document_ids: Optional[List[str]] = None,
    ) -> List[VectorSearchResult]:
        try:
            # Enforce user ownership
            must_conditions: List[models.Condition] = [
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=filter_user_id),
                )
            ]

            if filter_document_ids:
                must_conditions.append(
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchAny(any=filter_document_ids),
                    )
                )

            filter_query = models.Filter(must=must_conditions)

            search_result = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=filter_query,
            )

            results: List[VectorSearchResult] = []
            for hit in search_result:
                results.append(
                    VectorSearchResult(
                        id=str(hit.id),
                        score=float(hit.score),
                        payload=hit.payload or {},
                    )
                )
            return results
        except Exception as e:
            logger.error(f"Error performing search in Qdrant: {e}")
            return []

    async def delete(self, ids: List[str]) -> bool:
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=ids),
                wait=True,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete points from Qdrant: {e}")
            return False

    async def delete_by_document(self, document_id: str, user_id: str) -> bool:
        try:
            filter_selector = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id", match=models.MatchValue(value=document_id)
                    ),
                    models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id)),
                ]
            )
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=filter_selector),
                wait=True,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete document vectors from Qdrant: {e}")
            return False

    async def health_check(self) -> bool:
        try:
            await self.client.get_collections()
            return True
        except Exception:
            return False
