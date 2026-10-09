import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestException, PayloadTooLargeException
from app.core.file_security import sanitize_filename, validate_file_upload
from app.core.logging import log_event, logger
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentStatus, DocumentVersion
from app.models.ingestion import IngestionJob, JobStatus
from app.providers.embeddings.factory import get_embedding_provider
from app.providers.parsers.factory import get_parser
from app.providers.storage.factory import get_storage_provider
from app.providers.vector_store.base import VectorRecord
from app.providers.vector_store.factory import get_vector_store
from app.services.chunker import DocumentChunker
from app.services.graph_service import GraphService


class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = get_storage_provider()
        self.embedding_provider = get_embedding_provider()
        self.vector_store = get_vector_store()
        self.chunker = DocumentChunker(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

    async def upload_document(
        self,
        file: UploadFile,
        user_id: str,
        tenant_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Document:
        """Initial document upload, validation, idempotency check, and storage in object storage."""
        if not file.filename:
            raise BadRequestException("Missing filename", error_code="MISSING_FILENAME")

        content = await file.read()
        file_size = len(content)

        # Validate MIME, extension, and size
        content_type = file.content_type or "application/octet-stream"
        safe_name = validate_file_upload(file.filename, content_type, file_size)

        # Compute content hash (SHA-256) for idempotency
        content_hash = hashlib.sha256(content).hexdigest()
        effective_tenant = tenant_id or user_id

        # Idempotency check: see if identical file is already active for this tenant
        existing_stmt = select(Document).where(
            Document.tenant_id == effective_tenant,
            Document.content_hash == content_hash,
            Document.is_deleted == False,
        )
        existing_res = await self.db.execute(existing_stmt)
        existing_doc = existing_res.scalar_one_or_none()

        if existing_doc and existing_doc.status == DocumentStatus.COMPLETED:
            logger.info(
                f"Idempotent upload: document with hash {content_hash} already exists as {existing_doc.id}"
            )
            return existing_doc

        doc_id = str(uuid.uuid4())
        doc_title = title.strip() if title and title.strip() else os.path.splitext(safe_name)[0]

        # Secure storage path
        storage_path = f"tenants/{effective_tenant}/documents/{doc_id}/{safe_name}"

        # Upload to MinIO/Local Storage
        await self.storage.upload(content, storage_path, content_type=content_type)

        # Create Document record
        doc = Document(
            id=doc_id,
            user_id=user_id,
            tenant_id=effective_tenant,
            title=doc_title,
            filename=safe_name,
            file_size=file_size,
            content_type=content_type,
            storage_path=storage_path,
            content_hash=content_hash,
            status=DocumentStatus.UPLOADED,
            is_deleted=False,
            doc_metadata={
                "original_filename": file.filename,
                "content_type": content_type,
                "checksum": content_hash,
            },
        )
        self.db.add(doc)

        # Create Version record
        version = DocumentVersion(
            document_id=doc_id,
            version_number=1,
            storage_path=storage_path,
            file_size=file_size,
            checksum=content_hash,
        )
        self.db.add(version)

        # Create initial IngestionJob
        job = IngestionJob(
            document_id=doc_id,
            tenant_id=effective_tenant,
            status=JobStatus.PENDING,
            retry_count=0,
        )
        self.db.add(job)

        await self.db.commit()
        await self.db.refresh(doc)

        log_event(
            "document_uploaded",
            f"Document {doc_id} uploaded by user {user_id} in tenant {effective_tenant}",
            document_id=doc_id,
            user_id=user_id,
            tenant_id=effective_tenant,
            filename=safe_name,
            size=file_size,
        )

        return doc

    async def process_document(self, document_id: str, user_id: str) -> bool:
        """Complete parsing, chunking, embedding, and vector + graph storage pipeline."""
        stmt = select(Document).where(Document.id == document_id)
        res = await self.db.execute(stmt)
        doc = res.scalar_one_or_none()

        if not doc:
            logger.error(f"Cannot process document: {document_id} not found")
            return False

        # Find latest job
        job_stmt = (
            select(IngestionJob)
            .where(IngestionJob.document_id == document_id)
            .order_by(IngestionJob.created_at.desc())
        )
        job_res = await self.db.execute(job_stmt)
        job = job_res.scalars().first()
        if not job:
            job = IngestionJob(
                document_id=document_id,
                tenant_id=doc.tenant_id,
                status=JobStatus.RUNNING,
            )
            self.db.add(job)

        # Update status to processing
        doc.status = DocumentStatus.PROCESSING
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        await self.db.commit()

        log_event(
            "document_processing_started",
            f"Processing started for document {document_id}",
            document_id=document_id,
            user_id=user_id,
        )

        try:
            # 1. Download file from storage
            content = await self.storage.download(doc.storage_path)

            # 2. Parse document
            parser = get_parser(doc.filename, doc.content_type)
            sections = parser.parse(content, doc.filename)

            # 3. Clean and Chunk
            chunks = self.chunker.chunk_document(sections, doc.id)

            if not chunks:
                raise ValueError("No text content could be extracted from document.")

            # 4. Save chunks to PostgreSQL with deterministic chunk IDs
            db_chunks: List[DocumentChunk] = []
            for chunk_res in chunks:
                # Deterministic chunk ID based on document and chunk index
                chunk_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{doc.id}_{chunk_res.chunk_index}"))
                db_chunk = DocumentChunk(
                    id=chunk_uuid,
                    document_id=doc.id,
                    tenant_id=doc.tenant_id,
                    chunk_index=chunk_res.chunk_index,
                    text=chunk_res.text,
                    page_number=chunk_res.page_number,
                    section=chunk_res.section,
                    token_count=chunk_res.token_count,
                    chunk_metadata=chunk_res.metadata,
                )
                db_chunks.append(db_chunk)

            self.db.add_all(db_chunks)
            await self.db.flush()

            # 5. Generate embeddings in batches
            texts_to_embed = [c.text for c in chunks]
            embeddings = await self.embedding_provider.get_embeddings(texts_to_embed)

            # 6. Store in Vector Store (Qdrant / Memory) with tenant and user scoping
            vector_records: List[VectorRecord] = []
            for idx, c in enumerate(chunks):
                chunk_uuid = db_chunks[idx].id
                vector_records.append(
                    VectorRecord(
                        id=chunk_uuid,
                        vector=embeddings[idx],
                        payload={
                            "chunk_id": chunk_uuid,
                            "document_id": doc.id,
                            "user_id": user_id,
                            "tenant_id": doc.tenant_id,
                            "filename": doc.filename,
                            "page_number": c.page_number,
                            "section": c.section,
                            "text": c.text,
                        },
                    )
                )

            await self.vector_store.upsert(vector_records)

            # 7. Knowledge Graph Synchronization (Batch Processed)
            try:
                graph_service = GraphService()
                graph_chunk_payloads = [
                    {
                        "chunk_id": db_chunks[idx].id,
                        "text": c.text,
                        "page_number": c.page_number,
                    }
                    for idx, c in enumerate(chunks)
                ]
                stats = await graph_service.sync_chunks_to_graph(
                    user_id=user_id,
                    document_id=doc.id,
                    chunks=graph_chunk_payloads,
                )
                total_ent = stats.get("entities_synced", 0)
                total_rel = stats.get("relationships_synced", 0)

                log_event(
                    "graph_sync_completed",
                    f"Document {document_id} synced to Knowledge Graph ({total_ent} entities, {total_rel} relationships)",
                    document_id=document_id,
                    user_id=user_id,
                    entities_synced=total_ent,
                    relationships_synced=total_rel,
                )
            except Exception as ge:
                logger.warning(f"Knowledge Graph sync warning for doc {document_id}: {ge}")

            # 8. Update status to COMPLETED
            doc.status = DocumentStatus.COMPLETED
            doc.error_message = None
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()

            return True

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Document processing failed for {document_id}: {e}")
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            self.db.add(doc)
            self.db.add(job)
            await self.db.commit()
            return False
