import sqlite3
from flask import Flask, redirect, render_template, request
from dotenv import load_dotenv
from google import genai

app = Flask(__name__)

# upload key from .env file
load_dotenv()

def get_db_connection():
    conn = sqlite3.connect("books.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    # UPDATED: Added rating column to the table creation schema
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            notes TEXT NOT NULL,
            rating INTEGER NOT NULL DEFAULT 5
        )
    """
    )
    conn.commit()
    conn.close()


init_db()


@app.route("/")
def home():
    conn = get_db_connection()
    all_books = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    return render_template("index.html", books=all_books, recommendations=None)


@app.route("/add", methods=["POST"])
def add_book():
    input_title = request.form["title"].title()
    input_author = request.form["author"].title()
    input_notes = request.form["notes"]
    input_rating = int(request.form["rating"])  # <-- UPDATED: Catch the rating

    conn = get_db_connection()
    # UPDATED: Inserting the rating into the database query
    conn.execute(
        "INSERT INTO books (title, author, notes, rating) VALUES (?, ?, ?, ?)",
        (input_title, input_author, input_notes, input_rating),
    )
    conn.commit()
    conn.close()
    return redirect("/")

# deletes a book from the database
@app.route("/delete/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    return redirect("/")


@app.route("/clear", methods=["POST"])
def clear_history():
    conn = get_db_connection()
    conn.execute("DELETE FROM books")
    conn.commit()
    conn.close()
    return redirect("/")


@app.route("/recommend")
def recommend_books():
    conn = get_db_connection()
    all_books = conn.execute("SELECT * FROM books").fetchall()
    conn.close()

    if not all_books:
        return render_template(
            "index.html",
            books=[],
            recommendations="<p>Please add a few books to your history first so I can analyze your taste!</p>",
        )

    # UPDATED: Instruct the AI to care deeply about the numerical values
    master_prompt = (
        "You are a friendly, knowledgeable book assistant. Look at my reading history and ratings "
        "to recommend 5 niche/distinct books I should read next. Heavily prioritize elements from high-rated books.\n\n"
        
        "CRITICAL INSTRUCTIONS:\n"
        "1. Do NOT include any introductory titles, section headers, or concluding remarks. Do NOT use <h2> or any other main headings. Just jump straight into rendering the first book card.\n"
        "2. For each recommendation, identify its most popular, widely available classic edition ISBN-13 number to maximize the chance of finding its cover artwork.\n"
        "3. You MUST format each of the 5 book recommendations using this exact HTML structure:\n"
        "   <div class='rec-book-card'>\n"
        "       <img src='https://covers.openlibrary.org/b/isbn/[PUT_ISBN_HERE]-M.jpg' class='rec-cover' alt='Book Cover' onerror=\"this.onerror=null;this.src='https://placehold.co/100x150?text=No+Cover';\">\n"
        "       <div class='rec-details'>\n"
        "           <h3>[Book Title]</h3>\n"
        "           <p><strong>Author:</strong> [Author Name]</p>\n"
        "           <p><strong>Blurb:</strong> [A brief summary of what the book is about]</p>\n"
        "           <p><strong>Why you will like it:</strong> [A personalized sentence explaining why it fits their history/rating]</p>\n"
        "       </div>\n"
        "   </div>\n\n"
        
        "Do NOT wrap your response in markdown code blocks (like ```html), just output the raw HTML markup.\n\n"
        "Here is my reading history:\n"
    )

    for book in all_books:
        # UPDATED: Pushing ratings straight into the AI's training prompt context
        master_prompt += f"- '{book['title']}' by {book['author']}. My personal rating: {book['rating']}/5 stars. Why I liked it: {book['notes']}\n"

    try:
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=master_prompt
        )
        ai_analysis = response.text
    except Exception as e:
        ai_analysis = (
            f"<p style='color: #e74c3c;'><strong>API Connection Error:</strong> {e}<br>"
            "Make sure you have obtained a Gemini API Key and set it up in your system environment variables!</p>"
        )

    return render_template(
        "index.html", books=all_books, recommendations=ai_analysis
    )


if __name__ == "__main__":
    app.run(debug=True)