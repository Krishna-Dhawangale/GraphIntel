# GraphIntel API Specification (v1)

Base URL: `/api/v1`

Interactive Swagger Documentation: `http://localhost:8000/api/v1/docs`  
ReDoc: `http://localhost:8000/api/v1/redoc`

---

## 1. Health

### `GET /api/v1/health`
Returns system status and connectivity of database, storage, and vector store.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "ok",
    "storage": "ok",
    "vector_store": "ok"
  }
}
```

---

## 2. Authentication

### `POST /api/v1/auth/register`
Create a new user account.

**Request Body:**
```json
{
  "email": "analyst@firm.com",
  "password": "StrongPassword123!",
  "full_name": "Market Researcher"
}
```

**Response (201 Created):**
```json
{
  "id": "58c2780e-3fa5-45ec-974d-7ec794be10f6",
  "email": "analyst@firm.com",
  "full_name": "Market Researcher",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2026-10-04T01:00:00Z",
  "updated_at": "2026-10-04T01:00:00Z"
}
```

### `POST /api/v1/auth/login/json`
Authenticate and obtain JWT bearer token.

**Request Body:**
```json
{
  "email": "analyst@firm.com",
  "password": "StrongPassword123!"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### `GET /api/v1/auth/me`
*Requires `Authorization: Bearer <token>`*

---

## 3. Documents & Ingestion

### `POST /api/v1/documents`
*Requires `Authorization: Bearer <token>`*  
Multipart file upload.

**Query Parameters:**
* `sync_process` (boolean, default: `true`): If `true`, completes chunking, embedding, and vector upsert synchronously before returning.

**Form Data:**
* `file`: Binary file (PDF, DOCX, TXT, HTML, CSV, JSON)
* `title` (optional): User title

**Response (201 Created):**
```json
{
  "id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
  "user_id": "58c2780e-3fa5-45ec-974d-7ec794be10f6",
  "title": "Q3 10-Q Report",
  "filename": "q3_10q.pdf",
  "file_size": 245102,
  "content_type": "application/pdf",
  "storage_path": "users/58c2780e-3fa5-45ec-974d-7ec794be10f6/documents/f81d4fae-7dec-11d0-a765-00a0c91e6bf6/q3_10q.pdf",
  "status": "COMPLETED",
  "error_message": null,
  "doc_metadata": {
    "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  "created_at": "2026-10-04T01:05:00Z",
  "updated_at": "2026-10-04T01:05:02Z"
}
```

### `GET /api/v1/documents`
List user documents.
* `skip` (int, default: 0)
* `limit` (int, default: 50)

### `GET /api/v1/documents/{id}`
Retrieve document metadata and chunk count.

### `GET /api/v1/documents/{id}/status`
Retrieve ingestion status (`UPLOADED`, `PROCESSING`, `COMPLETED`, `FAILED`).

### `GET /api/v1/documents/{id}/chunks`
Retrieve chunks for a document.

### `DELETE /api/v1/documents/{id}`
Deletes document record, versions, chunks, MinIO object, and Qdrant vector points.

---

## 4. Query & RAG

### `POST /api/v1/query`
Execute grounded semantic retrieval.

**Request Body:**
```json
{
  "question": "What was the year-over-year revenue growth?",
  "top_k": 5,
  "document_ids": []
}
```

**Response (200 OK):**
```json
{
  "id": "c1f7a012-e567-48f1-a1d2-9cb8939c4f01",
  "question": "What was the year-over-year revenue growth?",
  "answer": "Revenue increased by 25% year-over-year reaching $120 million [1].",
  "sources": [
    {
      "document_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
      "filename": "q3_10q.pdf",
      "page_number": 2,
      "section": "Financial Highlights",
      "chunk_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "citation_order": 1,
      "relevance_score": 0.892
    }
  ],
  "retrieved_chunks": [
    {
      "chunk_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "document_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
      "filename": "q3_10q.pdf",
      "text": "Net revenue increased by 25% to $120 million...",
      "page_number": 2,
      "section": "Financial Highlights",
      "score": 0.892
    }
  ],
  "metadata": {
    "retrieval_time_ms": 24,
    "llm_time_ms": 280,
    "total_time_ms": 304,
    "chunks_retrieved": 1,
    "model_used": "gpt-4o-mini"
  }
}
```

### `GET /api/v1/query/history`
Retrieve past questions and answers for current user.
