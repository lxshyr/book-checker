"""Manual test script for the Vega library API client.

Usage:
    python -m scripts.test_library
    # or from repo root:
    python scripts/test_library.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from book_checker.library_client import VegaLibraryClient, parse_search_results


async def test_search(client: VegaLibraryClient, label: str, raw: dict) -> None:
    """Print parsed results for a search."""
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    print(f"Total results: {raw.get('totalResults', 0)}")

    results = parse_search_results(raw)
    for i, result in enumerate(results, 1):
        print(f"\n--- Result {i} ---")
        print(f"  Title:  {result.title}")
        print(f"  Author: {result.author}")
        print(f"  ISBN:   {result.isbn}")
        print(f"  Found:  {result.found}")
        for avail in result.availabilities:
            print(f"    [{avail.status}] {avail.location}", end="")
            if avail.call_number:
                print(f" -- {avail.call_number}", end="")
            print()

    if not results:
        print("  (no results)")


async def main() -> None:
    async with VegaLibraryClient() as client:
        # Title search: Wild Robot
        raw = await client.search_by_title("Wild Robot", page_size=3)
        await test_search(client, 'Title search: "Wild Robot"', raw)

        # Title search: Wings of Fire
        raw = await client.search_by_title("Wings of Fire", page_size=3)
        await test_search(client, 'Title search: "Wings of Fire"', raw)

        # ISBN search
        isbn = "9780316382007"
        raw = await client.search_by_isbn(isbn, page_size=3)
        await test_search(client, f"ISBN search: {isbn}", raw)


if __name__ == "__main__":
    asyncio.run(main())
