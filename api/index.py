from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "MealDB Flask is running on Vercel 🚀"

app = app
