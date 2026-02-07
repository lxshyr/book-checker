# Book Checker MVP - Implementation Plan

## Context

Build a service that takes a photo of books (like `data/PXL_20260117_190210631.jpg` which shows ~30 children's books on a table), identifies each book via a Vision Language Model, and checks availability at the Mountain View Public Library.

**Key discovery:** The library catalogue at `librarycatalog.mountainview.gov` runs **Vega by Innovative (iii)**, NOT Aspen Discovery. The API is a JSON REST API at `https://na5.iiivega.com`.

## Approach: VLM-First Pipeline

Send the full image to a VLM in a single API call to identify all books, then look each one up on the library catalogue. This is the simplest path to a working MVP with 85-95% accuracy.

**Two VLM backends** (selectable via config):
1. **GPT-4o** (default) — via OpenAI API, ~$0.01-0.03/image
2. **Open-source via vLLM** — Qwen2.5-VL (best open-source VLM for OCR/text extraction), runs locally. Since vLLM serves an OpenAI-compatible API, both backends use the same `openai` Python client — just different `base_url` and `model` settings.

```
Image → VLM (GPT-4o or Qwen2.5-VL via vLLM)
      → Open Library API (enrich with ISBNs, optional)
      → Vega API (search catalogue + get availability)
      → Combined JSON response
```

## Library API (Verified)

```
POST https://na5.iiivega.com/api/search-result/search/format-groups
Headers:
  iii-customer-domain: mvpl.na5.iiivega.com
  iii-host-domain: librarycatalog.mountainview.gov
  api-version: 2
  Content-Type: application/json
Body: {"searchText": "Wild Robot", "pageNum": 0, "pageSize": 3}
```

Search syntax: `"t:(Wild Robot)"` for title, `"a:(Peter Brown)"` for author, plain ISBN string for ISBN search.

Response includes: title, author, availability status, call number, location, ISBNs, edition info, cover URLs - all in one call.

## Project Structure

```
book-checker/
  pyproject.toml
  .env.example                    # OPENAI_API_KEY (already exists)
  data/                           # Sample images (already exists)
  src/book_checker/
    __init__.py
    config.py                     # Pydantic settings from .env
    models.py                     # All data models (IdentifiedBook, LibraryResult, etc.)
    vision.py                     # GPT-4o Vision book identification
    library_client.py             # Vega API client for Mountain View Library
    open_library.py               # Open Library API for ISBN enrichment
    pipeline.py                   # Orchestrator: identify → enrich → lookup
    main.py                       # FastAPI app with POST /v1/books/check
  scripts/
    test_vision.py                # Standalone: test VLM on sample image
    test_library.py               # Standalone: test library search
    test_pipeline.py              # Standalone: end-to-end test
  tests/
    conftest.py
    test_models.py
    test_library_client.py
    test_pipeline.py
```

## Dependencies

`fastapi`, `uvicorn[standard]`, `openai` (works for both GPT-4o and vLLM's OpenAI-compatible API), `httpx`, `pydantic`, `pydantic-settings`, `python-multipart`, `python-dotenv`

Dev: `pytest`, `pytest-asyncio`, `pytest-httpx`, `ruff`

## Implementation Order

### Step 1: Project skeleton + config + models
- `pyproject.toml`, `config.py`, `models.py`, `__init__.py`
- Models: `IdentifiedBook`, `LibraryAvailability`, `LibraryResult`, `BookResult`, `CheckBooksResponse`
- Config: `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4o`), `OPENAI_BASE_URL` (default `None` = OpenAI; set to `http://localhost:8000/v1` for local vLLM)
- For vLLM: user runs `vllm serve Qwen/Qwen2.5-VL-7B-Instruct` separately, then sets `OPENAI_BASE_URL=http://localhost:8000/v1` and `OPENAI_MODEL=Qwen/Qwen2.5-VL-7B-Instruct`

### Step 2: Library client (highest risk — undocumented API)
- `library_client.py`: POST to Vega API with required headers
- Search by title (`t:(title)`), by ISBN, by keyword
- Parse `materialTabs` for availability/format/location/call number
- Test with `scripts/test_library.py` against real API

### Step 3: Vision module
- `vision.py`: Send image as base64 via OpenAI client, parse JSON list of books
- Uses `openai.AsyncOpenAI(api_key=..., base_url=...)` — works for both GPT-4o and vLLM
- Structured prompt requesting title, author, series, confidence, notes
- Handle markdown-fenced JSON responses
- Test with `scripts/test_vision.py` on sample image

### Step 4: Open Library client (low risk, optional enrichment)
- `open_library.py`: Search `openlibrary.org/search.json` for ISBN enrichment
- Fallback-safe — failures just skip ISBN enrichment

### Step 5: Pipeline orchestrator
- `pipeline.py`: Wire identify → enrich → library lookup
- `asyncio.Semaphore(5)` to throttle concurrent library requests
- ISBN search first, fall back to title/author search
- Test with `scripts/test_pipeline.py` end-to-end

### Step 6: FastAPI endpoint
- `main.py`: `POST /v1/books/check` accepts image upload, returns `CheckBooksResponse`
- Input validation (file type, max 20MB)
- `GET /health` endpoint

### Step 7: Unit tests
- Mock external APIs with `pytest-httpx`
- Test parsing logic, edge cases, error handling

## Error Handling

- **VLM failures**: Fail the request (no fallback without the identification step)
- **Per-book library lookup failures**: Don't fail the whole request; return `found: false` for that book
- **Open Library failures**: Silently skip ISBN enrichment, fall back to title search
- **Concurrency**: Semaphore of 5 concurrent library requests to avoid overwhelming the API

## Verification

1. `scripts/test_library.py` — search "Wild Robot", "Wings of Fire", ISBN `9780316382007`; verify availability data returned
2. `scripts/test_vision.py` — run on `data/PXL_20260117_190210631.jpg`; verify 20+ books identified
3. `scripts/test_pipeline.py` — full end-to-end; verify books identified AND matched in library
4. `curl -X POST -F "file=@data/PXL_20260117_190210631.jpg" http://localhost:8000/v1/books/check` — verify JSON response
