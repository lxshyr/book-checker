# Book-Checker API: Milestones & Phases

Dates are relative; if we start the week of **February 3, 2026**, this plan targets a usable MVP in **6–8 weeks** with 1–3 engineers.

## Phase 0: Clarify Requirements (2–3 days)
Deliverables:
- Confirm target environments (mobile client? web upload?).
- Confirm library scope:
  - single library system first (recommended)
  - multi-branch vs multi-consortium
- Define constraints:
  - max image size
  - max books per image (soft cap, e.g., 30)
  - latency targets (async SLA)
- Define success metrics:
  - Top-1 identification accuracy per visible cover
  - “useful result rate” (at least 1 correct book found)

Decisions to lock:
- Async-first (job API) vs sync-first
- Which metadata source(s) to use in V1
- Which library system API to integrate first

## Phase 1: Skeleton Service + Job Flow (Week 1)
Deliverables:
- API skeleton:
  - `POST /v1/books/identify` returns `job_id`
  - `GET /v1/jobs/{job_id}` returns status/result
- Persistent storage:
  - object store for images
  - DB tables for jobs and results
- Queue + worker runner (single worker process is fine)
- Observability basics:
  - structured logs with job_id
  - per-stage timing fields

Exit criteria:
- You can submit an image and see a completed job (even if results are stubbed).

## Phase 2: OCR-First Identification (Weeks 2–3)
Why this phase:
- It gives an end-to-end book identification path quickly, even before cover detection is perfect.

Deliverables:
- Preprocessing step (resize/normalize).
- OCR on the full image OR naive cropping (temporary).
- Text parsing:
  - extract ISBN candidates
  - extract title/author candidates
- Metadata resolver integration:
  - ISBN lookup path
  - title/author lookup path
- Confidence scoring + match reasons returned in API response.

Exit criteria:
- For “easy” photos (few books, clear titles), the system returns correct canonical metadata.

## Phase 3: Library Availability V1 (Week 3–4)
Deliverables:
- Library adapter interface.
- Implement first connector (one real target).
- Availability normalization:
  - per-branch status
  - call number if available
- Caching:
  - cache by ISBN
  - cache negative results briefly
- Failure modes:
  - timeouts
  - partial availability results per book

Exit criteria:
- For a known ISBN, the system reliably returns normalized availability.

## Phase 4: Multi-Book Detection + Rectification (Weeks 4–6)
Why this phase matters (based on the attached image):
- Photos can contain many books; OCR across the whole image blends multiple covers.
- Covers can be rotated, skewed, partially hidden, and reflective.

Deliverables:
- Cover detection:
  - bounding boxes/polygons per cover
  - confidence thresholding
- Perspective rectification per cover.
- Per-cover OCR instead of full-image OCR.
- Candidate merge + dedup:
  - avoid reporting duplicates when there are multiple copies
  - choose best crop evidence for the same book
- Introduce a per-job cap and/or prioritization:
  - process highest-confidence covers first to stay within resource budgets

Exit criteria:
- For a “pile of books” photo, the system returns a list of distinct books with stable confidence ordering.

## Phase 5: Quality, Eval Harness, and Hardening (Weeks 6–7)
Deliverables:
- A small evaluation set (20–50 images):
  - varied lighting, angles, partial occlusion, stacks
- Eval tooling:
  - compute precision/recall at Top-1 and Top-3
  - track latency per pipeline stage
- Safety + reliability:
  - rate limiting + quotas
  - robust retries/backoff for external services
  - privacy defaults (image retention TTL)
- Regression tests on parsing and resolver ranking.

Exit criteria:
- Measured improvements over baseline and no major regressions across the eval set.

## Phase 6: “Hard Cases” Upgrades (Week 8+)
Pick based on observed failures.

Option A: Cover Embeddings
- Add embedding computation per crop.
- Use embeddings for candidate reranking, especially when OCR is low confidence.

Option B: Better Cover Detection
- Fine-tune detector on your own photos.
- Add segmentation for tighter crops.

Option C: Multi-Library Expansion
- Add 2–3 more connectors behind the adapter interface.
- Add library selection logic by user location / configured systems.

Exit criteria:
- Higher “useful result rate” on messy photos; broader library coverage.

## Recommended Execution Order (If Team Size Is 1)
1. Phase 1 (job plumbing) — prevents rewrites later.
2. Phase 2 (OCR-first) — fastest path to “it works”.
3. Phase 3 (library integration) — makes output valuable.
4. Phase 4 (cover detection/rectification) — unlocks multi-book photos like the attached example.
5. Phase 5 (eval + hardening) — makes it shippable.

