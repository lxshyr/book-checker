"""Manual test script for the Open Library API client.

Requires the package to be installed (``pip install -e .``).

Usage (from repo root):
    python scripts/test_open_library.py
"""

import asyncio

from book_checker.open_library import OpenLibraryClient, enrich_with_isbn


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

    # Test 4: Using the fallback-safe enrichment helper with existing ISBN
    print("\n--- Test 4: Enrichment with existing ISBN (fallback-safe) ---")
    existing = "9781234567890"
    result = await enrich_with_isbn("Some Title", existing_isbn=existing)
    print(f"Existing ISBN: {existing}")
    print(f"Result:        {result}")

    # Test 5: Using the enrichment helper without ISBN
    print("\n--- Test 5: Enrichment without existing ISBN (fallback-safe) ---")
    result = await enrich_with_isbn("The Wild Robot", "Peter Brown")
    print(f"Title:  'The Wild Robot'")
    print(f"Author: 'Peter Brown'")
    print(f"Result: {result or '(not found)'}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
