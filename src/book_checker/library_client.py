from typing import Any

import httpx

from book_checker.models import LibraryAvailability, LibraryResult

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
    ) -> list[LibraryResult]:
        """Search by title using Vega search syntax t:(title)."""
        raw = await self._search(f"t:({title})", page_size=page_size)
        return parse_search_results(raw)

    async def search_by_author(
        self, author: str, *, page_size: int = 5
    ) -> list[LibraryResult]:
        """Search by author using Vega search syntax a:(author)."""
        raw = await self._search(f"a:({author})", page_size=page_size)
        return parse_search_results(raw)

    async def search_by_isbn(
        self, isbn: str, *, page_size: int = 5
    ) -> list[LibraryResult]:
        """Search by ISBN (plain string)."""
        raw = await self._search(isbn, page_size=page_size)
        return parse_search_results(raw)

    async def search_by_keyword(
        self, keyword: str, *, page_size: int = 5
    ) -> list[LibraryResult]:
        """Search by keyword (general search text)."""
        raw = await self._search(keyword, page_size=page_size)
        return parse_search_results(raw)


def _parse_material_tab(tab: dict[str, Any]) -> list[LibraryAvailability]:
    """Parse a physical materialTab into one LibraryAvailability per location."""
    call_number = tab.get("callNumber")
    locations = tab.get("locations", [])

    if locations:
        return [
            LibraryAvailability(
                location=loc.get("label", "Unknown"),
                call_number=call_number,
                status=loc.get("availabilityStatus", "Unknown"),
            )
            for loc in locations
        ]

    # Fallback when no locations array is present
    availability = tab.get("availability", {})
    status_obj = availability.get("status", {})
    general_status = status_obj.get("general", "Unknown")
    location = tab.get("itemLibrary") or tab.get("name", "Unknown")

    return [
        LibraryAvailability(
            location=location,
            call_number=call_number,
            status=general_status,
        )
    ]


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

            availabilities.extend(_parse_material_tab(tab))

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
