#!/usr/bin/env python3
"""
Web scraper for AllRecipes.com
Scrapes recipes and adds them to the MealMaker database.
Note: This is for educational/personal use only (non-monetized project).
"""

import sqlite3
import os
import re
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# Database path
db_path = os.path.join(os.path.dirname(__file__), "recipes.db")

# Headers to mimic a browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def get_db_connection():
    """Create a database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def scrape_recipe_cards(page_url):
    """
    Scrape recipe cards from AllRecipes search/category page.
    Returns a list of recipe URLs.
    """
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        recipe_urls = []
        
        # Find recipe cards - look for various link patterns
        # AllRecipes recipe pages are typically at /recipe/ID/name/
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href and '/recipe/' in href and 'allrecipes.com' in href:
                full_url = urljoin(page_url, href)
                # Clean up URL (remove query parameters, ensure trailing slash)
                full_url = full_url.split('?')[0]
                if full_url.endswith('/'):
                    recipe_urls.append(full_url)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in recipe_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls[:10]  # Return up to 10 unique recipes per page
    
    except Exception as e:
        print(f"❌ Error scraping {page_url}: {e}")
        return []

def parse_recipe_page(recipe_url):
    """
    Parse a single recipe page from AllRecipes.
    Returns recipe data with name, ingredients, calories, and protein.
    """
    try:
        response = requests.get(recipe_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        recipe_data = {
            'name': None,
            'url': recipe_url,
            'calories': None,
            'protein': None,
            'time_minutes': None,
            'ingredients': []
        }
        
        # Try to extract from JSON-LD first (most reliable)
        scripts = soup.find_all('script', {'type': 'application/ld+json'})
        
        for script in scripts:
            try:
                import json
                json_str = script.string
                if not json_str:
                    continue
                    
                json_data = json.loads(json_str)
                
                # Handle nested structures - look for Recipe type
                def find_recipe(obj):
                    if isinstance(obj, dict):
                        if obj.get('@type') == 'Recipe':
                            return obj
                        # Check @graph for Recipe
                        if '@graph' in obj:
                            for item in obj['@graph']:
                                result = find_recipe(item)
                                if result:
                                    return result
                        # Check nested objects
                        for value in obj.values():
                            result = find_recipe(value)
                            if result:
                                return result
                    elif isinstance(obj, list):
                        for item in obj:
                            result = find_recipe(item)
                            if result:
                                return result
                    return None
                
                recipe = find_recipe(json_data)
                
                if recipe:
                    # Get recipe name
                    if 'name' in recipe and not recipe_data['name']:
                        recipe_data['name'] = recipe['name'].strip()
                    
                    # Get nutrition info
                    nutrition = recipe.get('nutrition', {})
                    if isinstance(nutrition, dict):
                        if 'calories' in nutrition and not recipe_data['calories']:
                            try:
                                cal_val = nutrition['calories']
                                if isinstance(cal_val, (int, float)):
                                    recipe_data['calories'] = int(cal_val)
                                else:
                                    # Try to extract from string
                                    match = re.search(r'(\d+)', str(cal_val))
                                    if match:
                                        recipe_data['calories'] = int(match.group(1))
                            except:
                                pass
                        
                        if 'proteinContent' in nutrition and not recipe_data['protein']:
                            try:
                                protein_val = nutrition['proteinContent']
                                if isinstance(protein_val, (int, float)):
                                    recipe_data['protein'] = float(protein_val)
                                else:
                                    # Try to extract from string
                                    match = re.search(r'(\d+(?:\.\d+)?)', str(protein_val))
                                    if match:
                                        recipe_data['protein'] = float(match.group(1))
                            except:
                                pass
                    
                    # Get cook time
                    if 'cookTime' in recipe and not recipe_data['time_minutes']:
                        cook_time = recipe['cookTime']
                        match = re.search(r'PT(?:(\d+)H)?(?:(\d+)M)?', cook_time)
                        if match:
                            hours = int(match.group(1)) if match.group(1) else 0
                            minutes = int(match.group(2)) if match.group(2) else 0
                            total = hours * 60 + minutes
                            if total > 0:
                                recipe_data['time_minutes'] = total
                    
                    # Get ingredients
                    if not recipe_data['ingredients'] and 'recipeIngredient' in recipe:
                        ingredients_list = recipe.get('recipeIngredient', [])
                        if isinstance(ingredients_list, list):
                            for ing_str in ingredients_list:
                                ing_str = str(ing_str).strip()
                                if ing_str and len(ing_str) > 2:
                                    parsed = parse_ingredient_string(ing_str)
                                    if parsed and parsed['name'] and len(parsed['name']) > 1:
                                        recipe_data['ingredients'].append(parsed)
            except Exception as e:
                continue
        
        # Validate we have minimum required data
        if recipe_data['name'] and recipe_data['ingredients']:
            return recipe_data
        else:
            return None
    
    except Exception as e:
        return None

def parse_ingredient_string(ing_str):
    """
    Parse ingredient string into components.
    Returns dict with 'name', 'quantity', 'unit'
    Example: "2 cups all-purpose flour" -> {'name': 'all-purpose flour', 'quantity': 2.0, 'unit': 'cups'}
    """
    ing_str = ing_str.strip()
    
    # Pattern to match: number (with fractions) + unit + ingredient name
    pattern = r'^([\d\.]+(?:\s*[/-]\s*[\d\.]+)?)\s*([a-zA-Z]+)?(.*)$'
    match = re.match(pattern, ing_str)
    
    if match:
        qty_str = match.group(1).replace(' ', '')
        unit = match.group(2) or ''
        name = match.group(3).strip()
        
        # Convert fraction strings
        if '/' in qty_str:
            parts = qty_str.split('/')
            try:
                qty = float(parts[0]) / float(parts[1])
            except:
                qty = 1.0
        else:
            try:
                qty = float(qty_str)
            except:
                qty = 1.0
        
        if name:
            return {
                'name': name,
                'quantity': qty,
                'unit': unit
            }
    
    # Fallback: treat whole string as ingredient name
    return {
        'name': ing_str,
        'quantity': 1,
        'unit': ''
    }

def add_recipes_to_db(recipes_list):
    """
    Add scraped recipes to the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    added = 0
    skipped = 0
    
    for recipe_data in recipes_list:
        try:
            # Check if recipe already exists
            cursor.execute(
                "SELECT recipe_id FROM Recipes WHERE source_url = ?",
                (recipe_data['url'],)
            )
            if cursor.fetchone():
                skipped += 1
                continue
            
            # Insert recipe
            cursor.execute(
                """INSERT INTO Recipes (name, source_url, calories, protein_g, total_time_min)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    recipe_data['name'],
                    recipe_data['url'],
                    recipe_data['calories'],
                    recipe_data['protein'],
                    recipe_data['time_minutes']
                )
            )
            recipe_id = cursor.lastrowid
            
            # Add ingredients
            for ing in recipe_data['ingredients']:
                ing_name = ing['name'].lower().strip()
                
                # Insert or get ingredient
                cursor.execute(
                    "INSERT OR IGNORE INTO Ingredients (name) VALUES (?)",
                    (ing_name,)
                )
                
                cursor.execute(
                    "SELECT ingredient_id FROM Ingredients WHERE name = ?",
                    (ing_name,)
                )
                ing_id = cursor.fetchone()[0]
                
                # Add recipe-ingredient relationship
                cursor.execute(
                    """INSERT INTO Recipe_Ingredients 
                       (recipe_id, ingredient_id, quantity_needed, unit)
                       VALUES (?, ?, ?, ?)""",
                    (recipe_id, ing_id, ing['quantity'], ing['unit'])
                )
            
            added += 1
            print(f"✅ Added: {recipe_data['name']}")
        
        except Exception as e:
            print(f"⚠️  Error adding recipe: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    return added, skipped

def main():
    """Main scraper function."""
    print("🍽️  AllRecipes.com Scraper for MealMaker")
    print("=" * 50)
    
    # List of AllRecipes category/search pages to scrape
    recipe_pages = [
        "https://www.allrecipes.com/",  # Main recipes page
        "https://www.allrecipes.com/search?q=chicken",  # Chicken recipes
        "https://www.allrecipes.com/search?q=pasta",  # Pasta recipes
        "https://www.allrecipes.com/search?q=quick",  # Quick recipes
        "https://www.allrecipes.com/search?q=healthy",  # Healthy recipes
    ]
    
    all_recipes = []
    
    for page_url in recipe_pages:
        print(f"\n📄 Scraping recipe cards from: {page_url}")
        recipe_urls = scrape_recipe_cards(page_url)
        print(f"   Found {len(recipe_urls)} recipes")
        
        # Limit to 5 recipes per page to avoid overloading
        for i, recipe_url in enumerate(recipe_urls[:5]):
            print(f"   [{i+1}/5] Parsing: {recipe_url}")
            recipe_data = parse_recipe_page(recipe_url)
            
            if recipe_data:
                all_recipes.append(recipe_data)
                print(f"      ✓ {recipe_data['name']}")
            
            time.sleep(1)  # Be respectful to the server
    
    print(f"\n\n📊 Summary")
    print("=" * 50)
    print(f"Total recipes scraped: {len(all_recipes)}")
    
    if all_recipes:
        print("\nAdding recipes to database...")
        added, skipped = add_recipes_to_db(all_recipes)
        print(f"✅ Added: {added} recipes")
        print(f"⏭️  Skipped: {skipped} recipes (already in DB)")

if __name__ == "__main__":
    main()
