# Book-Checker API: Architecture & Components

This system ingests a photo that may contain **many books at once** (like the attached image: mixed orientations, partial occlusion, stacks, glare), identifies the books, and checks their availability at local libraries.

## Goals
- Identify **multiple books per image**, with per-book confidence and explainability.
- Prefer **ISBN-based** identification when possible; fall back to title/author matching.
- Return **library availability** normalized across different library systems.
- Provide an **async job flow** for heavier workloads; optionally support sync for small requests.

## Non-Goals (V1)
- Perfect identification from heavily occluded spines only.
- Real-time video processing.
- Full “shopping cart” UX (this is API-only).

## High-Level Architecture
```mermaid
flowchart LR
  C[Client] -->|POST /v1/books/identify| API[API Service]
  API --> OBJ[(Object Store: images/crops)]
  API --> Q[(Queue)]
  API --> DB[(DB)]
  API --> R[(Redis Cache)]

  Q --> W[Worker Pool]
  W --> PP[Preprocess]
  PP --> DET[Book/Cover Detection]
  DET --> RECT[Rectify & Crop Covers]
  RECT --> OCR[OCR + Text Parsing]
  RECT --> EMB[Cover Embeddings (optional)]

  OCR --> RES[Metadata Resolver]
  EMB --> RES
  RES --> MERGE[Candidate Merge & Dedup]
  MERGE --> LIB[Library Availability Service]
  LIB --> ADPT[Library Connectors/Adapters]

  ADPT --> EXT1[(Library System A)]
  ADPT --> EXT2[(Library System B)]

  LIB --> DB
  MERGE --> DB
  C -->|GET /v1/jobs/{id}| API
```

## Components

### 1) API Service
Responsibilities:
- Accept image upload (multipart) or image URL.
- Validate request (size/type), auth, rate limiting.
- Store raw image in object storage.
- Enqueue an async job (default) and return `job_id`.
- Provide job polling endpoint for status + results.

Key endpoints:
- `POST /v1/books/identify`
- `GET /v1/jobs/{job_id}`
- `GET /v1/health`

### 2) Object Store (Images + Crops)
Responsibilities:
- Store raw image and derived artifacts:
  - normalized image
  - per-cover crops
  - (optional) debug overlays for internal review

Notes:
- Use short retention for raw images by default (privacy).
- Store only hashes/derived metadata when possible.

### 3) Queue + Worker Pool
Responsibilities:
- Async processing with retries/backoff.
- Timeouts and circuit breaking for external APIs (metadata + libraries).
- Concurrency control (prevent burst overload when a photo contains 20–50 books).

Why async matters for the attached image:
- Many covers in one frame can trigger dozens of downstream calls (resolver + library checks).

### 4) Preprocessing Service
Responsibilities:
- Normalize and improve readability:
  - resize to max edge
  - contrast normalization / glare reduction (best-effort)
  - mild deblur/denoise
  - orientation hints for detection models

Output:
- a normalized image that downstream detectors can reliably handle.

### 5) Book/Cover Detection
Responsibilities:
- Detect **each visible book cover region** in the photo.
- Output bounding boxes (or polygons) and detection confidence.

Why we need this for the attached image:
- Covers are at different angles; some are stacked; some partially occluded.
- OCR on the full image will mix text across multiple covers and degrade matching.

### 6) Rectification & Cropping
Responsibilities:
- Perspective-correct each detected cover (“flatten” it).
- Produce tight crops for OCR and embedding.

Output per cover:
- `crop_image`
- `crop_transform` (for debug overlays)
- `cover_id` (stable within a job)

### 7) OCR + Text Parsing
Responsibilities:
- Run OCR on each crop.
- Extract structured fields:
  - title candidates
  - author candidates
  - series candidates (helpful but optional)
  - ISBN candidates (fast path)

Implementation details:
- Aggressive ISBN extraction/validation (ISBN-10/13 checksums).
- Token cleanup for common OCR errors (e.g., I/1, O/0).

### 8) Cover Embeddings (Optional, Recommended After MVP)
Responsibilities:
- Compute an embedding vector per crop using a vision model.
- Use embeddings as a fallback when OCR is weak (glare, stylized fonts).

Two practical modes:
- Online lookup: compare against embeddings of known covers fetched from a metadata provider.
- Curated index: maintain an internal vector index for frequent titles or a specific collection.

### 9) Metadata Resolver
Responsibilities:
- Convert OCR/embedding signals into a canonical book record.

Resolution strategy:
1. If ISBN found: resolve directly by ISBN.
2. Else: query metadata sources with title/author candidates.
3. Re-rank candidates using:
   - text similarity (title/author)
   - OCR confidence
   - embedding similarity (if enabled)
4. Emit a canonical record:
   - `isbn13` when known
   - title, author(s)
   - edition hints (publisher/year) when available

Output:
- candidate list + chosen winner + confidence + match reasons (explainability).

### 10) Candidate Merge & Dedup
Responsibilities:
- Merge duplicates within the same image (e.g., repeated copies in stacks).
- Provide a stable `book_key`:
  - prefer `isbn13`
  - else `normalized(title) + normalized(author)`

Output:
- unique book list with aggregated evidence and a final confidence score.

### 11) Library Availability Service
Responsibilities:
- Query library availability for each canonical book.
- Prefer ISBN query; fall back to title/author.
- Normalize results to a common schema:
  - system, branch, availability status, call number, due date (if any)

Caching:
- Cache by `(library_system, isbn13)` for hours (tunable).
- Cache negative results briefly (minutes) to reduce repeated misses.

### 12) Library Connectors (Adapters)
Responsibilities:
- Provide per-library integration modules with consistent interface:
  - `search(isbn|title_author) -> bib_id(s)`
  - `availability(bib_id) -> holdings`

Why adapters:
- Library vendors differ in query syntax, auth, response shapes, and rate limits.

## Data Model (Conceptual)
- `Job`
  - id, status, timestamps, input metadata (library_system/location)
- `DetectedCover`
  - job_id, cover_id, bbox/polygon, crop_uri, detection_confidence
- `ResolvedBookCandidate`
  - cover_id, candidate metadata, score, reasons
- `BookResult`
  - job_id, book_key, canonical metadata, confidence, availability[]

## Operational Concerns
- Privacy: short TTL for images; redact logs; opt-in debug artifact storage.
- Rate limiting: per API key; per-job cap on detected covers.
- Timeouts: metadata lookups and library calls must be bounded.
- Observability: per-stage latency + counts (covers detected, books resolved, library calls made).

## Suggested V1 Tech Choices (Pragmatic)
- API: FastAPI (Python) or Express (Node), whichever matches the team.
- Queue: Redis + worker library (RQ/Celery/BullMQ).
- Storage: S3-compatible object store.
- DB: Postgres.
- Cache: Redis.
- OCR: start with a commodity OCR engine; swap behind an interface.
- Detection/rectification: start with a pre-trained detector; keep a seam for future training.

