#!/usr/bin/env python3
"""
Test script for collection service functionality.
Tests collection CRUD operations, shopping list generation, and sharing features.
"""

import sys
from pathlib import Path
import json
import tempfile
import os

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from services.collection_service import CollectionService
from services.database_service import DatabaseService
from services.auth_service import AuthService
from models import Collection, Recipe, Ingredient, RecipeIngredient, ShoppingList
from datetime import datetime

def create_test_data(db_service, auth_service):
    """Create test users, recipes, and ingredients for testing"""
    print("Creating test data...")
    
    import time
    unique_suffix = str(int(time.time() * 1000))[-6:]  # Use timestamp for uniqueness
    
    # Create test users
    user1 = auth_service.register_user(f"user1{unique_suffix}@test.com", "Password123", f"testuser1{unique_suffix}", "Test", "User1")
    user2 = auth_service.register_user(f"user2{unique_suffix}@test.com", "Password123", f"testuser2{unique_suffix}", "Test", "User2")
    
    # Create test ingredients with unique names
    ingredients = []
    test_ingredients = [
        (f"Salt{unique_suffix}", "seasoning"),
        (f"Pepper{unique_suffix}", "seasoning"),
        (f"Chicken Breast{unique_suffix}", "protein"),
        (f"Olive Oil{unique_suffix}", "oil"),
        (f"Garlic{unique_suffix}", "vegetable"),
        (f"Onion{unique_suffix}", "vegetable"),
        (f"Rice{unique_suffix}", "grain"),
        (f"Tomatoes{unique_suffix}", "vegetable")
    ]
    
    for name, category in test_ingredients:
        ingredient = db_service.create_ingredient(name, category)
        if ingredient:
            ingredients.append((ingredient.id, name, category))
        else:
            print(f"Warning: Failed to create ingredient {name}")
    
    if len(ingredients) < 7:
        raise Exception(f"Failed to create enough ingredients. Only created {len(ingredients)} out of {len(test_ingredients)}")
    
    # Create test recipes
    recipes = []
    
    # Recipe 1: Chicken Rice
    recipe_ingredients_1 = [
        {"ingredient_id": ingredients[2][0], "quantity": 1.0, "unit": "lb"},  # Chicken Breast
        {"ingredient_id": ingredients[6][0], "quantity": 2.0, "unit": "cups"},  # Rice
        {"ingredient_id": ingredients[4][0], "quantity": 3.0, "unit": "cloves"},  # Garlic
        {"ingredient_id": ingredients[3][0], "quantity": 2.0, "unit": "tbsp"},  # Olive Oil
        {"ingredient_id": ingredients[0][0], "quantity": 1.0, "unit": "tsp"},  # Salt
    ]
    
    recipe1_data = {
        "name": "Chicken Rice Bowl",
        "description": "Simple chicken and rice dish",
        "instructions": "1. Cook rice. 2. Season chicken. 3. Cook chicken. 4. Serve over rice.",
        "ingredients": recipe_ingredients_1,
        "prep_time_minutes": 15,
        "cook_time_minutes": 25,
        "servings": 4
    }
    
    recipe1 = db_service.create_recipe(recipe1_data, user1.id)
    if recipe1:
        recipes.append(recipe1.id)
    
    # Recipe 2: Garlic Tomato Pasta
    recipe_ingredients_2 = [
        {"ingredient_id": ingredients[4][0], "quantity": 4.0, "unit": "cloves"},  # Garlic
        {"ingredient_id": ingredients[7][0], "quantity": 2.0, "unit": "cups"},  # Tomatoes
        {"ingredient_id": ingredients[3][0], "quantity": 3.0, "unit": "tbsp"},  # Olive Oil
        {"ingredient_id": ingredients[0][0], "quantity": 1.0, "unit": "tsp"},  # Salt
        {"ingredient_id": ingredients[1][0], "quantity": 0.5, "unit": "tsp"},  # Pepper
    ]
    
    recipe2_data = {
        "name": "Garlic Tomato Pasta",
        "description": "Fresh tomato pasta with garlic",
        "instructions": "1. Heat oil. 2. Sauté garlic. 3. Add tomatoes. 4. Season and serve.",
        "ingredients": recipe_ingredients_2,
        "prep_time_minutes": 10,
        "cook_time_minutes": 15,
        "servings": 2
    }
    
    recipe2 = db_service.create_recipe(recipe2_data, user1.id)
    if recipe2:
        recipes.append(recipe2.id)
    
    print(f"[OK] Created {len(ingredients)} ingredients, {len(recipes)} recipes, 2 users")
    return user1, user2, ingredients, recipes


def test_collection_crud_operations():
    """Test basic CRUD operations for collections"""
    print("\nTesting Collection CRUD Operations...")
    
    db = DatabaseService(":memory:")
    auth_service = AuthService(db)
    collection_service = CollectionService(db)
    
    user1, user2, ingredients, recipes = create_test_data(db, auth_service)
    
    # Test creating collection
    collection = collection_service.create_collection(
        name="My Dinner Recipes",
        user_id=user1.id,
        description="Collection of my favorite dinner recipes",
        tags=["dinner", "favorites"],
        is_public=False
    )
    
    assert collection is not None, "Failed to create collection"
    assert collection.name == "My Dinner Recipes", "Collection name incorrect"
    assert collection.user_id == user1.id, "Collection user_id incorrect"
    assert "dinner" in collection.tags, "Collection tags not set correctly"
    assert collection.is_public == False, "Collection privacy setting incorrect"
    
    print("[OK] Collection creation successful")
    
    # Test getting collection
    retrieved_collection = collection_service.get_collection(collection.id)
    assert retrieved_collection is not None, "Failed to retrieve collection"
    assert retrieved_collection.name == collection.name, "Retrieved collection name mismatch"
    
    print("[OK] Collection retrieval successful")
    
    # Test updating collection
    success = collection_service.update_collection(
        collection.id,
        name="Updated Dinner Recipes",
        description="Updated description",
        tags=["dinner", "updated"],
        is_public=True
    )
    
    assert success, "Failed to update collection"
    
    updated_collection = collection_service.get_collection(collection.id)
    assert updated_collection.name == "Updated Dinner Recipes", "Collection name not updated"
    assert updated_collection.is_public == True, "Collection privacy not updated"
    assert "updated" in updated_collection.tags, "Collection tags not updated"
    
    print("[OK] Collection update successful")
    
    # Test getting user collections
    user_collections = collection_service.get_user_collections(user1.id)
    assert len(user_collections) >= 1, "Failed to get user collections"
    
    collection_names = [c.name for c in user_collections]
    assert "Updated Dinner Recipes" in collection_names, "User collection not found"
    
    print("[OK] User collections retrieval successful")
    
    # Test deleting collection
    delete_success = collection_service.delete_collection(collection.id, user1.id)
    assert delete_success, "Failed to delete collection"
    
    deleted_collection = collection_service.get_collection(collection.id)
    assert deleted_collection is None, "Collection not properly deleted"
    
    print("[OK] Collection deletion successful")
    return True


def test_recipe_collection_associations():
    """Test adding and removing recipes from collections"""
    print("\nTesting Recipe-Collection Associations...")
    
    db = DatabaseService(":memory:")
    auth_service = AuthService(db)
    collection_service = CollectionService(db)
    
    user1, user2, ingredients, recipes = create_test_data(db, auth_service)
    
    # Create collection
    collection = collection_service.create_collection(
        name="Test Recipe Collection",
        user_id=user1.id
    )
    
    assert collection is not None, "Failed to create collection"
    
    # Test adding recipes to collection
    for recipe_id in recipes:
        success = collection_service.add_recipe_to_collection(recipe_id, collection.id)
        assert success, f"Failed to add recipe {recipe_id} to collection"
    
    print("[OK] Recipes added to collection")
    
    # Test getting collection recipes
    collection_recipes = collection_service.get_collection_recipes(collection.id)
    assert len(collection_recipes) == len(recipes), "Incorrect number of recipes in collection"
    
    recipe_names = [r.name for r in collection_recipes]
    assert "Chicken Rice Bowl" in recipe_names, "Recipe not found in collection"
    assert "Garlic Tomato Pasta" in recipe_names, "Recipe not found in collection"
    
    print("[OK] Collection recipes retrieval successful")
    
    # Test removing recipe from collection
    success = collection_service.remove_recipe_from_collection(recipes[0], collection.id)
    assert success, "Failed to remove recipe from collection"
    
    updated_recipes = collection_service.get_collection_recipes(collection.id)
    assert len(updated_recipes) == len(recipes) - 1, "Recipe not properly removed from collection"
    
    print("[OK] Recipe removal from collection successful")
    
    # Test collection with recipes
    updated_collection = collection_service.get_collection(collection.id)
    assert len(updated_collection.recipe_ids) == len(recipes) - 1, "Collection recipe_ids not updated"
    
    print("[OK] Recipe-collection associations working correctly")
    return True


def test_shopping_list_generation():
    """Test shopping list generation from collections"""
    print("\nTesting Shopping List Generation...")
    
    db = DatabaseService(":memory:")
    auth_service = AuthService(db)
    collection_service = CollectionService(db)
    
    user1, user2, ingredients, recipes = create_test_data(db, auth_service)
    
    # Create collection with recipes
    collection = collection_service.create_collection(
        name="Weekly Meal Plan",
        user_id=user1.id
    )
    
    # Add both recipes
    for recipe_id in recipes:
        collection_service.add_recipe_to_collection(recipe_id, collection.id)
    
    # Generate shopping list
    shopping_list = collection_service.generate_shopping_list(collection.id)
    
    assert shopping_list is not None, "Failed to generate shopping list"
    assert shopping_list.collection_id == collection.id, "Shopping list collection_id incorrect"
    assert shopping_list.collection_name == collection.name, "Shopping list collection_name incorrect"
    assert shopping_list.total_recipes == 2, "Shopping list total_recipes incorrect"
    
    print("[OK] Shopping list generated successfully")
    
    # Test ingredient consolidation
    ingredients_in_list = [item.ingredient_name for item in shopping_list.items]
    garlic_names = [name for name in ingredients_in_list if "Garlic" in name]
    salt_names = [name for name in ingredients_in_list if "Salt" in name]
    oil_names = [name for name in ingredients_in_list if "Olive Oil" in name]
    
    assert len(garlic_names) > 0, f"Garlic not in shopping list: {ingredients_in_list}"
    assert len(salt_names) > 0, f"Salt not in shopping list: {ingredients_in_list}"
    assert len(oil_names) > 0, f"Olive Oil not in shopping list: {ingredients_in_list}"
    
    # Find garlic item (should be consolidated from both recipes)
    garlic_item = None
    for item in shopping_list.items:
        if "Garlic" in item.ingredient_name:
            garlic_item = item
            break
    
    assert garlic_item is not None, "Garlic item not found in shopping list"
    assert garlic_item.total_quantity == 7.0, f"Garlic quantity not consolidated correctly: {garlic_item.total_quantity}"  # 3 + 4 cloves
    assert len(garlic_item.recipe_names) == 2, "Garlic should be used in both recipes"
    
    print("[OK] Ingredient consolidation working correctly")
    
    # Test shopping list categories
    categories = shopping_list.get_items_by_category()
    assert "seasoning" in categories, "Seasoning category not found"
    assert "vegetable" in categories, "Vegetable category not found"
    
    seasoning_items = categories["seasoning"]
    seasoning_names = [item.ingredient_name for item in seasoning_items]
    salt_found = any("Salt" in name for name in seasoning_names)
    pepper_found = any("Pepper" in name for name in seasoning_names)
    assert salt_found, f"Salt not in seasoning category: {seasoning_names}"
    assert pepper_found, f"Pepper not in seasoning category: {seasoning_names}"
    
    print("[OK] Shopping list categories working correctly")
    
    # Test empty collection shopping list
    empty_collection = collection_service.create_collection("Empty Collection", user1.id)
    empty_shopping_list = collection_service.generate_shopping_list(empty_collection.id)
    
    assert empty_shopping_list is not None, "Failed to generate empty shopping list"
    assert empty_shopping_list.total_recipes == 0, "Empty shopping list should have 0 recipes"
    assert len(empty_shopping_list.items) == 0, "Empty shopping list should have no items"
    
    print("[OK] Shopping list generation working correctly")
    return True


def test_collection_sharing():
    """Test collection sharing functionality"""
    print("\nTesting Collection Sharing...")
    
    db = DatabaseService(":memory:")
    auth_service = AuthService(db)
    collection_service = CollectionService(db)
    
    user1, user2, ingredients, recipes = create_test_data(db, auth_service)
    
    # Create collection
    collection = collection_service.create_collection(
        name="Shared Recipe Collection",
        user_id=user1.id,
        description="A collection to share with friends"
    )
    
    # Add recipes to collection
    for recipe_id in recipes:
        collection_service.add_recipe_to_collection(recipe_id, collection.id)
    
    # Test generating share token
    share_token = collection_service.generate_share_token(collection.id, user1.id)
    assert share_token is not None, "Failed to generate share token"
    assert len(share_token) > 20, "Share token too short"
    
    print("[OK] Share token generation successful")
    
    # Test that collection is now public
    shared_collection = collection_service.get_collection(collection.id)
    assert shared_collection.is_public == True, "Collection not made public after sharing"
    assert shared_collection.share_token == share_token, "Share token not saved to collection"
    
    print("[OK] Collection made public with share token")
    
    # Test getting collection by share token
    token_collection = collection_service.get_collection_by_share_token(share_token)
    assert token_collection is not None, "Failed to get collection by share token"
    assert token_collection.id == collection.id, "Wrong collection retrieved by share token"
    assert token_collection.name == "Shared Recipe Collection", "Retrieved collection name incorrect"
    
    print("[OK] Collection retrieval by share token successful")
    
    # Test that user2 can access shared collection
    user2_collections = collection_service.get_user_collections(user2.id, include_public=True)
    shared_collection_names = [c.name for c in user2_collections]
    assert "Shared Recipe Collection" in shared_collection_names, "User2 cannot access shared collection"
    
    print("[OK] Shared collection accessible to other users")
    
    # Test unauthorized sharing attempt
    unauthorized_token = collection_service.generate_share_token(collection.id, user2.id)
    assert unauthorized_token is None, "Unauthorized user was able to generate share token"
    
    print("[OK] Unauthorized sharing properly blocked")
    
    # Test revoking share token
    revoke_success = collection_service.revoke_share_token(collection.id, user1.id)
    assert revoke_success, "Failed to revoke share token"
    
    # Test that collection is now private
    private_collection = collection_service.get_collection(collection.id)
    assert private_collection.is_public == False, "Collection not made private after token revocation"
    assert private_collection.share_token is None, "Share token not removed after revocation"
    
    # Test that token no longer works
    revoked_collection = collection_service.get_collection_by_share_token(share_token)
    assert revoked_collection is None, "Revoked share token still works"
    
    print("[OK] Share token revocation successful")
    return True


def test_favorites_management():
    """Test collection favorites functionality"""
    print("\nTesting Favorites Management...")
    
    db = DatabaseService(":memory:")
    auth_service = AuthService(db)
    collection_service = CollectionService(db)
    
    user1, user2, ingredients, recipes = create_test_data(db, auth_service)
    
    # Create multiple collections
    collection1 = collection_service.create_collection("Collection 1", user1.id)
    collection2 = collection_service.create_collection("Collection 2", user1.id)
    collection3 = collection_service.create_collection("Collection 3", user1.id)
    
    # Test setting favorite
    success = collection_service.set_favorite_collection(collection2.id, user1.id, True)
    assert success, "Failed to set favorite collection"
    
    # Test getting favorite collection
    favorite = collection_service.get_favorite_collection(user1.id)
    assert favorite is not None, "Failed to get favorite collection"
    assert favorite.id == collection2.id, "Wrong collection marked as favorite"
    assert favorite.name == "Collection 2", "Favorite collection name incorrect"
    
    print("[OK] Favorite collection set and retrieved successfully")
    
    # Test that setting new favorite removes old one
    success2 = collection_service.set_favorite_collection(collection3.id, user1.id, True)
    assert success2, "Failed to set new favorite collection"
    
    new_favorite = collection_service.get_favorite_collection(user1.id)
    assert new_favorite.id == collection3.id, "New favorite not set correctly"
    
    # Check that old favorite is no longer favorite
    old_collection = collection_service.get_collection(collection2.id)
    assert old_collection.is_favorite == False, "Old favorite not removed"
    
    print("[OK] Favorite collection replacement working correctly")
    
    # Test unsetting favorite
    unset_success = collection_service.set_favorite_collection(collection3.id, user1.id, False)
    assert unset_success, "Failed to unset favorite collection"
    
    no_favorite = collection_service.get_favorite_collection(user1.id)
    assert no_favorite is None, "Favorite collection not properly unset"
    
    print("[OK] Favorite collection unset successfully")
    return True


def test_service_integration():
    """Test integration with database and other services"""
    print("\nTesting Service Integration...")
    
    db = DatabaseService(":memory:")
    auth_service = AuthService(db)
    collection_service = CollectionService(db)
    
    user1, user2, ingredients, recipes = create_test_data(db, auth_service)
    
    # Test factory function
    from services.collection_service import get_collection_service
    factory_service = get_collection_service()
    assert factory_service is not None, "Factory function failed"
    assert isinstance(factory_service, CollectionService), "Factory function returned wrong type"
    
    print("[OK] Factory function working correctly")
    
    # Test database transaction handling
    collection = collection_service.create_collection("Transaction Test", user1.id)
    assert collection is not None, "Failed to create collection for transaction test"
    
    # Add multiple recipes in sequence
    for recipe_id in recipes:
        success = collection_service.add_recipe_to_collection(recipe_id, collection.id)
        assert success, f"Failed to add recipe {recipe_id} in transaction"
    
    # Verify all recipes were added
    final_collection = collection_service.get_collection(collection.id)
    assert len(final_collection.recipe_ids) == len(recipes), "Not all recipes added in transaction"
    
    print("[OK] Database transactions working correctly")
    
    # Test error handling with invalid IDs
    invalid_collection = collection_service.get_collection(99999)
    assert invalid_collection is None, "Should return None for invalid collection ID"
    
    invalid_add = collection_service.add_recipe_to_collection(99999, collection.id)
    assert invalid_add == False, "Should fail gracefully with invalid recipe ID"
    
    print("[OK] Error handling working correctly")
    return True


if __name__ == "__main__":
    try:
        success1 = test_collection_crud_operations()
        success2 = test_recipe_collection_associations()
        success3 = test_shopping_list_generation()
        success4 = test_collection_sharing()
        success5 = test_favorites_management()
        success6 = test_service_integration()
        
        if all([success1, success2, success3, success4, success5, success6]):
            print("\n[SUCCESS] All collection service tests passed!")
            print("\nTask 11 - Recipe Collections System Features:")
            print("• [OK] Collection CRUD operations (create, read, update, delete)")
            print("• [OK] Recipe-collection associations (add/remove recipes)")
            print("• [OK] Shopping list generation with ingredient consolidation")
            print("• [OK] Collection sharing with secure tokens")
            print("• [OK] Public/private collection access control")
            print("• [OK] Favorites management system")
            print("• [OK] Database transaction handling")
            print("• [OK] Error handling and validation")
            print("• [OK] Service factory functions")
            print("• [OK] Integration with authentication service")
            print("• [OK] Shopping list categorization and organization")
            print("• [OK] Recipe ingredient consolidation across collections")
            sys.exit(0)
        else:
            print("\n[FAIL] Some collection service tests failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"[ERROR] Collection service test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)