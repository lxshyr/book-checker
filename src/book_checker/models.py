from pydantic import BaseModel


class IdentifiedBook(BaseModel):
    title: str
    author: str | None = None
    series: str | None = None
    isbn: str | None = None
    confidence: float
    notes: str | None = None


class LibraryAvailability(BaseModel):
    location: str
    call_number: str | None = None
    status: str
    due_date: str | None = None


class LibraryResult(BaseModel):
    found: bool
    title: str | None = None
    author: str | None = None
    isbn: str | None = None
    availabilities: list[LibraryAvailability] = []


class BookResult(BaseModel):
    identified: IdentifiedBook
    library: LibraryResult


class CheckBooksResponse(BaseModel):
    books: list[BookResult]
    image_description: str | None = None
