"""Manual test script for the VLM book identification module.

Requires the package to be installed (``pip install -e .``) and a valid
``OPENAI_API_KEY`` in your ``.env`` file.

Usage (from repo root):
    python scripts/test_vision.py [IMAGE_PATH]

If no image path is provided, defaults to data/PXL_20260117_190210631.jpg.
"""

import asyncio
import sys
from pathlib import Path

from book_checker.models import IdentifiedBook
from book_checker.vision import identify_books

DEFAULT_IMAGE = Path("data/PXL_20260117_190210631.jpg")


def print_books(books: list[IdentifiedBook]) -> None:
    """Pretty-print identified books."""
    print(f"\n{'=' * 60}")
    print(f"  Identified {len(books)} book(s)")
    print(f"{'=' * 60}")

    for i, book in enumerate(books, 1):
        print(f"\n--- Book {i} ---")
        print(f"  Title:      {book.title}")
        print(f"  Author:     {book.author or '(unknown)'}")
        print(f"  Series:     {book.series or '(none)'}")
        print(f"  Confidence: {book.confidence:.0%}")
        if book.notes:
            print(f"  Notes:      {book.notes}")


async def main() -> None:
    image_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_IMAGE

    if not image_path.exists():
        print(f"Error: image not found: {image_path}")
        sys.exit(1)

    print(f"Identifying books in: {image_path}")
    books = await identify_books(image_path)
    print_books(books)


if __name__ == "__main__":
    asyncio.run(main())
