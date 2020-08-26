import os, json

from flask import Flask, session
from flask_session import Session

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import flash, redirect, render_template, request, abort, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import requests
from helpers import login_required

#os.environ["DATABASE_URL"] = "postgres://nwonjhmbpslrvx:d9bd4272d60aed0b26af4f671a3119ef4188cb3a223a950daab6262aab0361dd@ec2-34-202-88-122.compute-1.amazonaws.com:5432/d2j46inls63bnh"
# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

app = Flask(__name__)

 #Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"                                                                 
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
@login_required
def index():

    return render_template("index.html")


  #  if session.get("user_id") is None:
   #     return redirect("/login")
  #  else:
  #      return redirect("index.html")


    #if not session.get('logged in'):
     #   return render_template("/login")
    #else:
    #    return "hello Boss!"

@app.route("/login", methods = ["GET", "POST"])
def login():

    session.clear()


    username = request.form.get("username")

    if request.method == "POST":

        if not request.form.get("username"):
            return render_template("error.html", message = "must provide username")
        elif not request.form.get("password"):
            return render_template("error.html", message = "must provide password")              

        rows = db.execute("SELECT * from users WHERE username = :username",
                            {"username": username})

        result = rows.fetchone()

        if result == None or not check_password_hash(result[1], request.form.get("password")):
            return render_template("error.html", message = "Invalid username or password")

        session["user_name"] = result[0]
        session["user_id"] = result[2]
        

        return redirect("/")
    
    else:
        return render_template("login.html")

#def validate_login():

#    if request.form['password'] == 'password' and request.form['username']  == 'admin':
#        session['logged_in'] = True
#    else:
#        flash('wrong password!')
#        return home()

@app.route("/logout")

def logout():

    session.clear()

    return redirect("/")

@app.route("/register", methods = ["GET", "POST"])

def register():

    session.clear()

    if request.method == "POST":

        if not request.form.get("username"):
            return render_template("error.html", message = "must provide username")

        checkUser = db.execute("SELECT * from users where username = :username",
                                {"username":request.form.get("username")}).fetchone()
        if checkUser:
            return render_template("error.html", message = "username already exist")

        elif not request.form.get("password"):
            return render_template("error.html", message = "must provide password")

        elif not request.form.get("confirmation"):
            return render_template("error.html", message = "must confirm password")

        elif not request.form.get("password") == request.form.get("confirmation"):
            return render_template("error.html", message = "password didn't match")

        hashPassword = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)

        db.execute("INSERT into users (username, password) VALUES (:username, :password)",
                    {"username" :request.form.get("username"),"password" :hashPassword})

        db.commit()

        flash('Account created', 'info')

        return redirect("/login")

    else:
        return render_template("registration.html")

@app.route("/search", methods=["GET"])
@login_required
def search():
    if not request.args.get("book"):
        return render_template("error.html", message = "must provide book name or isbn")
    
    query = "%" + request.args.get("book") + "%"

    rows = db.execute("Select isbn, title, author, year from books WHERE \
                        isbn LIKE :query OR \
                        title LIKE :query OR\
                        author LIKE :query LIMIT 15",
                        {"query": query})

    if rows.rowcount == 0:
        return render_template("error.html", message = "There is no book with similar description")

    books = rows.fetchall()

    return render_template("results.html", books=books)

@app.route("/book/<isbn>", methods = ['GET' ,'POST'])
@login_required
def book(isbn):

    if request.method == "POST":

        currentUser = session["user_id"]

        rating = request.form.get("rating")
        comment = request.form.get("comment")

        row = db.execute("SELECT id from books WHERE isbn = :isbn", 
                            {"isbn" :isbn})

        bookId = row.fetchone()
        bookId = bookId[0]

        row2 = db.execute("SELECT * from reviews WHERE user_id = :user_id AND book_id = :book_id",
                            {"user_id": currentUser,
                             "book_id": bookId})

        if row2.rowcount == 1:

            return render_template("error.html", message = "already submitted review")
            return redirect("/book/" + isbn)

        rating = int(rating)

        db.execute("INSERT into reviews (user_id, book_id, comment, rating) VALUES (:user_id, :book_id, :comment, :rating)",
                    {"user_id" :currentUser,
                     "book_id" :bookId,
                     "comment" :comment,
                     "rating" :rating})

        db.commit()

        flash("Review submiited", 'info')

        return redirect("/book/" + isbn)

    else:

        row = db.execute("SELECT isbn, author, title from books WHERE isbn = :isbn",
                            {"isbn": isbn})

        bookInfo = row.fetchall()

        key = os.getenv("GOODREADS_KEY")

        query = requests.get("https://www.goodreads.com/book/review_counts.json",
                params={"key": key, "isbns": isbn})

        response = query.json()

        response = response['books'][0]

        bookInfo.append(response)

        row = db.execute("SELECT id from books where isbn = :isbn",
                            {"isbn":isbn})

        book = row.fetchone() # id
        book = book[0]

        results = db.execute("SELECT users.username, comment, rating, \
                                to_char(time, 'DD MON YY - HH24:MI:SS') as time \
                                FROM users \
                                INNER JOIN reviews \
                                ON users.id = reviews.user_id \
                                WHERE book_id = :book \
                                ORDER BY time",
                                {"book": book})

        reviews = results.fetchall()

        return render_template("book.html", bookInfo=bookInfo, reviews=reviews)

@app.route("/api/<isbn>", methods = ["GET"])
@login_required

def api_call(isbn):

    row = db.execute("SELECT title, author, year, isbn, \
                        COUNT(reviews.id) as review_count, \
                        AVG(reviews.rating) as average_score, \
                        FROM books \
                        INNER JOIN reviews \
                        ON books.id = reviews.book_Id \
                        Where isbn = :isbn \
                        GROUP BY title, author, year, isbn",
                        {"isbn": isbn})

    if row.rowcount != 1:
        return jsonify({"Error": "Invalid book isbn"}), 422

    temp = row.fetchone()

    result = dict(temp.items())

    result['average_score'] = float('.%2f'%(result['average_score']))

    return jsonify(result)







if __name__ == '__main__':
    
   # app.register_blueprint(app, url_prefix = '/')
  #  app.secret_key = os.urandom(12)
    app.run(debug = True)