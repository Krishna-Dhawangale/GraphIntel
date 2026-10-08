# GraphIntel Backend

FastAPI 0.110+ asynchronous backend powering document ingestion, storage, vector indexing, and grounded RAG queries.

## Technologies
* **Python 3.12+**
* **FastAPI** & **Pydantic v2**
* **SQLAlchemy 2.0** (Async & Sync) & **Alembic**
* **MinIO** (S3-compatible storage)
* **Qdrant** (Vector database)
* **PyMuPDF**, **python-docx**, **BeautifulSoup4**, **pandas**, **tiktoken**
* **Pytest**, **Ruff**, **Black**

## Local Setup

```bash
# 1. Create and activate virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Run database migrations
alembic upgrade head

# 4. Start backend development server
uvicorn app.main:app --reload --port 8000
```

## Running Tests & Linters

```bash
# Run 19 unit & integration tests
pytest -v

# Run linter
ruff check app tests

# Run code formatter
black --check app tests
```

## API Documentation
Once running, open:
* Interactive Swagger UI: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
* ReDoc UI: [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc)
