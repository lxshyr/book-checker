import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OpenLibraryClient:
    """Client for the Open Library API to enrich book data with ISBNs."""

    def __init__(self, timeout: float = 10.0) -> None:
        self._base_url = "https://openlibrary.org"
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "OpenLibraryClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def search_isbn(
        self, title: str, author: str | None = None
    ) -> str | None:
        """Search for a book by title and optional author, returning the first ISBN found.

        Returns None on any error (network, parsing, or no results).
        Failures are logged but do not raise exceptions to ensure
        pipeline continues with title/author fallback.
        """
        query = ""  # Initialize early to avoid UnboundLocalError in exception handlers
        try:
            query_parts = [title]
            if author:
                query_parts.append(author)
            query = " ".join(query_parts)

            params = {"q": query, "limit": 1, "fields": "isbn,title,author_name"}

            logger.info("Searching Open Library for: %r", query)
            resp = await self._client.get(
                f"{self._base_url}/search.json", params=params
            )
            resp.raise_for_status()
            data = resp.json()

            docs = data.get("docs", [])
            if not docs:
                logger.debug("No Open Library results for %r", query)
                return None

            first_doc = docs[0]
            isbn_list = first_doc.get("isbn", [])

            if not isbn_list:
                logger.debug(
                    "Open Library result for %r has no ISBN: %s",
                    query,
                    first_doc.get("title"),
                )
                return None

            isbn = isbn_list[0]
            logger.info(
                "Found ISBN %s for %r (from %s by %s)",
                isbn,
                query,
                first_doc.get("title"),
                first_doc.get("author_name", ["Unknown"])[0],
            )
            return isbn

        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Open Library API returned %s for query %r",
                exc.response.status_code,
                query,
            )
            return None
        except httpx.RequestError as exc:
            logger.warning("Open Library API request failed for query %r: %s", query, exc)
            return None
        except (ValueError, KeyError) as exc:
            logger.warning("Failed to parse Open Library response for query %r: %s", query, exc)
            return None


async def enrich_with_isbn(
    title: str, author: str | None = None, existing_isbn: str | None = None
) -> str | None:
    """Enrich a book with an ISBN from Open Library.

    Returns the existing ISBN if already present, otherwise searches
    Open Library. Returns None if enrichment fails or no ISBN found.

    This function never raises exceptions - all errors are logged and
    None is returned to ensure the pipeline can continue with title/author fallback.
    """
    if existing_isbn:
        logger.debug("ISBN already present for %r, skipping enrichment", title)
        return existing_isbn

    try:
        async with OpenLibraryClient() as client:
            return await client.search_isbn(title, author)
    except Exception as exc:
        # Catch-all for any unexpected errors to ensure pipeline continues
        logger.warning("Unexpected error during ISBN enrichment for %r: %s", title, exc)
        return None


