from flask import Flask, render_template, request
import requests

app = Flask(__name__)

MEALDB_BASE_URL = "https://www.themealdb.com/api/json/v1/1"

@app.route("/")
def home():
    return render_template("search.html")

@app.route("/search")
def search():
    q = request.args.get("q", "")
    meals = []

    if q:
        data = requests.get(f"{MEALDB_BASE_URL}/search.php?s={q}").json()
        meals = data.get("meals") or []

    return render_template("meals.html", meals=meals)

app = app
