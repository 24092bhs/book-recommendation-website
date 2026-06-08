from flask import Flask, render_template, request


app = Flask(__name__)


# home page
@app.route('/')
def home():
    # 1. look through SQL and grab books
    # 2. send those books to the HTML file
    return render_template('index.html')


# debug section thing
if __name__ == '__main__':
    app.run(debug=True)