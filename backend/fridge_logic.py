#Script to run the comparaison
import os
import sqlite3


def get_possible_recipes(fridge):

    db_path = os.path.join(os.path.dirname(__file__), "db", "recipes.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all recipes
    cursor.execute("SELECT recipe_id, name, source_url, calories, protein_g FROM Recipes")
    recipes = cursor.fetchall()

    possible_recipes = []

    for recipe_id, name, url, calories, protein in recipes:
        # Get ingredients for this recipe
        cursor.execute("""
            SELECT i.name, ri.quantity_needed
            FROM Recipe_Ingredients ri
            JOIN Ingredients i ON ri.ingredient_id = i.ingredient_id
            WHERE ri.recipe_id = ?
        """, (recipe_id,))
        
        ingredients = cursor.fetchall()

        can_make = True

        for ing_name, qty_needed in ingredients:
            # Skip optional ingredients (qty is NULL)
            if qty_needed is None:
                continue
            
            # Check if fridge has enough
            try:
                fridge_qty = float(fridge.get(ing_name, 0))
            except ValueError:
                fridge_qty = 0

            if fridge_qty < qty_needed:
                can_make = False
                break
        
        if can_make:
            possible_recipes.append((name, url,calories,protein))

    conn.close()
    return possible_recipes

'''#TestScript
fridge = {
    "Bagel": 1,
    "Cream cheese": 1,
    "Hot honey": 1,
    "Butter": 1,
    "Milk": 1000, 
    "Strawberries": 5
    # Skip "Flaky salt" since it's optional
}

preferences = { 
    "Calorie Max": 1000, 
    "Calorie Min": 200,
    "Protein": 10,
}

recipes = get_possible_recipes(fridge)



if recipes:
    for name, url, calories, protein in recipes:
        if preferences["Calorie Max"] >= calories >= preferences["Calorie Min"] and preferences["Protein"] <= protein:
           print(f"You can make: {name} via {url}")
        else:
           print("No recipes match your ingredients.")

'''