"""
MealMaker Backend - Flask Application
Handles fridge inventory management and recipe recommendations.
"""


from pathlib import Path
from flask import Flask, request, jsonify, render_template, g
from flask_cors import CORS
import os, json
from fridge_logic import get_possible_recipes
from functools import wraps
import jwt
from jwt import PyJWK
from dotenv import load_dotenv
import requests

# Load environment variables
# We'll explicitly load .env from the repository root and the backend folder
# so the server can read secrets when run from either location.

# Initialize Flask app
app = Flask(__name__)
# Enable CORS for cross-origin requests
CORS(app)

# === CONFIG ===
# Define directory paths for the application
BASE_DIR = Path(__file__).resolve().parent            # .../MealMaker/backend
ROOT_DIR = BASE_DIR.parent                            # .../MealMaker

# Load .env files: root first, then backend (backend can override root)
load_dotenv(str(ROOT_DIR / '.env'))
load_dotenv(str(BASE_DIR / '.env'))

# === JWT KEY CACHING (for Supabase ES256 verification) ===

_jwks_cache = {}  # Cache for JWKS public keys

def get_jwks_public_key(kid=None):
    """
    Fetch the public key from Supabase JWKS endpoint for verifying ES256 tokens.
    Caches the key to avoid repeated HTTP calls.
    
    @param kid: Key ID from the JWT header (optional; if not provided, uses the first available key)
    @return: PyJWK object or raises exception if not found
    """
    try:
        # Fetch JWKS from Supabase if not cached
        if not _jwks_cache:
            jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
            response = requests.get(jwks_url)
            response.raise_for_status()
            jwks_data = response.json()
            
            # Cache all keys by their kid
            for key_data in jwks_data.get("keys", []):
                key_id = key_data.get("kid")
                if key_id:
                    _jwks_cache[key_id] = PyJWK.from_dict(key_data)
        
        # Get the specific key or use the first one
        if kid and kid in _jwks_cache:
            return _jwks_cache[kid]
        elif _jwks_cache:
            # Return the first cached key if kid not found
            return next(iter(_jwks_cache.values()))
        else:
            raise Exception("No JWKS keys available")
    except Exception as e:
        app.logger.error(f"Error fetching JWKS public key: {e}")
        raise


# Supabase configuration from environment
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ttecrjtzqptstaqiztia.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "sb_publishable_cHHxBu6RwUCWJPQyWKqc7g_au4AtKsJ")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# === AUTH DECORATOR ===

def require_auth(f):
    """
    Decorator to require valid JWT authentication.
    Validates Bearer token from Authorization header using Supabase's public key (ES256).
    Sets g.user_id if token is valid.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        
        # Basic Authorization header checks
        if not auth_header.startswith("Bearer "):
            app.logger.debug("Missing or malformed Authorization header: %r", auth_header)
            return jsonify({"error": "Unauthorized"}), 401
        
        token = auth_header[7:]  # Remove "Bearer " prefix

        # Log a masked token for debugging (don't print full token in production logs)
        if token:
            app.logger.debug("Received token (masked): %s...", token[:20])
        else:
            app.logger.debug("Received empty token string")

        try:
            # Decode JWT header to get the kid (key ID)
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            app.logger.debug(f"Token kid: {kid}, algo: {unverified_header.get('alg')}")
            
            # Fetch the public key from Supabase JWKS
            public_key = get_jwks_public_key(kid)
            
            # Verify and decode the token using ES256 and the public key
            payload = jwt.decode(
                token,
                public_key.key,
                algorithms=["ES256"],
                audience="authenticated"
            )
            g.user_id = payload.get("sub")
            
            if not g.user_id:
                app.logger.debug("JWT decoded but missing sub claim: %r", payload)
                return jsonify({"error": "Invalid token"}), 401
            
            app.logger.debug(f"Auth success for user: {g.user_id}")
                
        except Exception as e:
            # Log the full exception for debugging (will show in server console)
            app.logger.error("JWT validation error: %s", repr(e))
            return jsonify({"error": "Invalid or expired token"}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

# === HELPER FUNCTIONS ===

def supabase_headers(token):
    """
    Return headers for Supabase REST API calls.
    Includes API key and user's authorization token.
    """
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def fuzzy_match(fridge_ingredient, recipe_ingredient):
    """
    Check if a fridge ingredient fuzzy matches a recipe ingredient.
    Handles plurals, substrings, and close typos using Levenshtein distance.
    """
    a = fridge_ingredient.lower().strip()
    b = recipe_ingredient.lower().strip()
    
    # Exact match
    if a == b:
        return True
    
    # One contains the other (e.g. "bread" matches "sourdough bread")
    if a in b or b in a:
        return True
    
    # Strip common plural suffixes (eggs -> egg, tomatoes -> tomato)
    def stem(word):
        for suffix in ["oes", "es", "s"]:
            if word.endswith(suffix):
                return word[:-len(suffix)]
        return word
    
    if stem(a) == stem(b):
        return True
    
    if stem(a) in b or stem(b) in a:
        return True
    
    # Levenshtein distance for typo tolerance
    def levenshtein(s1, s2):
        if len(s1) < len(s2):
            return levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)
        prev = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            curr = [i + 1]
            for j, c2 in enumerate(s2):
                curr.append(min(prev[j+1]+1, curr[j]+1, prev[j]+(c1!=c2)))
            prev = curr
        return prev[-1]
    
    # Allow 1 edit for short words, 2 edits for longer words
    max_dist = 1 if len(b) <= 5 else 2
    if levenshtein(a, b) <= max_dist:
        return True
    
    return False

# === ROUTES: Page Rendering ===

@app.route("/")
def home():
    """Render the home/index page with fridge slots."""
    return render_template("index.html")

@app.route("/login")
def login_page():
    """Render the login/signup page."""
    return render_template("login.html")

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

# === ROUTES: API (Fridge Management) ===

@app.route("/api/fridge", methods=["GET"])
@require_auth
def get_fridges():
    """
    Get all fridges for the authenticated user.
    Proxies to Supabase REST API filtering by user_id.
    """
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        url = f"{SUPABASE_URL}/rest/v1/fridges"
        params = {"user_id": f"eq.{g.user_id}", "select": "*"}
        
        response = requests.get(
            url,
            headers=supabase_headers(token),
            params=params
        )
        
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/fridge", methods=["POST"])
@require_auth
def create_fridge():
    """
    Create a new fridge for the authenticated user.
    Proxies to Supabase REST API with user_id set automatically.
    Expected request body: { "name": "Fridge Name", "slot_index": 1 }
    """
    try:
        data = request.get_json(silent=True) or {}
        
        # Extract fields matching the actual table schema
        fridge_data = {
            "name": data.get("name", "New Item"),
            "quantity": data.get("quantity", 0),
            "unit": data.get("unit", "pcs"),
            "fridge_name": data.get("fridge_name", "My Fridge"),
            "user_id": g.user_id
        }
        # Enforce user ownership
        fridge_data["user_id"] = g.user_id
        
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        url = f"{SUPABASE_URL}/rest/v1/fridges"
        
        response = requests.post(
            url,
            headers=supabase_headers(token),
            json=fridge_data
        )
        
        # log for debugging
        app.logger.debug("create_fridge payload=%s status=%s body=%s", fridge_data, response.status_code, response.text)
        
        # safely try to parse JSON in case body is empty or invalid
        try:
            resp_json = response.json()
        except ValueError:
            resp_json = {"raw_body": response.text}
        return jsonify(resp_json), response.status_code
    except Exception as e:
        app.logger.exception("Unhandled error in create_fridge")
        return jsonify({"error": str(e)}), 500

@app.route("/api/fridge/<item_id>", methods=["PUT"])
@require_auth
def update_fridge(item_id):
    """
    Update a fridge item (name, quantity, unit, etc) if owned by the user.
    Proxies to Supabase REST API with user_id filter.
    """
    try:
        data = request.get_json(silent=True) or {}
        
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        url = f"{SUPABASE_URL}/rest/v1/fridges"
        params = {
            "id": f"eq.{item_id}",
            "user_id": f"eq.{g.user_id}"
        }
        
        response = requests.patch(
            url,
            headers=supabase_headers(token),
            json=data,
            params=params
        )
        
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/fridge/<item_id>", methods=["DELETE"])
@require_auth
def delete_fridge_item(item_id):
    """
    Delete a single fridge item if owned by the user.
    Proxies to Supabase REST API with user_id filter.
    """
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        url = f"{SUPABASE_URL}/rest/v1/fridges"
        params = {
            "id": f"eq.{item_id}",
            "user_id": f"eq.{g.user_id}"
        }
        
        response = requests.delete(
            url,
            headers=supabase_headers(token),
            params=params
        )
        
        return jsonify(response.json()) if response.text else jsonify({}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/fridge", methods=["DELETE"])
@require_auth
def delete_all_fridges():
    """
    Delete all fridges for the authenticated user.
    Proxies to Supabase REST API filtering by user_id.
    """
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        url = f"{SUPABASE_URL}/rest/v1/fridges"
        params = {"user_id": f"eq.{g.user_id}"}
        
        response = requests.delete(
            url,
            headers=supabase_headers(token),
            params=params
        )
        
        return jsonify(response.json()) if response.text else jsonify({}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === ROUTE: Recipe Finder ===

@app.route("/get_recipes", methods=["POST"])
def get_recipes():
    try:
        data = request.get_json(silent=True) or {}
        fridge = data.get("fridge", {})
        preferences = data.get("preferences", {})

        calorie_min = preferences.get("calorieMin", 0)
        calorie_max = preferences.get("calorieMax", 9999)
        protein_min = preferences.get("protein", 0)

        # Fetch all recipes from Supabase
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/recipes",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                "Content-Type": "application/json"
            },
            params={"select": "id,name,calories,protein_g,source_url"}
        )
        all_recipes = response.json()
        # After fetching recipes
        print("recipes response status:", response.status_code)
        print("recipes data:", response.json())

        # Fetch all ingredients from Supabase
        ing_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/recipe_ingredients",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                "Content-Type": "application/json"
            },
            params={"select": "recipe_id,ingredient,quantity,unit"}
        )
        all_ingredients = ing_response.json()
        # After fetching ingredients  
        print("ingredients response status:", ing_response.status_code)
        print("ingredients data:", ing_response.json())

        # Normalize fridge keys to lowercase
        fridge_normalized = {k.lower(): float(v) for k, v in fridge.items() if v}

        # Group ingredients by recipe_id
        from collections import defaultdict
        recipe_ingredients = defaultdict(list)
        for ing in all_ingredients:
            recipe_ingredients[ing["recipe_id"]].append(ing)

        # Match recipes against fridge
        result = []
        for recipe in all_recipes:
            # Filter by preferences
            if not (calorie_min <= recipe["calories"] <= calorie_max):
                continue
            if recipe["protein_g"] < protein_min:
                continue

            # Check if user has all ingredients
            ingredients = recipe_ingredients[recipe["id"]]
            can_make = all(
                any(
                    fuzzy_match(fridge_key, ing["ingredient"]) and float(fridge_normalized[fridge_key]) >= ing["quantity"]
                    for fridge_key in fridge_normalized
                )
                for ing in ingredients
            )

            if can_make:
                result.append({
                    "name": recipe["name"],
                    "source_url": recipe["source_url"],
                    "calories": recipe["calories"],
                    "protein_g": recipe["protein_g"]
                })

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

if __name__ == "__main__":
    app.run(debug=True)