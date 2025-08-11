"""
Collection service for Pans Cookbook application.

Handles all collection operations including CRUD operations, shopping list generation,
and collection sharing functionality. Integrates with existing database patterns
from the Herbalism app architecture.
"""

import json
import secrets
import logging
from typing import List, Optional, Dict, Set, Tuple
from datetime import datetime

from models import Collection, Recipe, ShoppingList, ShoppingListItem
from .database_service import DatabaseService, get_database_service

logger = logging.getLogger(__name__)


class CollectionService:
    """
    Service for managing recipe collections and generating shopping lists.
    Provides CRUD operations, sharing functionality, and shopping list generation.
    """
    
    def __init__(self, database_service: Optional[DatabaseService] = None):
        self.db = database_service or get_database_service()
    
    # Collection CRUD Operations
    
    def create_collection(self, name: str, user_id: int, description: str = "",
                         tags: List[str] = None, is_public: bool = False) -> Optional[Collection]:
        """Create a new recipe collection"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert collection
                cursor.execute("""
                    INSERT INTO collections (name, description, user_id, tags, is_public, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    name, description, user_id, 
                    ','.join(tags) if tags else '',
                    1 if is_public else 0,
                    datetime.now(), datetime.now()
                ))
                
                collection_id = cursor.lastrowid
                conn.commit()
                
                # Return the created collection
                return self.get_collection(collection_id)
                
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return None
    
    def get_collection(self, collection_id: int) -> Optional[Collection]:
        """Get collection by ID with recipe relationships"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get collection details
                cursor.execute("""
                    SELECT id, name, description, user_id, tags, is_public, is_favorite,
                           created_at, updated_at, share_token
                    FROM collections 
                    WHERE id = ?
                """, (collection_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Get associated recipe IDs
                cursor.execute("""
                    SELECT recipe_id FROM collection_recipes WHERE collection_id = ?
                """, (collection_id,))
                
                recipe_ids = {row[0] for row in cursor.fetchall()}
                
                # Create collection object
                tags = [tag.strip() for tag in row['tags'].split(',') if tag.strip()]
                
                return Collection(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    user_id=row['user_id'],
                    recipe_ids=recipe_ids,
                    tags=tags,
                    is_public=bool(row['is_public']),
                    is_favorite=bool(row['is_favorite']),
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    share_token=row['share_token']
                )
                
        except Exception as e:
            logger.error(f"Failed to get collection {collection_id}: {e}")
            return None
    
    def get_user_collections(self, user_id: int, include_public: bool = True) -> List[Collection]:
        """Get all collections for a user"""
        try:
            collections = []
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query
                if include_public:
                    cursor.execute("""
                        SELECT id, name, description, user_id, tags, is_public, is_favorite,
                               created_at, updated_at, share_token
                        FROM collections 
                        WHERE user_id = ? OR is_public = 1
                        ORDER BY is_favorite DESC, updated_at DESC
                    """, (user_id,))
                else:
                    cursor.execute("""
                        SELECT id, name, description, user_id, tags, is_public, is_favorite,
                               created_at, updated_at, share_token
                        FROM collections 
                        WHERE user_id = ?
                        ORDER BY is_favorite DESC, updated_at DESC
                    """, (user_id,))
                
                for row in cursor.fetchall():
                    # Get recipe IDs for this collection
                    cursor.execute("""
                        SELECT recipe_id FROM collection_recipes WHERE collection_id = ?
                    """, (row['id'],))
                    
                    recipe_ids = {r[0] for r in cursor.fetchall()}
                    tags = [tag.strip() for tag in row['tags'].split(',') if tag.strip()]
                    
                    collection = Collection(
                        id=row['id'],
                        name=row['name'],
                        description=row['description'],
                        user_id=row['user_id'],
                        recipe_ids=recipe_ids,
                        tags=tags,
                        is_public=bool(row['is_public']),
                        is_favorite=bool(row['is_favorite']),
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        share_token=row['share_token']
                    )
                    
                    collections.append(collection)
            
            return collections
            
        except Exception as e:
            logger.error(f"Failed to get user collections for user {user_id}: {e}")
            return []
    
    def update_collection(self, collection_id: int, name: str = None, description: str = None,
                         tags: List[str] = None, is_public: bool = None) -> bool:
        """Update collection details"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build update query dynamically
                updates = []
                params = []
                
                if name is not None:
                    updates.append("name = ?")
                    params.append(name)
                
                if description is not None:
                    updates.append("description = ?")
                    params.append(description)
                
                if tags is not None:
                    updates.append("tags = ?")
                    params.append(','.join(tags))
                
                if is_public is not None:
                    updates.append("is_public = ?")
                    params.append(1 if is_public else 0)
                
                if not updates:
                    return True  # No changes requested
                
                updates.append("updated_at = ?")
                params.append(datetime.now())
                params.append(collection_id)
                
                query = f"UPDATE collections SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to update collection {collection_id}: {e}")
            return False
    
    def delete_collection(self, collection_id: int, user_id: int) -> bool:
        """Delete a collection (only by owner)"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verify ownership
                cursor.execute("""
                    SELECT user_id FROM collections WHERE id = ?
                """, (collection_id,))
                
                row = cursor.fetchone()
                if not row or row[0] != user_id:
                    logger.warning(f"User {user_id} attempted to delete collection {collection_id} without permission")
                    return False
                
                # Delete collection (cascade will handle recipes)
                cursor.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_id}: {e}")
            return False
    
    # Recipe-Collection Associations
    
    def add_recipe_to_collection(self, recipe_id: int, collection_id: int) -> bool:
        """Add a recipe to a collection"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if recipe exists
                cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipe_id,))
                if not cursor.fetchone():
                    logger.warning(f"Recipe {recipe_id} does not exist")
                    return False
                
                # Check if collection exists
                cursor.execute("SELECT id FROM collections WHERE id = ?", (collection_id,))
                if not cursor.fetchone():
                    logger.warning(f"Collection {collection_id} does not exist")
                    return False
                
                # Insert association (ignore if already exists)
                cursor.execute("""
                    INSERT OR IGNORE INTO collection_recipes (collection_id, recipe_id, added_at)
                    VALUES (?, ?, ?)
                """, (collection_id, recipe_id, datetime.now()))
                
                # Update collection timestamp
                cursor.execute("""
                    UPDATE collections SET updated_at = ? WHERE id = ?
                """, (datetime.now(), collection_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to add recipe {recipe_id} to collection {collection_id}: {e}")
            return False
    
    def remove_recipe_from_collection(self, recipe_id: int, collection_id: int) -> bool:
        """Remove a recipe from a collection"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Remove association
                cursor.execute("""
                    DELETE FROM collection_recipes 
                    WHERE collection_id = ? AND recipe_id = ?
                """, (collection_id, recipe_id))
                
                # Update collection timestamp
                cursor.execute("""
                    UPDATE collections SET updated_at = ? WHERE id = ?
                """, (datetime.now(), collection_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to remove recipe {recipe_id} from collection {collection_id}: {e}")
            return False
    
    def get_collection_recipes(self, collection_id: int) -> List[Recipe]:
        """Get all recipes in a collection"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get recipes with collection association
                cursor.execute("""
                    SELECT r.id, r.name, r.description, r.instructions, r.prep_time_minutes,
                           r.cook_time_minutes, r.servings, r.difficulty_level, r.cuisine_type,
                           r.meal_category, r.dietary_tags, r.nutritional_info, r.created_by,
                           r.created_at, r.updated_at, r.source_url, r.is_public, r.rating, r.rating_count
                    FROM recipes r
                    JOIN collection_recipes cr ON r.id = cr.recipe_id
                    WHERE cr.collection_id = ?
                    ORDER BY cr.added_at DESC
                """, (collection_id,))
                
                recipes = []
                for row in cursor.fetchall():
                    # Get recipe ingredients
                    ingredients = self._get_recipe_ingredients(row['id'], cursor)
                    
                    # Parse dietary tags
                    dietary_tags = [tag.strip() for tag in row['dietary_tags'].split(',') if tag.strip()]
                    
                    # Parse nutritional info
                    nutritional_info = {}
                    try:
                        if row['nutritional_info']:
                            nutritional_info = json.loads(row['nutritional_info'])
                    except json.JSONDecodeError:
                        pass
                    
                    recipe = Recipe(
                        id=row['id'],
                        name=row['name'],
                        description=row['description'],
                        instructions=row['instructions'],
                        prep_time_minutes=row['prep_time_minutes'],
                        cook_time_minutes=row['cook_time_minutes'],
                        servings=row['servings'],
                        difficulty_level=row['difficulty_level'],
                        cuisine_type=row['cuisine_type'],
                        meal_category=row['meal_category'],
                        dietary_tags=dietary_tags,
                        nutritional_info=nutritional_info,
                        created_by=row['created_by'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        source_url=row['source_url'],
                        is_public=bool(row['is_public']),
                        rating=row['rating'],
                        rating_count=row['rating_count'],
                        ingredients=ingredients
                    )
                    
                    recipes.append(recipe)
                
                return recipes
                
        except Exception as e:
            logger.error(f"Failed to get recipes for collection {collection_id}: {e}")
            return []
    
    def _get_recipe_ingredients(self, recipe_id: int, cursor) -> List:
        """Helper method to get recipe ingredients"""
        cursor.execute("""
            SELECT i.id, i.name, i.category, ri.quantity, ri.unit, ri.preparation_note, ri.ingredient_order
            FROM ingredients i
            JOIN recipe_ingredients ri ON i.id = ri.ingredient_id
            WHERE ri.recipe_id = ?
            ORDER BY ri.ingredient_order
        """, (recipe_id,))
        
        from models import RecipeIngredient, Ingredient
        ingredients = []
        
        for ing_row in cursor.fetchall():
            ingredient = Ingredient(
                id=ing_row['id'],
                name=ing_row['name'],
                category=ing_row['category']
            )
            
            recipe_ingredient = RecipeIngredient(
                recipe_id=recipe_id,
                ingredient_id=ing_row['id'],
                quantity=ing_row['quantity'],
                unit=ing_row['unit'],
                preparation_note=ing_row['preparation_note'],
                ingredient_order=ing_row['ingredient_order']
            )
            
            # Store the ingredient object as an attribute for easier access
            recipe_ingredient.ingredient = ingredient
            
            ingredients.append(recipe_ingredient)
        
        return ingredients
    
    # Shopping List Generation
    
    def generate_shopping_list(self, collection_id: int) -> Optional[ShoppingList]:
        """Generate a consolidated shopping list from collection recipes"""
        try:
            collection = self.get_collection(collection_id)
            if not collection:
                return None
            
            recipes = self.get_collection_recipes(collection_id)
            if not recipes:
                return ShoppingList(
                    collection_id=collection_id,
                    collection_name=collection.name,
                    total_recipes=0
                )
            
            shopping_list = ShoppingList(
                collection_id=collection_id,
                collection_name=collection.name,
                total_recipes=len(recipes)
            )
            
            # Process each recipe's ingredients
            for recipe in recipes:
                for recipe_ingredient in recipe.ingredients:
                    shopping_list.add_ingredient(
                        ingredient_name=recipe_ingredient.ingredient.name,
                        quantity=recipe_ingredient.quantity,
                        unit=recipe_ingredient.unit,
                        recipe_name=recipe.name,
                        category=recipe_ingredient.ingredient.category
                    )
            
            return shopping_list
            
        except Exception as e:
            logger.error(f"Failed to generate shopping list for collection {collection_id}: {e}")
            return None
    
    # Collection Sharing
    
    def generate_share_token(self, collection_id: int, user_id: int) -> Optional[str]:
        """Generate a shareable token for a collection"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verify ownership
                cursor.execute("""
                    SELECT user_id FROM collections WHERE id = ?
                """, (collection_id,))
                
                row = cursor.fetchone()
                if not row or row[0] != user_id:
                    logger.warning(f"User {user_id} attempted to share collection {collection_id} without permission")
                    return None
                
                # Generate unique token
                share_token = secrets.token_urlsafe(32)
                
                # Update collection with share token and make public
                cursor.execute("""
                    UPDATE collections 
                    SET share_token = ?, is_public = 1, updated_at = ?
                    WHERE id = ?
                """, (share_token, datetime.now(), collection_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    return share_token
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate share token for collection {collection_id}: {e}")
            return None
    
    def get_collection_by_share_token(self, share_token: str) -> Optional[Collection]:
        """Get a collection by its share token"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id FROM collections WHERE share_token = ? AND is_public = 1
                """, (share_token,))
                
                row = cursor.fetchone()
                if row:
                    return self.get_collection(row[0])
                return None
                
        except Exception as e:
            logger.error(f"Failed to get collection by share token: {e}")
            return None
    
    def revoke_share_token(self, collection_id: int, user_id: int) -> bool:
        """Revoke sharing for a collection"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verify ownership
                cursor.execute("""
                    SELECT user_id FROM collections WHERE id = ?
                """, (collection_id,))
                
                row = cursor.fetchone()
                if not row or row[0] != user_id:
                    return False
                
                # Remove share token and make private
                cursor.execute("""
                    UPDATE collections 
                    SET share_token = NULL, is_public = 0, updated_at = ?
                    WHERE id = ?
                """, (datetime.now(), collection_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to revoke share token for collection {collection_id}: {e}")
            return False
    
    # Favorites Management
    
    def set_favorite_collection(self, collection_id: int, user_id: int, is_favorite: bool = True) -> bool:
        """Set/unset a collection as favorite for a user"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verify ownership or public access
                cursor.execute("""
                    SELECT user_id, is_public FROM collections WHERE id = ?
                """, (collection_id,))
                
                row = cursor.fetchone()
                if not row or (row[0] != user_id and not row[1]):
                    return False
                
                # Only allow one favorite collection per user
                if is_favorite:
                    # Remove existing favorite
                    cursor.execute("""
                        UPDATE collections SET is_favorite = 0 WHERE user_id = ? AND is_favorite = 1
                    """, (user_id,))
                
                # Update collection favorite status
                cursor.execute("""
                    UPDATE collections SET is_favorite = ?, updated_at = ? WHERE id = ?
                """, (1 if is_favorite else 0, datetime.now(), collection_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to set favorite collection {collection_id}: {e}")
            return False
    
    def get_favorite_collection(self, user_id: int) -> Optional[Collection]:
        """Get user's favorite collection"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id FROM collections WHERE user_id = ? AND is_favorite = 1
                """, (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return self.get_collection(row[0])
                return None
                
        except Exception as e:
            logger.error(f"Failed to get favorite collection for user {user_id}: {e}")
            return None


def get_collection_service() -> CollectionService:
    """Factory function to get collection service instance"""
    return CollectionService()