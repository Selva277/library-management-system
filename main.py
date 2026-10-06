from library_database import connection
from Library import Library,Book, Member

L1=Library(connection)

B1=Book(301,'python DSA','karthi','physical',10,10)
B2=Book(302,'java DSA','bala sir','digital',0,0)

M1=Member(4,'ram')
M2=Member(5,'sanjay')

#L1.add_book(B1)
#L1.add_book(B2) 

# L1.register_member(M1)
# L1.register_member(M2)

# L1.Borrow_book(4,301)
# L1.Borrow_book(5,302)
L1.borrow_book(5,101)
L1.show_all_books()
L1.show_borrowed_books()
