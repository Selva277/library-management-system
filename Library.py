#Library Management System classes with methods
class Book:

    def __init__(
        self,
        isbn,
        title,
        author,
        book_type,
        available_copys,
        total_copies
    ):
        self.isbn = isbn
        self.title = title
        self.author = author
        self.book_type = book_type
        self.available_copys = available_copys
        self.total_copies = total_copies

    def __repr__(self):
        return (
            f"Book(ISBN={self.isbn}, Title='{self.title}', "
            f"Author='{self.author}', Available={self.available_copys})"
        )


class DigitalBook(Book):

    def __init__(self, isbn, title, author, file_size):

        super().__init__(
            isbn,
            title,
            author,
            "digital",
            0,
            0
        )

        self.file_size = file_size

class Member:

    def __init__(self, member_id, name):

        self.member_id = member_id
        self.name = name
        
        
class Library:

    def __init__(self, connection):

        self.connection = connection
        self.cursor = self.connection.cursor()

    # ---------------- ADD BOOK ----------------

    def add_book(self, book):

        self.cursor.execute(
            """
            INSERT INTO Books
            (isbn, title, author, book_type, available_copys, total_copies)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                book.isbn,
                book.title,
                book.author,
                book.book_type,
                book.available_copys,
                book.total_copies
            )
        )

        self.connection.commit()

        print("Book added successfully.")

    # ---------------- REMOVE BOOK ----------------

    def remove_book(self, isbn):

        self.cursor.execute(
            """
            SELECT available_copys, total_copies
            FROM Books
            WHERE isbn = ?
            """,
            (isbn,)
        )

        book = self.cursor.fetchone()

        if book is None:
            print("Book not found.")
            return

        available_copys = book[0]
        total_copies = book[1]

        if available_copys < total_copies:
            print("Cannot remove - book currently borrowed.")
            return

        self.cursor.execute(
            """
            DELETE FROM Books
            WHERE isbn = ?
            """,
            (isbn,)
        )

        self.connection.commit()

        print("Book removed successfully.")

    # ---------------- SEARCH BOOK ----------------

    def search_book(self, title=None, author=None):

        if title is not None and author is not None:

            self.cursor.execute(
                """
                SELECT *
                FROM Books
                WHERE title = ? AND author = ?
                """,
                (title, author)
            )

        elif title is not None:

            self.cursor.execute(
                """
                SELECT *
                FROM Books
                WHERE title = ?
                """,
                (title,)
            )

        elif author is not None:

            self.cursor.execute(
                """
                SELECT *
                FROM Books
                WHERE author = ?
                """,
                (author,)
            )

        else:
            print("Please provide title or author.")
            return

        results = self.cursor.fetchall()

        if results:

            for book in results:
                print(book)

        else:
            print("No books found matching the criteria.")

    # ---------------- REGISTER MEMBER ----------------

    def register_member(self, member):

        self.cursor.execute(
            """
            INSERT INTO Members
            (member_id, member_name)
            VALUES (?, ?)
            """,
            (
                member.member_id,
                member.name
            )
        )

        self.connection.commit()

        print("Member registered successfully.")

    # ---------------- MEMBER INFO ----------------

    def member_info(self, member_id):

        self.cursor.execute(
            """
            SELECT member_id, member_name
            FROM Members
            WHERE member_id = ?
            """,
            (member_id,)
        )

        member = self.cursor.fetchone()

        if member is None:
            print("Member not found.")
            return

        print(f"Member ID: {member[0]}")
        print(f"Name: {member[1]}")

        self.cursor.execute(
            """
            SELECT b.title
            FROM BorrowedBooks br
            JOIN Books b
            ON br.isbn = b.isbn
            WHERE br.member_id = ?
            AND br.status = ?
            """,
            (member_id, "borrowed")
        )

        borrowed_books = self.cursor.fetchall()

        if borrowed_books:

            print("Borrowed Books:")

            for book in borrowed_books:
                print(book[0])

        else:
            print("No borrowed books.")

    # ---------------- BORROW BOOK ----------------

    def borrow_book(self, member_id, isbn):

        try:

            # 1. Check member

            self.cursor.execute(
                """
                SELECT *
                FROM Members
                WHERE member_id = ?
                """,
                (member_id,)
            )

            member = self.cursor.fetchone()

            if member is None:
                print("Member not found.")
                return

            # 2. Check book

            self.cursor.execute(
                """
                SELECT *
                FROM Books
                WHERE isbn = ?
                """,
                (isbn,)
            )

            book = self.cursor.fetchone()

            if book is None:
                print("Book not found.")
                return

            # Books columns:
            # 0 -> isbn
            # 1 -> title
            # 2 -> author
            # 3 -> book_type
            # 4 -> available_copys
            # 5 -> total_copies

            book_type = book[3]
            available_copys = book[4]

            # 3. Check whether member already borrowed this book

            self.cursor.execute(
                """
                SELECT *
                FROM BorrowedBooks
                WHERE member_id = ?
                AND isbn = ?
                AND status = ?
                """,
                (
                    member_id,
                    isbn,
                    "borrowed"
                )
            )

            existing_borrow = self.cursor.fetchone()

            if existing_borrow is not None:

                print("Member has already borrowed this book.")

                return

            # 4. Check physical book availability

            if book_type == "physical" and available_copys <= 0:

                print("Book is not available.")

                return

            # 5. Create borrowing record

            self.cursor.execute(
                """
                INSERT INTO BorrowedBooks
                (member_id, isbn, status)
                VALUES (?, ?, ?)
                """,
                (
                    member_id,
                    isbn,
                    "borrowed"
                )
            )

            # 6. Decrease physical book availability

            if book_type == "physical":

                self.cursor.execute(
                    """
                    UPDATE Books
                    SET available_copys = available_copys - 1
                    WHERE isbn = ?
                    """,
                    (isbn,)
                )

            # 7. Save transaction

            self.connection.commit()

            print("Book borrowed successfully.")

        except Exception as e:

            # Undo all changes if something goes wrong

            self.connection.rollback()

            print(f"Error while borrowing book: {e}")

    # ---------------- RETURN BOOK ----------------

    def return_book(self, member_id, isbn):

        try:

            # 1. Check borrowing record

            self.cursor.execute(
                """
                SELECT *
                FROM BorrowedBooks
                WHERE member_id = ?
                AND isbn = ?
                AND status = ?
                """,
                (
                    member_id,
                    isbn,
                    "borrowed"
                )
            )

            borrowing = self.cursor.fetchone()

            if borrowing is None:

                print(
                    "This book is not borrowed by this member."
                )

                return

            # 2. Get book type

            self.cursor.execute(
                """
                SELECT book_type
                FROM Books
                WHERE isbn = ?
                """,
                (isbn,)
            )

            book = self.cursor.fetchone()

            if book is None:

                print("Book not found.")

                return

            # 3. Update borrowing status

            self.cursor.execute(
                """
                UPDATE BorrowedBooks
                SET status = ?
                WHERE member_id = ?
                AND isbn = ?
                AND status = ?
                """,
                (
                    "returned",
                    member_id,
                    isbn,
                    "borrowed"
                )
            )

            # 4. Increase physical book availability

            if book[0] == "physical":

                self.cursor.execute(
                    """
                    UPDATE Books
                    SET available_copys = available_copys + 1
                    WHERE isbn = ?
                    """,
                    (isbn,)
                )

            # 5. Save transaction

            self.connection.commit()

            print("Book returned successfully.")

        except Exception as e:

            # Undo all changes if something goes wrong

            self.connection.rollback()

            print(f"Error while returning book: {e}")

    # ---------------- SHOW BORROWED BOOKS ----------------

    def show_borrowed_books(self):

        self.cursor.execute(
            """
            SELECT b.title, m.member_name, br.status
            FROM BorrowedBooks br
            JOIN Books b
            ON br.isbn = b.isbn
            JOIN Members m
            ON br.member_id = m.member_id
            """
        )

        borrowed_books = self.cursor.fetchall()

        if not borrowed_books:

            print("No borrowed books found.")

            return

        for title, member_name, status in borrowed_books:

            print(
                f"Title: {title}, "
                f"Borrowed by: {member_name}, "
                f"Status: {status}"
            )

    # ---------------- SHOW ALL BOOKS ----------------

    def show_all_books(self):

        self.cursor.execute(
            """
            SELECT *
            FROM Books
            """
        )

        books = self.cursor.fetchall()

        if not books:

            print("No books found.")

            return

        for book in books:

            print(
                f"ISBN: {book[0]}, "
                f"Title: {book[1]}, "
                f"Author: {book[2]}, "
                f"Type: {book[3]}, "
                f"Available Copies: {book[4]}, "
                f"Total Copies: {book[5]}"
            )