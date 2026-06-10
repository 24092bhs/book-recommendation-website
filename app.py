import sqlite3
from flask import Flask, redirect, render_template, request
from google import genai  # <-- 1. NEW IMPORT

app = Flask(__name__)


def get_db_connection():
    conn = sqlite3.connect("books.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            notes TEXT NOT NULL
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
    input_title = request.form["title"]
    input_author = request.form["author"]
    input_notes = request.form["notes"]

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO books (title, author, notes) VALUES (?, ?, ?)",
        (input_title, input_author, input_notes),
    )
    conn.commit()
    conn.close()
    return redirect("/")


# 2. NEW ROUTE: Constructing the Prompt & contacting Gemini
@app.route("/recommend")
def recommend_books():
    conn = get_db_connection()
    all_books = conn.execute("SELECT * FROM books").fetchall()
    conn.close()

    # If the user hasn't added any books yet, don't waste an API call
    if not all_books:
        return render_template(
            "index.html",
            books=[],
            recommendations="<p>Please add a few books to your history first so I can analyze your taste!</p>",
        )

    # 3. Constructing the dynamic Master Prompt
    master_prompt = (
        "You are an elite literary critic. Based on my reading history and why I liked each book, "
        "recommend 3 distinct books I should read next. "
        "Format your output using clean HTML elements like <p>, <strong>, <ul>, and <li> so it integrates seamlessly into a webpage. "
        "Do NOT wrap your response in markdown code blocks (like ```html), just output the raw HTML markup text.\n\n"
        "Here is my reading history:\n"
    )

    for book in all_books:
        master_prompt += f"- '{book['title']}' by {book['author']}. Why I liked it: {book['notes']}\n"

    # 4. Attempting to call the Gemini API
    try:
        # By default, genai.Client() automatically looks for an environment variable named GEMINI_API_KEY
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

    # Render the home page, but this time pass the AI suggestions along
    return render_template(
        "index.html", books=all_books, recommendations=ai_analysis
    )


if __name__ == "__main__":
    app.run(debug=True)