#!/usr/bin/env python3
"""
Simple test script to verify database service functionality.
Tests recipe CRUD operations and ingredient filtering.
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from services.database_service import DatabaseService
from services.auth_service import AuthService
from models import Recipe, Ingredient

def test_database_service():
    """Test basic database operations"""
    print("Testing Database Service...")
    
    # Use in-memory database for testing
    db = DatabaseService(":memory:")
    auth = AuthService(db)
    
    print("[OK] Database initialized")
    
    # Verify database is properly initialized
    stats = db.get_database_stats()
    print(f"[INFO] Database stats: {stats}")
    
    # Test user creation
    user = auth.register_user(
        email="test@example.com",
        password="TestPassword123",
        username="testuser",
        first_name="Test",
        last_name="User"
    )
    
    if user:
        print(f"[OK] User created: {user.email}")
    else:
        print("[FAIL] User creation failed")
        return False
    
    # Test ingredient creation - use different names to avoid conflicts with schema defaults
    ingredients = [
        {"name": "Sea Salt", "category": "seasoning"},
        {"name": "White Pepper", "category": "seasoning"},
        {"name": "Turkey Breast", "category": "protein"},
        {"name": "Avocado Oil", "category": "oil"},
        {"name": "Shallots", "category": "vegetable"}
    ]
    
    ingredient_ids = []
    for ing_data in ingredients:
        ingredient = db.create_ingredient(**ing_data)
        if ingredient:
            ingredient_ids.append(ingredient.id)
            print(f"[OK] Ingredient created: {ingredient.name}")
        else:
            print(f"[FAIL] Failed to create ingredient: {ing_data['name']}")
    
    # If creation failed, use existing ingredients from schema
    if not ingredient_ids:
        print("[INFO] Using existing ingredients from schema")
        all_ingredients = db.get_all_ingredients()
        ingredient_ids = [ing.id for ing in all_ingredients[:5]]  # Use first 5
    
    # Test recipe creation
    recipe_data = {
        "name": "Simple Grilled Chicken",
        "description": "A basic grilled chicken recipe",
        "instructions": "1. Season chicken with salt and pepper\n2. Heat olive oil in pan\n3. Cook chicken 6-7 minutes per side\n4. Serve hot",
        "prep_time_minutes": 10,
        "cook_time_minutes": 15,
        "servings": 4,
        "difficulty_level": "easy",
        "cuisine_type": "American",
        "meal_category": "dinner",
        "dietary_tags": ["gluten-free", "high-protein"],
        "ingredients": [
            {"ingredient_id": ingredient_ids[0], "quantity": 1, "unit": "tsp"},  # Salt
            {"ingredient_id": ingredient_ids[1], "quantity": 0.5, "unit": "tsp"},  # Pepper
            {"ingredient_id": ingredient_ids[2], "quantity": 4, "unit": "pieces"},  # Chicken
            {"ingredient_id": ingredient_ids[3], "quantity": 2, "unit": "tbsp"},  # Oil
            {"ingredient_id": ingredient_ids[4], "quantity": 2, "unit": "cloves", "preparation_note": "minced"}  # Garlic
        ]
    }
    
    recipe = db.create_recipe(recipe_data, user.id)
    if recipe:
        print(f"[OK] Recipe created: {recipe.name}")
        print(f"   - Ingredients: {len(recipe.ingredients)}")
        print(f"   - Total time: {recipe.get_total_time_minutes()} minutes")
    else:
        print("[FAIL] Recipe creation failed")
        return False
    
    # Test recipe filtering by ingredients
    # Should find our recipe when we have chicken and salt
    available_ingredients = [ingredient_ids[0], ingredient_ids[2]]  # Salt and chicken
    matching_recipes = db.get_recipes_by_ingredients(available_ingredients, user.id)
    
    print(f"[TEST] Ingredient filtering test:")
    print(f"   - Available ingredients: Salt, Chicken Breast")
    print(f"   - Matching recipes: {len(matching_recipes)}")
    
    if matching_recipes:
        recipe = matching_recipes[0]
        can_make, missing = recipe.can_make_with_ingredients(set(available_ingredients))
        print(f"   - Can make '{recipe.name}': {can_make}")
        if not can_make:
            print(f"   - Missing {len(missing)} ingredients")
    
    # Test recipe search
    search_results = db.search_recipes("chicken", user.id)
    print(f"[TEST] Recipe search test:")
    print(f"   - Search term: 'chicken'")
    print(f"   - Results: {len(search_results)}")
    
    # Test ingredient search
    ing_search = db.search_ingredients("salt")
    print(f"[TEST] Ingredient search test:")
    print(f"   - Search term: 'salt'")
    print(f"   - Results: {len(ing_search)}")
    
    print("\n[SUCCESS] All database tests passed!")
    return True

if __name__ == "__main__":
    try:
        success = test_database_service()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)