"""
Database Utilities - SQLite Setup
Creates and initializes the SQLite database schema for recipes, ingredients, and their relationships.
"""

import sqlite3

# Connect to SQLite database
conn = sqlite3.connect("recipes.db")
cursor = conn.cursor()

# === TABLE: Ingredients ===
# Stores unique food ingredients used in recipes
cursor.execute("""CREATE TABLE IF NOT EXISTS Ingredients (
    ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
)""")

# === TABLE: Recipes ===
# Stores recipe metadata including name, cook time, and source URL
cursor.execute("""CREATE TABLE IF NOT EXISTS Recipes (
    recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    total_time_min INTEGER,
    source_url TEXT NOT NULL,
    calories INTEGER,
    protein_g REAL
)""")

# === TABLE: Recipe_Ingredients ===
# Junction table linking recipes to their required ingredients with quantities
cursor.execute("""CREATE TABLE IF NOT EXISTS Recipe_Ingredients (
    recipe_id INTEGER,
    ingredient_id INTEGER,
    quantity_needed REAL,
    unit TEXT,
    PRIMARY KEY (recipe_id, ingredient_id),
    FOREIGN KEY (recipe_id) REFERENCES Recipes(recipe_id),
    FOREIGN KEY (ingredient_id) REFERENCES Ingredients(ingredient_id)
)""")

# Commit all table creations
conn.commit()