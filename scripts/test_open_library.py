"""Manual test script for the Open Library API client.

Requires the package to be installed (``pip install -e .``).

Usage (from repo root):
    python scripts/test_open_library.py
"""

import asyncio

from book_checker.open_library import OpenLibraryClient


async def main() -> None:
    async with OpenLibraryClient() as client:
        print("\n" + "=" * 60)
        print("  Testing Open Library ISBN Enrichment")
        print("=" * 60)

        # Test 1: Title only
        print("\n--- Test 1: Title only ---")
        title = "The Wild Robot"
        isbn = await client.search_isbn(title)
        print(f"Title: {title!r}")
        print(f"ISBN:  {isbn or '(not found)'}")

        # Test 2: Title + Author
        print("\n--- Test 2: Title + Author ---")
        title = "Wings of Fire"
        author = "Tui T. Sutherland"
        isbn = await client.search_isbn(title, author)
        print(f"Title:  {title!r}")
        print(f"Author: {author!r}")
        print(f"ISBN:   {isbn or '(not found)'}")

        # Test 3: Obscure title (should return None gracefully)
        print("\n--- Test 3: Nonexistent book ---")
        title = "This Book Definitely Does Not Exist 12345"
        isbn = await client.search_isbn(title)
        print(f"Title: {title!r}")
        print(f"ISBN:  {isbn or '(not found)'}")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
