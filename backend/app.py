"""
MealMaker Backend - Flask Application
Handles fridge inventory management and recipe recommendations.
"""


from pathlib import Path
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os, json
from fridge_logic import get_possible_recipes

# Initialize Flask app
app = Flask(__name__)
# Enable CORS for cross-origin requests
CORS(app)

# === CONFIG ===
# Define directory paths for the application
BASE_DIR = Path(__file__).resolve().parent            # .../MealMaker/backend
ROOT_DIR = BASE_DIR.parent                            # .../MealMaker

# (AI scanning removed - model code deleted)
model = None

# === ROUTES: Page Rendering ===

@app.route("/")
def home():
    """Render the home/index page with fridge slots."""
    return render_template("index.html")


@app.route("/index")
def index():
    """Redirect to home page."""
    return render_template("index.html")

@app.route("/edit")
def edit_fridge():
    """Render the fridge editor page for manual inventory management."""
    return render_template("edit_fridge.html")

@app.route("/recipes")
def recipes_page():
    """Render the recipes page to display matching recipes."""
    return render_template("recipes.html")

# === ROUTE: Recipe Finder ===

@app.route("/get_recipes", methods=["POST"])
def get_recipes():
    """
    Fetch and filter recipes based on available fridge items and user preferences.

    Request body:
        - fridge: dict of {ingredient: quantity}
        - preferences: dict with calorieMin, calorieMax, protein (min)

    Returns: JSON list of recipes with name, URL, calories, and protein content
    """
    try:
        data = request.get_json(silent=True) or {}
        fridge = data.get("fridge", {})
        preferences = data.get("preferences", {})

        # ensure correct types
        if not isinstance(fridge, dict):
            fridge = {}
        if not isinstance(preferences, dict):
            preferences = {}

        # Get recipes that can be made
        recipes = get_possible_recipes(fridge)

        # Extract user preference filters
        calorie_min = preferences.get("calorieMin", 0)
        calorie_max = preferences.get("calorieMax", 9999)
        protein_min = preferences.get("protein", 0)

        # Filter recipes by nutritional preferences
        filtered = [
            r for r in recipes
            if calorie_min <= r[2] <= calorie_max and r[3] >= protein_min
        ]

        # Format recipes for JSON response
        result = [
            {
                "name": r[0],
                "source_url": r[1],
                "calories": r[2],
                "protein_g": r[3]
            } for r in filtered
        ]

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400






# === ERROR HANDLING ===

@app.errorhandler(404)
def not_found(e):
    # return a simple JSON or HTML depending on request
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Not found"}), 404
    return "<h1>404 - Page not found</h1>", 404


# === MAIN ===

if __name__ == "__main__":
    # Start Flask development server with debug mode enabled
    app.run(debug=True)
