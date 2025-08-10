"""
Recipe deletion utility for removing problematic recipes from the database.
"""
import sqlite3
from pathlib import Path

def delete_recipe(recipe_id: int):
    """Delete a recipe and all its relationships from the database."""
    db_path = Path("herbalism.db")
    if not db_path.exists():
        print("Database not found")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Start transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # First, check if recipe exists
        cursor.execute("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
        result = cursor.fetchone()
        if not result:
            print(f"Recipe ID {recipe_id} not found")
            conn.rollback()
            return False
        
        recipe_name = result[0]
        print(f"Deleting recipe: {recipe_name} (ID: {recipe_id})")
        
        # Delete recipe-herb relationships first (foreign key constraint)
        cursor.execute("DELETE FROM recipe_herbs WHERE recipe_id = ?", (recipe_id,))
        deleted_relationships = cursor.rowcount
        print(f"Deleted {deleted_relationships} herb relationships")
        
        # Delete the recipe
        cursor.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        deleted_recipes = cursor.rowcount
        print(f"Deleted {deleted_recipes} recipe record")
        
        # Commit transaction
        conn.commit()
        print(f"Successfully deleted recipe '{recipe_name}' (ID: {recipe_id})")
        return True
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error deleting recipe: {e}")
        return False
    finally:
        conn.close()

def list_recipes():
    """List all recipes in the database."""
    db_path = Path("herbalism.db")
    if not db_path.exists():
        print("Database not found")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, name, category FROM recipes ORDER BY id")
        recipes = cursor.fetchall()
        
        print("Current recipes in database:")
        print("-" * 50)
        for recipe_id, name, category in recipes:
            print(f"ID {recipe_id}: {name} ({category})")
        print(f"\nTotal: {len(recipes)} recipes")
        
    except sqlite3.Error as e:
        print(f"Error listing recipes: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Recipe Management Utility")
    print("=" * 40)
    
    # List current recipes
    list_recipes()
    
    print("\nDeleting problematic herbal shampoo recipe (ID 103)...")
    success = delete_recipe(103)
    
    if success:
        print("\nUpdated recipe list:")
        list_recipes()
    else:
        print("\nDeletion failed!")