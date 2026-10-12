import sqlite3
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from Library import Book, ConflictError, Library, Member, NotFoundError
from library_database import DB_PATH, init_db
from schemas import (
    BookCreate,
    BookResponse,
    BookUpdate,
    BorrowRecordResponse,
    BorrowRequest,
    MemberCreate,
    MemberInfoResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create tables once, when the server starts
    yield


app = FastAPI(title="Library API", lifespan=lifespan)


# ---------------- dependencies ----------------

def get_db():
    """One SQLite connection per request, always closed afterwards.

    check_same_thread=False is safe here: the connection belongs to a single
    request and is never used by two threads at once. (FastAPI may run the
    dependency and the endpoint in different worker threads.)
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def get_library(conn: sqlite3.Connection = Depends(get_db)) -> Library:
    return Library(conn)


# ---------------- error handling ----------------

@app.exception_handler(NotFoundError)
def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
def conflict_handler(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


# ---------------- root ----------------

@app.get("/")
def root():
    return {"message": "Library API is running"}


# ---------------- books ----------------

@app.post("/books", response_model=BookResponse, status_code=201)
def create_book(book: BookCreate, library: Library = Depends(get_library)):
    new_book = Book(
        isbn=book.isbn,
        title=book.title,
        author=book.author,
        book_type=book.book_type,
        available_copies=book.total_copies,
        total_copies=book.total_copies,
    )
    return library.add_book(new_book)


# Must be declared BEFORE /books/{isbn}, otherwise "search" is read as an isbn.
@app.get("/books/search", response_model=list[BookResponse])
def search_books(
    title: str | None = None,
    author: str | None = None,
    library: Library = Depends(get_library),
):
    if title is None and author is None:
        raise HTTPException(status_code=400, detail="Please provide title or author")
    return library.search_book(title, author)


@app.get("/books/{isbn}", response_model=BookResponse)
def get_book(isbn: str, library: Library = Depends(get_library)):
    return library.book_info(isbn)


@app.get("/books", response_model=list[BookResponse])
def get_books(library: Library = Depends(get_library)):
    return library.show_all_books()  # empty list is a valid 200 response


@app.put("/books/{isbn}", response_model=BookResponse)
def update_book(
    isbn: str, book: BookUpdate, library: Library = Depends(get_library)
):
    return library.update_book(
        isbn, book.title, book.author, book.book_type, book.total_copies
    )


@app.delete("/books/{isbn}")
def delete_book(isbn: str, library: Library = Depends(get_library)):
    library.remove_book(isbn)
    return {"message": "Book removed successfully"}


# ---------------- borrow / return ----------------

@app.post("/borrow")
def borrow_book(request: BorrowRequest, library: Library = Depends(get_library)):
    library.borrow_book(request.member_id, request.isbn)
    return {"message": "Book borrowed successfully"}


@app.post("/return")
def return_book(request: BorrowRequest, library: Library = Depends(get_library)):
    library.return_book(request.member_id, request.isbn)
    return {"message": "Book returned successfully"}


@app.get("/borrowed", response_model=list[BorrowRecordResponse])
def get_borrowed(
    status: Literal["borrowed", "returned"] | None = None,
    library: Library = Depends(get_library),
):
    return library.show_borrowed_books(status)


# ---------------- members ----------------

@app.post("/members", response_model=MemberInfoResponse, status_code=201)
def register_member(member: MemberCreate, library: Library = Depends(get_library)):
    return library.register_member(Member(member.member_id, member.member_name))


@app.get("/members/{member_id}/info", response_model=MemberInfoResponse)
def get_member_info(member_id: int, library: Library = Depends(get_library)):
    return library.member_info(member_id)


@app.get("/members", response_model=list[MemberInfoResponse])
def get_all_members(library: Library = Depends(get_library)):
    return library.show_all_members()


@app.delete("/members/{member_id}")
def delete_member(member_id: int, library: Library = Depends(get_library)):
    library.delete_member(member_id)
    return {"message": "Member deleted successfully"}