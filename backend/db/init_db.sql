-- SQL cleanup script to remove a specific recipe from the database
-- Deletes recipe_id = 2 and its associated ingredients through cascading foreign keys

DELETE FROM Recipes
WHERE recipe_id = 2;