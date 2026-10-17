import json
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research_history import ResearchHistory
from app.schemas.query import GraphPathInfo, QueryMetadata, SourceCitation
from app.schemas.research_history import (
    ResearchHistoryDetail,
    ResearchHistoryItem,
)


class ResearchHistoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_preview(self, text: str, max_chars: int = 160) -> str:
        clean = " ".join(text.split())
        return clean[:max_chars] + ("..." if len(clean) > max_chars else "")

    async def create_history_record(
        self,
        question: str,
        answer: str,
        retrieval_mode: str,
        citations: List[SourceCitation],
        graph_paths: List[GraphPathInfo],
        metadata: Optional[QueryMetadata] = None,
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
        status: str = "SUCCESS",
    ) -> ResearchHistory:
        """Create a persistent research history entry scoped to user or guest session."""
        citations_data = [c.model_dump() for c in citations]
        paths_data = [p.model_dump() for p in graph_paths]
        metadata_data = metadata.model_dump() if metadata else {}

        record = ResearchHistory(
            user_id=user_id,
            guest_session_id=guest_session_id,
            question=question,
            answer=answer,
            retrieval_mode=retrieval_mode,
            citations_json=json.dumps(citations_data),
            graph_paths_json=json.dumps(paths_data),
            metadata_json=json.dumps(metadata_data),
            status=status,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def list_history(
        self,
        user_id: Optional[str],
        guest_session_id: Optional[str],
        q: Optional[str] = None,
        retrieval_mode: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[ResearchHistoryItem], int]:
        """List history records with strict ownership isolation, filtering, and pagination."""
        query = select(ResearchHistory)

        # Strict ownership filter
        if user_id:
            query = query.where(ResearchHistory.user_id == user_id)
        elif guest_session_id:
            query = query.where(ResearchHistory.guest_session_id == guest_session_id)
        else:
            return [], 0

        # Optional filters
        if q and q.strip():
            search_term = f"%{q.strip()}%"
            query = query.where(
                (ResearchHistory.question.ilike(search_term))
                | (ResearchHistory.answer.ilike(search_term))
            )

        if retrieval_mode and retrieval_mode.lower() != "all":
            query = query.where(ResearchHistory.retrieval_mode == retrieval_mode.lower())

        if start_date:
            query = query.where(ResearchHistory.created_at >= start_date)
        if end_date:
            query = query.where(ResearchHistory.created_at <= end_date)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        count_res = await self.db.execute(count_query)
        total = count_res.scalar() or 0

        # Order and paginate
        query = query.order_by(ResearchHistory.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        records = result.scalars().all()

        items: List[ResearchHistoryItem] = []
        for r in records:
            c_count = 0
            p_count = 0
            try:
                if r.citations_json:
                    c_count = len(json.loads(r.citations_json))
            except Exception:
                pass
            try:
                if r.graph_paths_json:
                    p_count = len(json.loads(r.graph_paths_json))
            except Exception:
                pass

            items.append(
                ResearchHistoryItem(
                    id=r.id,
                    question=r.question,
                    answer=r.answer,
                    answer_preview=self._get_preview(r.answer),
                    retrieval_mode=r.retrieval_mode,
                    citations_count=c_count,
                    graph_paths_count=p_count,
                    status=r.status,
                    created_at=r.created_at,
                )
            )

        return items, total

    async def get_history_detail(
        self,
        history_id: str,
        user_id: Optional[str],
        guest_session_id: Optional[str],
    ) -> Optional[ResearchHistoryDetail]:
        """Fetch detail of a single history record enforcing strict ownership."""
        stmt = select(ResearchHistory).where(ResearchHistory.id == history_id)
        if user_id:
            stmt = stmt.where(ResearchHistory.user_id == user_id)
        elif guest_session_id:
            stmt = stmt.where(ResearchHistory.guest_session_id == guest_session_id)
        else:
            return None

        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return None

        citations = []
        if record.citations_json:
            try:
                citations = [SourceCitation(**c) for c in json.loads(record.citations_json)]
            except Exception:
                pass

        graph_paths = []
        if record.graph_paths_json:
            try:
                graph_paths = [GraphPathInfo(**p) for p in json.loads(record.graph_paths_json)]
            except Exception:
                pass

        metadata = None
        if record.metadata_json:
            try:
                metadata = QueryMetadata(**json.loads(record.metadata_json))
            except Exception:
                pass

        return ResearchHistoryDetail(
            id=record.id,
            user_id=record.user_id,
            guest_session_id=record.guest_session_id,
            question=record.question,
            answer=record.answer,
            retrieval_mode=record.retrieval_mode,
            citations=citations,
            graph_paths=graph_paths,
            metadata=metadata,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def delete_history_item(
        self,
        history_id: str,
        user_id: Optional[str],
        guest_session_id: Optional[str],
    ) -> bool:
        """Delete a single history entry verifying caller ownership."""
        stmt = select(ResearchHistory).where(ResearchHistory.id == history_id)
        if user_id:
            stmt = stmt.where(ResearchHistory.user_id == user_id)
        elif guest_session_id:
            stmt = stmt.where(ResearchHistory.guest_session_id == guest_session_id)
        else:
            return False

        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return False

        await self.db.delete(record)
        await self.db.commit()
        return True

    async def clear_history(
        self,
        user_id: Optional[str],
        guest_session_id: Optional[str],
    ) -> int:
        """Clear all history entries for current user or guest session."""
        stmt = delete(ResearchHistory)
        if user_id:
            stmt = stmt.where(ResearchHistory.user_id == user_id)
        elif guest_session_id:
            stmt = stmt.where(ResearchHistory.guest_session_id == guest_session_id)
        else:
            return 0

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount or 0

    async def migrate_guest_history(
        self,
        guest_session_id: str,
        target_user_id: str,
    ) -> int:
        """
        Transactional and idempotent migration of guest history to registered user account.
        Only updates records strictly belonging to the verified guest_session_id.
        """
        if not guest_session_id or not target_user_id:
            return 0

        stmt = (
            update(ResearchHistory)
            .where(
                ResearchHistory.guest_session_id == guest_session_id,
                ResearchHistory.user_id.is_(None),
            )
            .values(
                user_id=target_user_id,
                guest_session_id=None,
            )
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount or 0
