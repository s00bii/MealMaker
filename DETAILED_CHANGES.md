# Code Changes Reference

## Key Improvements Made

### Backend (app.py)

#### REMOVED Sections:
```python
# BEFORE:
try:
    from ultralytics import YOLO
except Exception:
    YOLO = None

if YOLO is None:
    print("⚠️ ultralytics package not installed...")
    model = None
else:
    if not os.path.exists(WEIGHTS_PATH):
        print(f"⚠️ WARNING: YOLO model not found...")
    else:
        try:
            model = YOLO(str(WEIGHTS_PATH))
        except Exception as e:
            print(f"⚠️ ERROR loading YOLO model: {e}")
            model = None

@app.route("/ai")
def ai_page():
    """Render the AI ingredient scanner page using camera."""
    response = render_template("ai_fridge.html")
    if isinstance(response, str):
        from flask import Response
        response = Response(response)
    response.headers["Content-Security-Policy"] = "script-src 'self' 'unsafe-eval'..."
    return response

@app.route("/scan_image", methods=["POST"])
def scan_image():
    """Process uploaded image with YOLOv8..."""
    # ~50 lines of code

@app.route("/save_frame", methods=["POST"])
def save_frame():
    """Save a base64-encoded image frame..."""
    # ~25 lines of code

@app.route("/add_items", methods=["POST"])
def add_items():
    """Add items to a fridge's inventory..."""
    # ~30 lines of code (now unused)

@app.route("/confirm_items", methods=["POST"])
def confirm_items():
    """Confirm and persist detected ingredients..."""
    # ~30 lines of code (now unused)

# AFTER:
# (AI scanning removed - model code deleted)
model = None

# All routes removed, no changes needed
```

#### ADDED Error Handling:
```python
# BEFORE:
@app.route("/get_recipes", methods=["POST"])
def get_recipes():
    data = request.json  # Could crash if malformed
    fridge = data.get("fridge", {})
    preferences = data.get("preferences", {})
    
    print("=== DEBUG: Incoming Data ===")
    print("Fridge:", fridge)
    print("Preferences:", preferences)
    # ... debug prints

# AFTER:
@app.route("/get_recipes", methods=["POST"])
def get_recipes():
    try:
        data = request.get_json(silent=True) or {}
        fridge = data.get("fridge", {})
        preferences = data.get("preferences", {})
        
        # Validate types
        if not isinstance(fridge, dict):
            fridge = {}
        if not isinstance(preferences, dict):
            preferences = {}
        
        # No debug prints
        recipes = get_possible_recipes(fridge)
        # ... rest of logic
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.errorhandler(404)
def not_found(e):
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Not found"}), 404
    return "<h1>404 - Page not found</h1>", 404
```

---

### Backend (fridge_logic.py)

#### ADDED Robustness:
```python
# BEFORE:
def get_possible_recipes(fridge):
    db_path = os.path.join(os.path.dirname(__file__), "db", "recipes.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ...
    
    for ing_name, qty_needed in ingredients:
        if qty_needed is None:
            continue
        
        try:
            fridge_qty = float(fridge.get(ing_name, 0))  # Case-sensitive lookup
        except ValueError:
            fridge_qty = 0
    
    # No input validation

# AFTER:
def get_possible_recipes(fridge):
    # Guard against bad input
    if not isinstance(fridge, dict):
        fridge = {}
    
    # Normalize keys to lowercase for case-insensitive matching
    fridge_normalized = {}
    for k, v in fridge.items():
        try:
            fridge_normalized[str(k).lower()] = v
        except Exception:
            pass
    
    db_path = os.path.join(os.path.dirname(__file__), "db", "recipes.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ...
    
    for ing_name, qty_needed in ingredients:
        if qty_needed is None:
            continue
        
        available_qty = 0
        try:
            available_qty = float(fridge_normalized.get(ing_name.lower(), 0))  # Case-insensitive
        except Exception:
            available_qty = 0
```

---

### Frontend (script.js)

#### FIXED Edit Page Item Bugs:
```javascript
// BEFORE: Could create duplicate "New Item" keys on multiple clicks
addItemBtn.addEventListener("click", () => {
    fridge.items["New Item"] = "0";
    saveFridges(fridges);
    renderItems();
});

// AFTER: Generates unique names
addItemBtn.addEventListener("click", () => {
    let base = "New Item";
    let idx = 1;
    let key = base;
    while (fridge.items.hasOwnProperty(key)) {
        idx += 1;
        key = `${base} ${idx}`;
    }
    fridge.items[key] = "0";
    saveFridges(fridges);
    renderItems();
});
```

#### FIXED Item Name Editing:
```javascript
// BEFORE: Closure staling - originalName could be incorrect
function attachItemHandlers(li, originalName) {
    function saveItem() {
        const newName = nameEl.textContent.trim();
        if (originalName !== newName) delete fridge.items[originalName];
        fridge.items[newName] = newQty;
        saveFridges(fridges);
        originalName = newName;  // Trying to update closure variable
    }
}

// AFTER: Using data attribute
li.dataset.origName = name;

function attachItemHandlers(li) {
    function saveItem() {
        const originalName = li.dataset.origName;
        const newName = nameEl.textContent.trim();
        if (originalName !== newName) {
            delete fridge.items[originalName];
            li.dataset.origName = newName;  // Update attribute
        }
        fridge.items[newName] = newQty;
        saveFridges(fridges);
    }
}
```

#### FIXED Event Listener Stacking:
```javascript
// BEFORE: Click listener added inside renderSlots() on every render
function renderSlots() {
    fridgeSlotsContainer.innerHTML = "";
    
    fridges.forEach((fridge, index) => {
        // ... create elements
    });
    
    // PROBLEM: This runs every time renderSlots() is called
    document.addEventListener("click", (e) => {
        if (!e.target.closest(".slot-wrapper")) {
            document.querySelectorAll(".slot-context-menu").forEach(menu => {
                menu.classList.remove("active");
            });
        }
    });
}

// AFTER: Click listener moved OUTSIDE renderSlots()
function renderSlots() {
    fridgeSlotsContainer.innerHTML = "";
    
    fridges.forEach((fridge, index) => {
        // ... create elements
    });
}

// Listener attached once
document.addEventListener("click", (e) => {
    if (!e.target.closest(".slot-wrapper")) {
        document.querySelectorAll(".slot-context-menu").forEach(menu => {
            menu.classList.remove("active");
        });
    }
});
```

#### ADDED Code Encapsulation:
```javascript
// BEFORE: All functions in global scope
function initializeFridges() { ... }
function getFridges() { ... }
function setupEditPage() { ... }
// etc - all exposed to window

// AFTER: Wrapped in IIFE
(function() {
    function initializeFridges() { ... }
    function getFridges() { ... }
    function setupEditPage() { ... }
    // etc - all scoped to module
})();
```

---

### Frontend (recipes.js)

#### IMPROVED Error Handling:
```javascript
// BEFORE:
.then(res => res.json())
.then(data => {
    if (data.length === 0) {  // Could crash if data isn't array
        recipesContainer.innerHTML = "<p>No matching recipes found.</p>";
    }
})
.catch(err => {
    recipesContainer.innerHTML = "<p>Error loading recipes. Check server.</p>";
    console.error(err);
});

// AFTER:
.then(res => {
    if (!res.ok) throw new Error(`Server error ${res.status}`);
    return res.json();
})
.then(data => {
    if (!Array.isArray(data) || data.length === 0) {
        recipesContainer.innerHTML = "<p>No matching recipes found. Try adjusting your preferences or add more ingredients.</p>";
        return;
    }
})
.catch(() => {
    recipesContainer.innerHTML = "<p>Error loading recipes. Please try again.</p>";
    // No console.error
});
```

#### ADDED Code Encapsulation:
```javascript
// BEFORE: Global scope DOMContentLoaded listener
document.addEventListener("DOMContentLoaded", () => { ... });

// AFTER: Wrapped in IIFE
(function() {
    document.addEventListener("DOMContentLoaded", () => { ... });
})();
```

---

### Frontend (edit_fridge.html)

#### REMOVED AI Button:
```html
<!-- BEFORE -->
<div class="controls">
    <button id="addItemBtn">+ Add Item</button>
    <button id="addAIButton">+ Add from Receipt</button>
</div>

<!-- AFTER -->
<div class="controls">
    <button id="addItemBtn">+ Add Item</button>
</div>
```

#### REMOVED AI Event Handler:
```javascript
// BEFORE: In script.js
document.getElementById("addAIButton").addEventListener("click", () => {
    window.location.href = `/ai?fridge=${slotIndex + 1}`;
});

// AFTER: Completely removed
```

---

## Summary Statistics

- **Lines of code removed:** ~250+
- **Dead routes removed:** 5 (`/ai`, `/scan_image`, `/save_frame`, `/add_items`, `/confirm_items`)
- **Files deleted:** 2 (ai_fridge.html, ai_fridge.js)
- **Debug statements removed:** 10+ (console.log, print)
- **Error handling improvements:** 3 major areas
- **Bug fixes:** 4 (duplicate item names, event listener stacking, name editing closure, input validation)

All changes maintain backward compatibility with existing localStorage schema and recipe database structure.
