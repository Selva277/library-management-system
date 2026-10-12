from typing import Literal

from pydantic import BaseModel, Field

BookType = Literal["physical", "digital"]


# ---------------- books ----------------

class BookCreate(BaseModel):
    """Body of POST /books."""
    isbn: int
    title: str
    author: str
    book_type: BookType
    total_copies: int = Field(ge=0)  # rejects negative numbers with 422


class BookUpdate(BaseModel):
    """Body of PUT /books/{isbn}. The isbn comes from the URL, not the body."""
    title: str
    author: str
    book_type: BookType
    total_copies: int = Field(ge=0)


class BookResponse(BaseModel):
    isbn: int
    title: str
    author: str
    book_type: str
    available_copies: int
    total_copies: int


# ---------------- borrow / return ----------------

class BorrowRequest(BaseModel):
    """Body of POST /borrow and POST /return."""
    member_id: int
    isbn: str


class BorrowRecordResponse(BaseModel):
    borrow_id: int
    member_id: int
    member_name: str
    isbn: int
    title: str
    status: str


# ---------------- members ----------------

class MemberCreate(BaseModel):
    member_id: int
    member_name: str


class MemberInfoResponse(BaseModel):
    member_id: int
    member_name: str
    borrowed_books: list[str]