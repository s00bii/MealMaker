#!/usr/bin/env python3
"""
Seed script for populating MealMaker recipe database with recipes from AllRecipes.
Run this once to populate the database with recipes and ingredients.
"""

import sqlite3
import os

# Path to database
db_path = os.path.join(os.path.dirname(__file__), "db", "recipes.db")

def seed_recipes():
    """Populate the database with sample recipes from AllRecipes."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("DELETE FROM Recipe_Ingredients")
    cursor.execute("DELETE FROM Recipes")
    cursor.execute("DELETE FROM Ingredients")

    # === ADD INGREDIENTS ===
    ingredients = [
        "milk", "eggs", "cheese", "butter", "bread", "flour", "salt", 
        "pepper", "sugar", "oil", "vegetable oil", "chicken", "beef", "onion", "garlic",
        "tomato", "lettuce", "potatoes", "rice", "pasta", "beans", "water",
        "pork sausage", "biscuit mix", "cheddar cheese", "olive oil", "celery",
        "parsley", "italian seasoning", "red pepper flakes", "chicken broth",
        "tomato sauce", "ditalini pasta", "cannellini beans", "broccoli", "bell pepper",
        "carrots", "green onion", "soy sauce", "sesame seeds", "greek yogurt",
        "cottage cheese", "apple", "dried cranberries", "pecans", "dijon mustard",
        "ginger", "garam masala", "cumin", "chili powder", "bay leaf", "tomato puree",
        "half-and-half", "plain yogurt", "chicken thighs", "cornstarch", "shallot",
        "lemon juice", "cayenne pepper", "peanut oil", "red bell pepper", "white onion"
    ]
    
    for ingredient in ingredients:
        cursor.execute("INSERT INTO Ingredients (name) VALUES (?)", (ingredient,))
    
    conn.commit()
    
    # Get ingredient IDs
    cursor.execute("SELECT ingredient_id, name FROM Ingredients")
    ing_dict = {name: ing_id for ing_id, name in cursor.fetchall()}

    # === ADD RECIPES - Mix of AllRecipes and originals ===
    recipes = [
        # AllRecipes recipes
        ("Pasta e Fagioli (Pasta and Beans)", "https://www.allrecipes.com/recipe/13009/pasta-fagioli/", 225, 11),
        ("Quick Beef Stir-Fry", "https://www.allrecipes.com/recipe/228823/quick-beef-stir-fry/", 268, 23),
        ("Sausage Balls", "https://www.allrecipes.com/recipe/21649/sausage-balls/", 264, 13),
        ("Healthy Chicken Salad", "https://www.allrecipes.com/recipe/272849/healthy-chicken-salad/", 168, 15),
        ("Chicken Makhani (Indian Butter Chicken)", "https://www.allrecipes.com/recipe/45957/chicken-makhani-indian-butter-chicken/", 408, 23),
        # Original recipes
        ("Simple Omelette", "https://example.com/omelette", 300, 18),
        ("Grilled Cheese", "https://example.com/grilled-cheese", 400, 16),
        ("Fried Rice", "https://example.com/fried-rice", 450, 15),
        ("Buttered Toast", "https://example.com/toast", 250, 8),
        ("Scrambled Eggs", "https://example.com/scrambled", 200, 12),
        ("Cheese Sandwich", "https://example.com/sandwich", 350, 14),
    ]

    recipe_ids = {}
    for name, url, calories, protein in recipes:
        cursor.execute(
            "INSERT INTO Recipes (name, source_url, calories, protein_g) VALUES (?, ?, ?, ?)",
            (name, url, calories, protein)
        )
        recipe_id = cursor.lastrowid
        recipe_ids[name] = recipe_id

    conn.commit()

    # === ADD RECIPE INGREDIENTS (RELATIONSHIPS) ===
    recipe_ingredients = {
        "Pasta e Fagioli (Pasta and Beans)": [
            ("olive oil", 1, "tbsp"),
            ("onion", 1, "medium"),
            ("celery", 2, "stalks"),
            ("garlic", 3, "cloves"),
            ("parsley", 2, "tsp"),
            ("italian seasoning", 1, "tsp"),
            ("red pepper flakes", 0.25, "tsp"),
            ("salt", 1, "tsp"),
            ("chicken broth", 1, "can"),
            ("tomato", 2, "medium"),
            ("tomato sauce", 1, "can"),
            ("ditalini pasta", 0.5, "cup"),
            ("cannellini beans", 1, "can"),
        ],
        "Quick Beef Stir-Fry": [
            ("vegetable oil", 2, "tbsp"),
            ("chicken", 1, "pound"),
            ("broccoli", 1.5, "cups"),
            ("bell pepper", 1, "red"),
            ("carrots", 2, "medium"),
            ("green onion", 1, "whole"),
            ("garlic", 1, "tsp"),
            ("soy sauce", 2, "tbsp"),
            ("sesame seeds", 2, "tbsp"),
        ],
        "Sausage Balls": [
            ("pork sausage", 1, "pound"),
            ("biscuit mix", 2, "cups"),
            ("cheddar cheese", 12, "ounces"),
        ],
        "Healthy Chicken Salad": [
            ("greek yogurt", 6, "ounces"),
            ("cottage cheese", 0.5, "cup"),
            ("celery", 0.5, "cup"),
            ("apple", 0.5, "cup"),
            ("dried cranberries", 0.25, "cup"),
            ("onion", 2, "tbsp"),
            ("pecans", 2, "tbsp"),
            ("dijon mustard", 0.5, "tbsp"),
            ("chicken", 1.25, "cups"),
            ("salt", 1, "pinch"),
            ("pepper", 1, "pinch"),
        ],
        "Chicken Makhani (Indian Butter Chicken)": [
            ("peanut oil", 2, "tbsp"),
            ("shallot", 1, "whole"),
            ("onion", 0.25, "medium"),
            ("butter", 2, "tbsp"),
            ("ginger", 1, "tbsp"),
            ("garlic", 1, "tbsp"),
            ("lemon juice", 2, "tsp"),
            ("garam masala", 2, "tsp"),
            ("chili powder", 1, "tsp"),
            ("cumin", 1, "tsp"),
            ("bay leaf", 1, "whole"),
            ("tomato puree", 1, "cup"),
            ("half-and-half", 1, "cup"),
            ("plain yogurt", 0.25, "cup"),
            ("chicken thighs", 1, "pound"),
            ("cayenne pepper", 0.25, "tsp"),
            ("cornstarch", 1, "tbsp"),
            ("water", 0.25, "cup"),
        ],
        "Simple Omelette": [
            ("eggs", 2, "large"),
            ("butter", 1, "tbsp"),
            ("salt", 0.5, "tsp"),
            ("pepper", 0.25, "tsp"),
        ],
        "Grilled Cheese": [
            ("bread", 2, "slices"),
            ("cheese", 2, "slices"),
            ("butter", 2, "tbsp"),
        ],
        "Fried Rice": [
            ("rice", 2, "cups"),
            ("eggs", 2, "large"),
            ("oil", 2, "tbsp"),
            ("onion", 1, "medium"),
            ("garlic", 2, "cloves"),
        ],
        "Buttered Toast": [
            ("bread", 2, "slices"),
            ("butter", 1, "tbsp"),
            ("salt", 0.25, "tsp"),
        ],
        "Scrambled Eggs": [
            ("eggs", 3, "large"),
            ("butter", 1, "tbsp"),
            ("milk", 2, "tbsp"),
            ("salt", 0.25, "tsp"),
        ],
        "Cheese Sandwich": [
            ("bread", 2, "slices"),
            ("cheese", 2, "slices"),
            ("butter", 1, "tbsp"),
        ],
    }

    for recipe_name, ingredients_list in recipe_ingredients.items():
        recipe_id = recipe_ids[recipe_name]
        for ing_name, qty, unit in ingredients_list:
            ing_id = ing_dict[ing_name]
            cursor.execute(
                """INSERT INTO Recipe_Ingredients (recipe_id, ingredient_id, quantity_needed, unit) 
                   VALUES (?, ?, ?, ?)""",
                (recipe_id, ing_id, qty, unit)
            )

    conn.commit()
    conn.close()
    
    print("✅ Database seeded successfully!")
    print(f"   - Added {len(ingredients)} ingredients")
    print(f"   - Added {len(recipes)} recipes")
    print(f"   - Created recipe-ingredient relationships")

if __name__ == "__main__":
    seed_recipes()
