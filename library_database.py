"""Database setup for the Library API.

main.py imports two things from here:
- DB_PATH:  where the SQLite file lives
- init_db(): creates the tables (and seed data) if they do not exist

There is no module-level connection any more. Every request opens its own
connection (see get_db in main.py).
"""
import os
import sqlite3

# Absolute path next to this file, so the same library.db is used no matter
# which folder uvicorn is started from. LIBRARY_DB lets tests use another file.
DB_PATH = os.getenv(
    "LIBRARY_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "library.db"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS Books (
    isbn             TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    author           TEXT NOT NULL,
    book_type        TEXT NOT NULL CHECK (book_type IN ('physical', 'digital')),
    available_copies INTEGER NOT NULL CHECK (available_copies >= 0),
    total_copies     INTEGER NOT NULL CHECK (total_copies >= 0)
);

CREATE TABLE IF NOT EXISTS Members (
    member_id   INTEGER PRIMARY KEY,
    member_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS BorrowedBooks (
    borrow_id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL,
    isbn      TEXT NOT NULL,
    status    TEXT NOT NULL CHECK (status IN ('borrowed', 'returned')),
    FOREIGN KEY (member_id) REFERENCES Members(member_id),
    FOREIGN KEY (isbn) REFERENCES Books(isbn)
);
"""

# (isbn, title, author, book_type, available_copies, total_copies)
# Digital books do not track copies, so they are stored as 0 / 0.
SEED_BOOKS = [
    ("101", "python book", "kaasim", "physical", 10, 10),
    ("102", "java book", "bala", "digital", 0, 0),
    ("103", "c++ book", "tamil", "physical", 5, 5),
    ("104", "story book", "kumar", "physical", 3, 3),
    ("105", "novel book", "raja", "digital", 0, 0),
    ("106", "history book", "siva", "physical", 2, 2),
]

# (member_id, member_name)
SEED_MEMBERS = [
    (1, "John"),
    (2, "Alice"),
    (3, "Bob"),
]


def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        # INSERT OR IGNORE: safe to run on every startup, never duplicates rows
        conn.executemany("INSERT OR IGNORE INTO Books VALUES (?, ?, ?, ?, ?, ?)", SEED_BOOKS)
        conn.executemany("INSERT OR IGNORE INTO Members VALUES (?, ?)", SEED_MEMBERS)
        conn.commit()
    finally:
        conn.close()