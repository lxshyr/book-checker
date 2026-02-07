import logging

import httpx

logger = logging.getLogger(__name__)

VEGA_API_URL = "https://na5.iiivega.com/api/search-result/search/format-groups"

VEGA_HEADERS = {
    "Content-Type": "application/json",
    "iii-customer-domain": "mvpl.na5.iiivega.com",
    "iii-host-domain": "librarycatalog.mountainview.gov",
    "api-version": "2",
}


class VegaLibraryClient:
    """Client for the Mountain View Public Library Vega API."""

    def __init__(self, timeout: float = 10.0) -> None:
        self._client = httpx.AsyncClient(
            headers=VEGA_HEADERS,
            timeout=timeout,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "VegaLibraryClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def _search(
        self, query: str, *, page: int = 0, page_size: int = 5
    ) -> dict:
        """Execute a raw search and return the JSON response."""
        payload = {
            "searchText": query,
            "pageNum": page,
            "pageSize": page_size,
        }
        resp = await self._client.post(VEGA_API_URL, json=payload)
        resp.raise_for_status()
        return resp.json()

    async def search_by_title(
        self, title: str, *, page_size: int = 5
    ) -> dict:
        """Search by title using Vega search syntax t:(title)."""
        return await self._search(f"t:({title})", page_size=page_size)

    async def search_by_isbn(self, isbn: str, *, page_size: int = 5) -> dict:
        """Search by ISBN (plain string)."""
        return await self._search(isbn, page_size=page_size)

    async def search_by_keyword(
        self, keyword: str, *, page_size: int = 5
    ) -> dict:
        """Search by keyword (general search text)."""
        return await self._search(keyword, page_size=page_size)
