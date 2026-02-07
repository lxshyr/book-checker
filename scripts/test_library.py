"""Manual test script for the Vega library API client.

Usage:
    python -m scripts.test_library
    # or from repo root:
    python scripts/test_library.py
"""

import asyncio

from book_checker.library_client import VegaLibraryClient
from book_checker.models import LibraryResult


def print_results(label: str, results: list[LibraryResult]) -> None:
    """Print parsed results for a search."""
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")

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
        results = await client.search_by_title("Wild Robot", page_size=3)
        print_results('Title search: "Wild Robot"', results)

        results = await client.search_by_title("Wings of Fire", page_size=3)
        print_results('Title search: "Wings of Fire"', results)

        isbn = "9780316382007"
        results = await client.search_by_isbn(isbn, page_size=3)
        print_results(f"ISBN search: {isbn}", results)


if __name__ == "__main__":
    asyncio.run(main())
