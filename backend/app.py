from pathlib import Path
from flask import Flask, request, jsonify, render_template, url_for  # consolidate imports
from flask_cors import CORS
from ultralytics import YOLO
import os, json, base64, uuid
from datetime import datetime
from fridge_logic import get_possible_recipes

# Initialize app
app = Flask(__name__)
CORS(app)

# === CONFIG ===
BASE_DIR = Path(__file__).resolve().parent            # .../MealMaker/backend
ROOT_DIR = BASE_DIR.parent                            # .../MealMaker

FRIDGE_PATH = ROOT_DIR / "data" / "fridges.json"      # .../MealMaker/data/fridges.json
IMAGE_FOLDER = BASE_DIR / "images"                    # .../MealMaker/backend/images  (non-web)
WEIGHTS_PATH = ROOT_DIR / "yolov8n.pt"                # .../MealMaker/yolov8n.pt

os.makedirs(IMAGE_FOLDER, exist_ok=True)

# Load YOLOv8 model once
model = YOLO(str(WEIGHTS_PATH))  #Trained to detect multiple items
@app.route("/")
def home():
    return render_template("index.html")
@app.route("/ai")
def ai_page():
    return render_template("ai_fridge.html")
@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/edit")
def edit_fridge():
    return render_template("edit_fridge.html")

@app.route("/recipes")
def recipes_page():
    return render_template("recipes.html")

# === ROUTE: Recipe Finder ===
@app.route("/get_recipes", methods=["POST"])
def get_recipes():
    data = request.json
    fridge = data.get("fridge", {})
    preferences = data.get("preferences", {})

    print("=== DEBUG: Incoming Data ===")
    print("Fridge:", fridge)
    print("Preferences:", preferences)

    recipes = get_possible_recipes(fridge)

    print("=== DEBUG: Recipes BEFORE filtering ===")
    print(recipes)

    calorie_min = preferences.get("calorieMin", 0)
    calorie_max = preferences.get("calorieMax", 9999)
    protein_min = preferences.get("protein", 0)

    filtered = [
        r for r in recipes
        if calorie_min <= r[2] <= calorie_max and r[3] >= protein_min
    ]

    print("=== DEBUG: Recipes AFTER filtering ===")
    print(filtered)

    result = [
        {
            "name": r[0],
            "source_url": r[1],
            "calories": r[2],
            "protein_g": r[3]
        } for r in filtered
    ]

    return jsonify(result)

# === ROUTE: Scan Image and Detect Ingredients ===
@app.route("/scan_image", methods=["POST"])
def scan_image():
    try:
        image = request.files.get("photo")
        fridge_id = request.form.get("fridge_id", "default")
        print("✅ Received photo:", image.filename)
        print("✅ Fridge ID:", fridge_id)

        if not image:
            print("x No image received")
            return jsonify({"status": "error", "message": "No image received"})

        # Save uploaded image with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{fridge_id}_{timestamp}.jpg"
        image_path = os.path.join(IMAGE_FOLDER, filename)

        print("📸 Saving image to:", image_path)
        image.save(image_path)
        print("✅ Image saved")

        # Run detection
        results = model(image_path)
        detected_items = set()

        for r in results:
            for c in r.boxes.cls:
                label = model.names[int(c)]
                detected_items.add(label.lower())

        print("🧠 Detected:", detected_items)

        # Load/update fridge
        if os.path.exists(FRIDGE_PATH):
            with open(FRIDGE_PATH, "r") as f:
                fridges = json.load(f)
        else:
            fridges = {}

        if fridge_id not in fridges:
            fridges[fridge_id] = {}

        for item in detected_items:
            fridges[fridge_id][item] = 1

        with open(FRIDGE_PATH, "w") as f:
            json.dump(fridges, f, indent=2)

        return jsonify({
            "status": "success",
            "fridge": fridge_id,
            "items": list(detected_items),
            "image_path": image_path
        })

    except Exception as e:
        print("X Exception occurred:", str(e))
        return jsonify({"status": "error", "message": str(e)})
    
@app.route("/save_frame", methods=["POST"])
def save_frame():
    data = request.get_json(silent=True) or {}
    img_b64 = data.get("imageData", "")
    header, b64data = img_b64.split(",", 1) if "," in img_b64 else ("", img_b64)

    img_bytes = base64.b64decode(b64data)
    save_dir = os.path.join(app.static_folder, "images")
    os.makedirs(save_dir, exist_ok=True)

    fname = f"{uuid.uuid4().hex}.png"
    fpath = os.path.join(save_dir, fname)
    with open(fpath, "wb") as f:
        f.write(img_bytes)

    return jsonify({"ok": True, "url": url_for('static', filename=f'images/{fname}')})


# === MAIN ===
if __name__ == "__main__":
    app.run(debug=True)
