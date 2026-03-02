"""
Fridge Logic - Recipe Matching Engine
Determines which recipes can be made with available ingredients in the fridge.
"""

import os
import sqlite3


def get_possible_recipes(fridge):
    """
    Find all recipes that can be made with ingredients available in the fridge.

    Args:
        fridge (dict): Dictionary of {ingredient_name: quantity}
                      Example: {"milk": 1000, "eggs": 12, "butter": 200}

    Returns:
        list: List of tuples (recipe_name, source_url, calories, protein_g)
              containing recipes that can be made with available ingredients
    """
    # guard against bad input
    if not isinstance(fridge, dict):
        fridge = {}

    # normalize keys to lowercase for case-insensitive matching
    fridge_normalized = {}
    for k, v in fridge.items():
        try:
            fridge_normalized[str(k).lower()] = v
        except Exception:
            pass

    db_path = os.path.join(os.path.dirname(__file__), "db", "recipes.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT recipe_id, name, source_url, calories, protein_g FROM Recipes")
    recipes = cursor.fetchall()

    possible_recipes = []

    for recipe_id, name, url, calories, protein in recipes:
        cursor.execute("""
            SELECT i.name, ri.quantity_needed
            FROM Recipe_Ingredients ri
            JOIN Ingredients i ON ri.ingredient_id = i.ingredient_id
            WHERE ri.recipe_id = ?
        """, (recipe_id,))
        ingredients = cursor.fetchall()

        can_make = True

        for ing_name, qty_needed in ingredients:
            if qty_needed is None:
                continue

            available_qty = 0
            try:
                available_qty = float(fridge_normalized.get(ing_name.lower(), 0))
            except Exception:
                available_qty = 0

            if available_qty < qty_needed:
                can_make = False
                break

        if can_make:
            possible_recipes.append((name, url, calories, protein))

    conn.close()
    return possible_recipes