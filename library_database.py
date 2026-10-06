import sqlite3

connection=sqlite3.connect('library.db')

cursor=connection.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS Books(
    isbn integer PRIMARY KEY,
    title text NOT NULL,
    author text NOT NULL,
    book_type text NOT NULL,
    available_copys integer NOT NULL,
    total_copies integer NOT NULL
    )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS Members (
    member_id integer PRIMARY KEY,
    member_name text NOT NULL
    )''')

cursor.execute('''CREATE TABLE  IF NOT EXISTS BorrowedBooks (
    borrow_id integer PRIMARY KEY AUTOINCREMENT,
    member_id integer,
    isbn integer,
    status text NOT NULL,
    
    FOREIGN KEY (member_id) REFERENCES Members(member_id),
    FOREIGN KEY (isbn) REFERENCES Books(isbn)
    )''')

cursor.execute('''
                INSERT OR IGNORE INTO Books VALUES
               (101,'python book','kaasim','physical',10,10),
               (102,'java book','bala','digital',0,0),
               (103,'c++ book','tamil','physical',5,5),
               (104,'story book','kumar','physical',3,3),
               (105,'novel book','raja','digital',0,0),
               (106,'history book','siva','physical',2,2)''')

cursor.execute('''
                INSERT OR IGNORE INTO Members VALUES
               (1,'John'),
               (2,'Alice'),
               (3,'Bob')''')

# cursor.execute('''
#                INSERT INTO BorrowedBooks (member_id,isbn,status) values 
#                (1,101,'borrowed'),
#                (2,102,'returned'),
#                (3,103,'borrowed')''')

# cursor.execute('''SELECT * FROM Members WHERE member_id = 2''')

# rows=cursor.fetchone()

# print(rows)


connection.commit()