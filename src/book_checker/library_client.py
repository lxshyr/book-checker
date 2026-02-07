import logging
from typing import Any

import httpx

from book_checker.models import LibraryAvailability, LibraryResult

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


def _parse_material_tab(tab: dict[str, Any]) -> LibraryAvailability:
    """Parse a single materialTab entry into a LibraryAvailability."""
    availability = tab.get("availability", {})
    status_obj = availability.get("status", {})
    general_status = status_obj.get("general", "Unknown")

    location = tab.get("itemLibrary") or tab.get("name", "Unknown")
    call_number = tab.get("callNumber")

    return LibraryAvailability(
        location=location,
        call_number=call_number,
        status=general_status,
    )


def parse_search_results(response: dict[str, Any]) -> list[LibraryResult]:
    """Parse a Vega API response into a list of LibraryResult objects.

    Extracts availability data from materialTabs for each format group.
    ``found`` is True when the item exists in the catalogue (any
    materialTab present).  Physical availability details are recorded in
    ``availabilities``.
    """
    results: list[LibraryResult] = []
    for item in response.get("data", []):
        title = item.get("title")
        agent = item.get("primaryAgent", {})
        author = agent.get("label") if agent else None

        isbn: str | None = None
        availabilities: list[LibraryAvailability] = []
        tabs = item.get("materialTabs", [])

        for tab in tabs:
            # Grab the first ISBN from any tab
            if isbn is None:
                identified = tab.get("identifiedBy", {})
                isbn_list = identified.get("isbn", [])
                if isbn_list:
                    isbn = isbn_list[0]

            if tab.get("type") != "physical":
                continue

            availabilities.append(_parse_material_tab(tab))

        results.append(
            LibraryResult(
                found=bool(tabs),
                title=title,
                author=author,
                isbn=isbn,
                availabilities=availabilities,
            )
        )

    return results
