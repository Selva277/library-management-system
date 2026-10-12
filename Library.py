"""Library Management System: domain classes and database logic.

Design notes
- Every API request gets its own Library(connection), so no connection or
  cursor is shared between threads (see get_db in main.py).
- Expected business-rule failures raise NotFoundError / ConflictError.
  main.py converts them to HTTP 404 / 409 in one place.
- Physical vs digital is a `book_type` column (single-table design), not a
  subclass. Digital books do not track copies (stored as 0 / 0).
- Writes use `with self.connection:`, which commits on success and rolls
  back automatically if anything inside raises.
"""
import sqlite3

PHYSICAL = "physical"
DIGITAL = "digital"
BORROWED = "borrowed"
RETURNED = "returned"


class LibraryError(Exception):
    """Base class for expected business-rule failures."""


class NotFoundError(LibraryError):
    """A book or member does not exist (HTTP 404)."""


class ConflictError(LibraryError):
    """The request conflicts with the current state (HTTP 409)."""


class Book:
    def __init__(self, isbn, title, author, book_type, available_copies, total_copies):
        self.isbn = isbn
        self.title = title
        self.author = author
        self.book_type = book_type
        self.available_copies = available_copies
        self.total_copies = total_copies

    def __repr__(self):
        return (
            f"Book(ISBN={self.isbn}, Title='{self.title}', "
            f"Author='{self.author}', Available={self.available_copies})"
        )


class Member:
    def __init__(self, member_id, name):
        self.member_id = member_id
        self.name = name


class Library:
    def __init__(self, connection):
        self.connection = connection
        # Rows behave like dicts: row["title"], dict(row)
        self.connection.row_factory = sqlite3.Row

    # ---------------- helpers ----------------

    def _get_book(self, isbn):
        row = self.connection.execute(
            "SELECT * FROM Books WHERE isbn = ?", (isbn,)
        ).fetchone()
        if row is None:
            raise NotFoundError("Book not found")
        return row

    def _get_member(self, member_id):
        row = self.connection.execute(
            "SELECT member_id, member_name FROM Members WHERE member_id = ?",
            (member_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError("Member not found")
        return row

    def _active_borrow(self, member_id, isbn):
        return self.connection.execute(
            """
            SELECT borrow_id FROM BorrowedBooks
            WHERE member_id = ? AND isbn = ? AND status = ?
            """,
            (member_id, isbn, BORROWED),
        ).fetchone()

    def _active_borrow_count(self, isbn):
        return self.connection.execute(
            "SELECT COUNT(*) FROM BorrowedBooks WHERE isbn = ? AND status = ?",
            (isbn, BORROWED),
        ).fetchone()[0]

    def _borrowed_titles(self, member_id):
        rows = self.connection.execute(
            """
            SELECT b.title
            FROM BorrowedBooks br
            JOIN Books b ON br.isbn = b.isbn
            WHERE br.member_id = ? AND br.status = ?
            ORDER BY br.borrow_id
            """,
            (member_id, BORROWED),
        ).fetchall()
        return [row["title"] for row in rows]

    # ---------------- books ----------------

    def add_book(self, book):
        if book.book_type == DIGITAL:
            total = available = 0
        else:
            total, available = book.total_copies, book.available_copies

        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO Books
                    (isbn, title, author, book_type, available_copies, total_copies)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (book.isbn, book.title, book.author, book.book_type, available, total),
                )
        except sqlite3.IntegrityError:
            raise ConflictError("A book with this ISBN already exists")

        return self.book_info(book.isbn)

    def book_info(self, isbn):
        return dict(self._get_book(isbn))

    def show_all_books(self):
        rows = self.connection.execute("SELECT * FROM Books ORDER BY isbn").fetchall()
        return [dict(row) for row in rows]

    def search_book(self, title=None, author=None):
        """Exact-match search. With no filters it returns every book."""
        query = "SELECT * FROM Books WHERE 1=1"
        params = []

        if title is not None:
            query += " AND title = ?"
            params.append(title)

        if author is not None:
            query += " AND author = ?"
            params.append(author)

        query += " ORDER BY isbn"
        rows = self.connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def update_book(self, isbn, title, author, book_type, total_copies):
        """Full replace (PUT semantics). Keeps available_copies consistent."""
        self._get_book(isbn)

        if book_type == DIGITAL:
            total = available = 0
        else:
            borrowed = self._active_borrow_count(isbn)
            if total_copies < borrowed:
                raise ConflictError(
                    f"Cannot set total copies below the {borrowed} currently borrowed"
                )
            total, available = total_copies, total_copies - borrowed

        with self.connection:
            self.connection.execute(
                """
                UPDATE Books
                SET title = ?, author = ?, book_type = ?,
                    total_copies = ?, available_copies = ?
                WHERE isbn = ?
                """,
                (title, author, book_type, total, available, isbn),
            )

        return self.book_info(isbn)

    def remove_book(self, isbn):
        self._get_book(isbn)

        # Check real borrow records, not copy counts: this also protects
        # digital books, which are always stored as 0 / 0.
        if self._active_borrow_count(isbn) > 0:
            raise ConflictError("Cannot remove - book currently borrowed")

        with self.connection:
            self.connection.execute("DELETE FROM BorrowedBooks WHERE isbn = ?", (isbn,))
            self.connection.execute("DELETE FROM Books WHERE isbn = ?", (isbn,))

    # ---------------- members ----------------

    def register_member(self, member):
        try:
            with self.connection:
                self.connection.execute(
                    "INSERT INTO Members (member_id, member_name) VALUES (?, ?)",
                    (member.member_id, member.name),
                )
        except sqlite3.IntegrityError:
            raise ConflictError("Member ID already exists")

        return self.member_info(member.member_id)

    def member_info(self, member_id):
        member = self._get_member(member_id)
        return {
            "member_id": member["member_id"],
            "member_name": member["member_name"],
            "borrowed_books": self._borrowed_titles(member_id),
        }

    def show_all_members(self):
        # One query with LEFT JOINs instead of one query per member (N+1).
        rows = self.connection.execute(
            """
            SELECT m.member_id, m.member_name, b.title
            FROM Members m
            LEFT JOIN BorrowedBooks br
                   ON br.member_id = m.member_id AND br.status = ?
            LEFT JOIN Books b ON b.isbn = br.isbn
            ORDER BY m.member_id, br.borrow_id
            """,
            (BORROWED,),
        ).fetchall()

        members = {}
        for row in rows:
            entry = members.setdefault(
                row["member_id"],
                {
                    "member_id": row["member_id"],
                    "member_name": row["member_name"],
                    "borrowed_books": [],
                },
            )
            if row["title"] is not None:
                entry["borrowed_books"].append(row["title"])

        return list(members.values())

    def delete_member(self, member_id):
        self._get_member(member_id)

        active = self.connection.execute(
            "SELECT 1 FROM BorrowedBooks WHERE member_id = ? AND status = ? LIMIT 1",
            (member_id, BORROWED),
        ).fetchone()
        if active is not None:
            raise ConflictError("Return all borrowed books before deleting this member")

        with self.connection:
            self.connection.execute(
                "DELETE FROM BorrowedBooks WHERE member_id = ?", (member_id,)
            )
            self.connection.execute(
                "DELETE FROM Members WHERE member_id = ?", (member_id,)
            )

    # ---------------- borrow / return ----------------

    def borrow_book(self, member_id, isbn):
        self._get_member(member_id)
        book = self._get_book(isbn)

        if self._active_borrow(member_id, isbn) is not None:
            raise ConflictError("Book already borrowed by this member")

        with self.connection:
            if book["book_type"] == PHYSICAL:
                # Check-and-decrement in ONE statement. A separate SELECT
                # then UPDATE would let two requests take the last copy.
                cursor = self.connection.execute(
                    """
                    UPDATE Books
                    SET available_copies = available_copies - 1
                    WHERE isbn = ? AND available_copies > 0
                    """,
                    (isbn,),
                )
                if cursor.rowcount == 0:
                    raise ConflictError("No copies available")

            self.connection.execute(
                "INSERT INTO BorrowedBooks (member_id, isbn, status) VALUES (?, ?, ?)",
                (member_id, isbn, BORROWED),
            )

    def return_book(self, member_id, isbn):
        self._get_member(member_id)
        book = self._get_book(isbn)

        borrow = self._active_borrow(member_id, isbn)
        if borrow is None:
            raise ConflictError("This member has not borrowed this book")

        with self.connection:
            self.connection.execute(
                "UPDATE BorrowedBooks SET status = ? WHERE borrow_id = ?",
                (RETURNED, borrow["borrow_id"]),
            )

            if book["book_type"] == PHYSICAL:
                self.connection.execute(
                    """
                    UPDATE Books
                    SET available_copies = available_copies + 1
                    WHERE isbn = ?
                    """,
                    (isbn,),
                )

    def show_borrowed_books(self, status=None):
        query = """
            SELECT br.borrow_id, br.member_id, m.member_name,
                   br.isbn, b.title, br.status
            FROM BorrowedBooks br
            JOIN Books b ON br.isbn = b.isbn
            JOIN Members m ON br.member_id = m.member_id
        """
        params = []

        if status is not None:
            query += " WHERE br.status = ?"
            params.append(status)

        query += " ORDER BY br.borrow_id"
        rows = self.connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]