from flask import Flask, render_template, request, redirect, session
import requests
import os
import mysql.connector

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

# SECRET KEY (CORRECT PLACE)
app.secret_key = os.environ.get("SECRET_KEY", "default_secret")

MEALDB_BASE_URL = "https://www.themealdb.com/api/json/v1/1"

def get_db_connection():
    return mysql.connector.connect(
        host=os.environ["MYSQLHOST"],
        user=os.environ["MYSQLUSER"],
        password=os.environ["MYSQLPASSWORD"],
        database=os.environ["MYSQLDATABASE"],
        port=int(os.environ["MYSQLPORT"])
    )

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session["user_id"] = user[0]
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        return "POST reached successfully"
    return "REGISTER PAGE LOADED"


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ===============================
# DASHBOARD
# ===============================
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")
    return render_template("dashboard.html")

# ===============================
# MEAL SEARCH
# ===============================
@app.route("/search")
def search():
    query = request.args.get("q", "").strip().lower()
    meals = []

    if query:
        if len(query) == 1 and query.isalpha():
            data = requests.get(f"{MEALDB_BASE_URL}/search.php?f={query}").json()
            meals = data.get("meals") or []
        else:
            data = requests.get(f"{MEALDB_BASE_URL}/search.php?s={query}").json()
            meals = data.get("meals") or []

            if not meals:
                data = requests.get(f"{MEALDB_BASE_URL}/filter.php?c={query}").json()
                basic = data.get("meals") or []
                for m in basic:
                    lookup = requests.get(
                        f"{MEALDB_BASE_URL}/lookup.php?i={m['idMeal']}"
                    ).json()
                    if lookup.get("meals"):
                        meals.append(lookup["meals"][0])

    return render_template("meals.html", meals=meals)

# ===============================
# RECIPE DETAILS + NUTRITION
# ===============================
@app.route("/recipe/<meal_id>")
def recipe_details(meal_id):
    meal = requests.get(
        f"{MEALDB_BASE_URL}/lookup.php?i={meal_id}"
    ).json()["meals"][0]

    nutrition = calculate_nutrition(meal)
    return render_template("recipe_details.html", meal=meal, nutrition=nutrition)

def calculate_nutrition(meal):
    meal_id = meal["idMeal"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT calories, protein, fat FROM recipe_nutrition WHERE meal_id=%s",
        (meal_id,)
    )
    cached = cur.fetchone()

    if cached:
        cur.close()
        conn.close()
        return {"calories": cached[0], "protein": cached[1], "fat": cached[2]}

    total_cal = total_protein = total_fat = 0

    for i in range(1, 21):
        ingredient = meal.get(f"strIngredient{i}")
        if ingredient:
            r = requests.get(
                os.environ["USDA_BASE_URL"],
                params={
                    "query": ingredient,
                    "api_key": os.environ["USDA_API_KEY"],
                    "pageSize": 1
                }
            ).json()

            if r.get("foods"):
                for n in r["foods"][0].get("foodNutrients", []):
                    if n["nutrientName"] == "Energy":
                        total_cal += n.get("value", 0)
                    elif n["nutrientName"] == "Protein":
                        total_protein += n.get("value", 0)
                    elif n["nutrientName"] == "Total lipid (fat)":
                        total_fat += n.get("value", 0)

    cur.execute("""
        INSERT INTO recipe_nutrition (meal_id, calories, protein, fat)
        VALUES (%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
        calories=VALUES(calories),
        protein=VALUES(protein),
        fat=VALUES(fat)
    """, (meal_id, round(total_cal), round(total_protein, 1), round(total_fat, 1)))

    conn.commit()
    cur.close()
    conn.close()

    return {
        "calories": round(total_cal),
        "protein": round(total_protein, 1),
        "fat": round(total_fat, 1)
    }

# ===============================
# REQUIRED FOR VERCEL
# ===============================
app = app





