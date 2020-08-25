import os, csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

os.environ["DATABASE_URL"] = "postgres://nwonjhmbpslrvx:d9bd4272d60aed0b26af4f671a3119ef4188cb3a223a950daab6262aab0361dd@ec2-34-202-88-122.compute-1.amazonaws.com:5432/d2j46inls63bnh"
# database engine object from SQLAlchemy that manages connections to the database
engine = create_engine(os.getenv("DATABASE_URL"))

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# create a 'scoped session' that ensures different users' interactions with the
# database are kept separate
db = scoped_session(sessionmaker(bind=engine))

file = open("books.csv")

reader = csv.reader(file)

for isbn, title, author, year in reader:

    db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                {"isbn": isbn, 
                 "title": title,
                 "author": author,
                 "year": year})

    print(f"Added book {title} to database.")

    db.commit()