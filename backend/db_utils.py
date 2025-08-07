import sqlite3

conn = sqlite3.connect("recipes.db")
cursor = conn.cursor()


cursor.execute("""CREATE TABLE IF NOT EXISTS Ingredients (
    ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS Recipes (
    recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    total_time_min INTEGER,
    source_url TEXT NOT NULL
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS Recipe_Ingredients (
    recipe_id INTEGER,
    ingredient_id INTEGER,
    quantity_needed REAL,
    unit TEXT,
    PRIMARY KEY (recipe_id, ingredient_id),
    FOREIGN KEY (recipe_id) REFERENCES Recipes(recipe_id),
    FOREIGN KEY (ingredient_id) REFERENCES Ingredients(ingredient_id)
)""")


conn.commit()