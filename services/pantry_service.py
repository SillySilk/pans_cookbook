"""
Pantry management service for Pans Cookbook application.

Manages user's ingredient inventory (pantry) and finds recipes that can be made
with available ingredients. Core functionality for "what can I make" feature.
"""

import logging
from typing import List, Optional, Dict, Set, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from models.recipe_models import Recipe, Ingredient, RecipeIngredient
from services.database_service import DatabaseService, get_database_service
from utils import get_logger

logger = get_logger(__name__)


@dataclass
class PantryItem:
    """Item in user's pantry with availability status"""
    ingredient_id: int
    ingredient_name: str
    category: str
    is_available: bool = True
    quantity_estimate: Optional[str] = None  # "plenty", "running low", "just enough"
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()


@dataclass
class RecipeMatch:
    """Recipe with ingredient match analysis"""
    recipe: Recipe
    available_ingredients: List[str]  # ingredients user has
    missing_ingredients: List[str]   # ingredients user needs
    match_percentage: float          # percentage of ingredients available
    can_make: bool                   # True if all required ingredients available
    difficulty_score: float          # How hard to make (missing key ingredients)
    
    @property
    def match_status(self) -> str:
        """Human readable match status"""
        if self.can_make:
            return "✅ Can make now"
        elif self.match_percentage >= 0.8:
            return "🟡 Almost ready"
        elif self.match_percentage >= 0.5:
            return "🟠 Missing some"
        else:
            return "❌ Need many ingredients"


class PantryService:
    """
    Service for managing user pantry and finding matching recipes.
    
    Core functionality:
    - Manage user's ingredient inventory
    - Find recipes that can be made with available ingredients
    - Smart ingredient suggestions and shopping lists
    """
    
    def __init__(self, database_service: Optional[DatabaseService] = None):
        self.db = database_service or get_database_service()
    
    def get_user_pantry(self, user_id: int) -> List[PantryItem]:
        """Get user's complete pantry inventory"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get user's pantry items with ingredient details
                cursor.execute("""
                    SELECT 
                        p.ingredient_id,
                        i.name,
                        i.category,
                        p.is_available,
                        p.quantity_estimate,
                        p.last_updated
                    FROM user_pantry p
                    JOIN ingredients i ON p.ingredient_id = i.id
                    WHERE p.user_id = ?
                    ORDER BY i.category, i.name
                """, (user_id,))
                
                rows = cursor.fetchall()
                pantry_items = []
                
                for row in rows:
                    pantry_items.append(PantryItem(
                        ingredient_id=row['ingredient_id'],
                        ingredient_name=row['name'],
                        category=row['category'],
                        is_available=bool(row['is_available']),
                        quantity_estimate=row['quantity_estimate'],
                        last_updated=datetime.fromisoformat(row['last_updated']) if row['last_updated'] else datetime.now()
                    ))
                
                return pantry_items
                
        except Exception as e:
            logger.error(f"Failed to get user pantry: {e}")
            return []
    
    def update_pantry_item(self, user_id: int, ingredient_id: int, is_available: bool,
                          quantity_estimate: Optional[str] = None) -> bool:
        """Update availability of pantry item"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if pantry item exists
                cursor.execute("""
                    SELECT user_id FROM user_pantry 
                    WHERE user_id = ? AND ingredient_id = ?
                """, (user_id, ingredient_id))
                
                if cursor.fetchone():
                    # Update existing item
                    cursor.execute("""
                        UPDATE user_pantry SET
                            is_available = ?,
                            quantity_estimate = ?,
                            last_updated = ?
                        WHERE user_id = ? AND ingredient_id = ?
                    """, (is_available, quantity_estimate, datetime.now(), user_id, ingredient_id))
                else:
                    # Create new pantry item
                    cursor.execute("""
                        INSERT INTO user_pantry (user_id, ingredient_id, is_available, quantity_estimate, last_updated)
                        VALUES (?, ?, ?, ?, ?)
                    """, (user_id, ingredient_id, is_available, quantity_estimate, datetime.now()))
                
                conn.commit()
                logger.info(f"Updated pantry item {ingredient_id} for user {user_id}: available={is_available}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update pantry item {ingredient_id} for user {user_id}: {e}")
            import traceback
            logger.error(f"Pantry update traceback: {traceback.format_exc()}")
            return False
    
    def add_common_ingredients_to_pantry(self, user_id: int, categories: List[str] = None) -> int:
        """Add common ingredients to user's pantry (for setup)"""
        try:
            # Common ingredients by category
            common_ingredients = {
                'spice': ['salt', 'pepper', 'garlic powder', 'onion powder', 'paprika'],
                'oil': ['olive oil', 'vegetable oil', 'butter'],
                'pantry': ['flour', 'sugar', 'baking powder', 'vanilla extract'],
                'dairy': ['milk', 'eggs', 'cheese'],
                'vegetable': ['onion', 'garlic'],
                'protein': ['chicken breast', 'ground beef']
            }
            
            if categories is None:
                categories = list(common_ingredients.keys())
            
            added_count = 0
            
            for category in categories:
                if category not in common_ingredients:
                    continue
                    
                for ingredient_name in common_ingredients[category]:
                    # Find or create ingredient
                    ingredient = self._find_or_create_ingredient(ingredient_name, category)
                    if ingredient:
                        # Add to pantry as available
                        if self.update_pantry_item(user_id, ingredient.id, True, "plenty"):
                            added_count += 1
            
            logger.info(f"Added {added_count} common ingredients to user {user_id}'s pantry")
            return added_count
            
        except Exception as e:
            logger.error(f"Failed to add common ingredients: {e}")
            return 0
    
    def find_makeable_recipes(self, user_id: int, strict_mode: bool = True,
                             include_partial_matches: bool = False) -> List[RecipeMatch]:
        """
        Find recipes that can be made with current pantry items.
        
        Args:
            user_id: User ID
            strict_mode: If True, require ALL ingredients. If False, allow missing 1-2 items
            include_partial_matches: Include recipes with <50% ingredient matches
        """
        try:
            # Get user's available ingredients
            pantry = self.get_user_pantry(user_id)
            available_ingredients = {
                item.ingredient_id for item in pantry if item.is_available
            }
            
            if not available_ingredients:
                logger.info(f"User {user_id} has no available ingredients")
                return []
            
            # Get all recipes with their ingredients
            recipes = self._get_recipes_with_ingredients(user_id)
            recipe_matches = []
            
            for recipe, recipe_ingredients in recipes:
                required_ingredient_ids = {ri.ingredient_id for ri in recipe_ingredients}
                
                # Calculate match
                available_in_recipe = available_ingredients.intersection(required_ingredient_ids)
                missing_in_recipe = required_ingredient_ids - available_ingredients
                
                if not required_ingredient_ids:  # Recipe with no ingredients
                    continue
                    
                match_percentage = len(available_in_recipe) / len(required_ingredient_ids)
                can_make = len(missing_in_recipe) == 0
                
                # Apply filtering based on mode
                if strict_mode and not can_make:
                    continue
                    
                if not include_partial_matches and match_percentage < 0.5:
                    continue
                
                # Calculate difficulty score (higher = more difficult)
                difficulty_score = self._calculate_difficulty_score(recipe_ingredients, missing_in_recipe)
                
                # Get ingredient names
                available_names = [self._get_ingredient_name(ing_id) for ing_id in available_in_recipe]
                missing_names = [self._get_ingredient_name(ing_id) for ing_id in missing_in_recipe]
                
                recipe_match = RecipeMatch(
                    recipe=recipe,
                    available_ingredients=available_names,
                    missing_ingredients=missing_names,
                    match_percentage=match_percentage,
                    can_make=can_make,
                    difficulty_score=difficulty_score
                )
                
                recipe_matches.append(recipe_match)
            
            # Sort by match percentage (desc) and difficulty (asc)
            recipe_matches.sort(key=lambda x: (-x.match_percentage, x.difficulty_score))
            
            logger.info(f"Found {len(recipe_matches)} recipe matches for user {user_id}")
            return recipe_matches
            
        except Exception as e:
            logger.error(f"Failed to find makeable recipes: {e}")
            return []
    
    def get_shopping_list(self, user_id: int, recipe_ids: List[int]) -> Dict[str, List[str]]:
        """Generate shopping list for selected recipes"""
        try:
            pantry = self.get_user_pantry(user_id)
            available_ingredients = {item.ingredient_id for item in pantry if item.is_available}
            
            shopping_list = {}
            
            for recipe_id in recipe_ids:
                recipe_ingredients = self._get_recipe_ingredients(recipe_id)
                
                for ri in recipe_ingredients:
                    if ri.ingredient_id not in available_ingredients:
                        ingredient_name = self._get_ingredient_name(ri.ingredient_id)
                        category = self._get_ingredient_category(ri.ingredient_id)
                        
                        if category not in shopping_list:
                            shopping_list[category] = []
                        
                        # Format with quantity
                        item_text = f"{ri.get_display_text()} {ingredient_name}"
                        if item_text not in shopping_list[category]:
                            shopping_list[category].append(item_text)
            
            return shopping_list
            
        except Exception as e:
            logger.error(f"Failed to generate shopping list: {e}")
            return {}
    
    def suggest_recipes_to_complete_pantry(self, user_id: int, max_missing: int = 2) -> List[RecipeMatch]:
        """Suggest recipes that need just a few more ingredients"""
        try:
            # Get partial matches with missing ingredients
            partial_matches = self.find_makeable_recipes(
                user_id, 
                strict_mode=False, 
                include_partial_matches=True
            )
            
            # Filter to recipes missing just a few ingredients
            suggestions = [
                match for match in partial_matches
                if len(match.missing_ingredients) <= max_missing and not match.can_make
            ]
            
            # Sort by fewest missing ingredients first
            suggestions.sort(key=lambda x: (len(x.missing_ingredients), -x.match_percentage))
            
            return suggestions[:10]  # Top 10 suggestions
            
        except Exception as e:
            logger.error(f"Failed to suggest completion recipes: {e}")
            return []
    
    def get_pantry_categories(self, user_id: int) -> Dict[str, List[PantryItem]]:
        """Get pantry items organized by category"""
        pantry = self.get_user_pantry(user_id)
        categories = {}
        
        for item in pantry:
            if item.category not in categories:
                categories[item.category] = []
            categories[item.category].append(item)
        
        # Sort categories and items within categories
        sorted_categories = {}
        for category in sorted(categories.keys()):
            sorted_categories[category] = sorted(categories[category], key=lambda x: x.ingredient_name)
        
        return sorted_categories
    
    # Helper methods
    
    def _get_recipes_with_ingredients(self, user_id: int) -> List[Tuple[Recipe, List[RecipeIngredient]]]:
        """Get all recipes with their ingredient lists"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all accessible recipes
                cursor.execute("""
                    SELECT * FROM recipes
                    WHERE is_public = 1 OR created_by = ?
                    ORDER BY name
                """, (user_id,))
                
                recipes = []
                for row in cursor.fetchall():
                    recipe = self.db._row_to_recipe(row)
                    
                    # Get recipe ingredients
                    recipe_ingredients = self._get_recipe_ingredients(recipe.id)
                    recipes.append((recipe, recipe_ingredients))
                
                return recipes
                
        except Exception as e:
            logger.error(f"Failed to get recipes with ingredients: {e}")
            return []
    
    def _get_recipe_ingredients(self, recipe_id: int) -> List[RecipeIngredient]:
        """Get ingredients for a recipe"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM recipe_ingredients
                    WHERE recipe_id = ?
                    ORDER BY ingredient_order
                """, (recipe_id,))
                
                ingredients = []
                for row in cursor.fetchall():
                    ingredients.append(self.db._row_to_recipe_ingredient(row))
                
                return ingredients
                
        except Exception as e:
            logger.error(f"Failed to get recipe ingredients: {e}")
            return []
    
    def _calculate_difficulty_score(self, recipe_ingredients: List[RecipeIngredient], 
                                  missing_ingredient_ids: Set[int]) -> float:
        """Calculate how difficult a recipe is based on missing ingredients"""
        if not missing_ingredient_ids:
            return 0.0
        
        # Base difficulty from number of missing ingredients
        base_score = len(missing_ingredient_ids)
        
        # Adjust based on ingredient types (proteins/oils more critical)
        critical_categories = ['protein', 'oil', 'dairy']
        critical_missing = 0
        
        for ingredient_id in missing_ingredient_ids:
            category = self._get_ingredient_category(ingredient_id)
            if category in critical_categories:
                critical_missing += 1
        
        # Higher score = more difficult
        return base_score + (critical_missing * 0.5)
    
    def _find_or_create_ingredient(self, name: str, category: str) -> Optional[Ingredient]:
        """Find existing ingredient or create new one"""
        try:
            # Search for existing ingredient
            ingredients = self.db.search_ingredients(name)
            exact_match = next((ing for ing in ingredients if ing.name.lower() == name.lower()), None)
            
            if exact_match:
                return exact_match
            
            # Create new ingredient
            new_ingredient = self.db.create_ingredient(name, category)
            if new_ingredient:
                return new_ingredient
            
            # If creation failed due to constraint, search again (race condition)
            ingredients = self.db.search_ingredients(name)
            exact_match = next((ing for ing in ingredients if ing.name.lower() == name.lower()), None)
            if exact_match:
                logger.debug(f"Ingredient {name} was created by another thread")
                return exact_match
            
            logger.warning(f"Failed to find or create ingredient: {name}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to find/create ingredient {name}: {e}")
            return None
    
    def _get_ingredient_name(self, ingredient_id: int) -> str:
        """Get ingredient name by ID"""
        ingredient = self.db.get_ingredient_by_id(ingredient_id)
        return ingredient.name if ingredient else f"Unknown({ingredient_id})"
    
    def _get_ingredient_category(self, ingredient_id: int) -> str:
        """Get ingredient category by ID"""
        ingredient = self.db.get_ingredient_by_id(ingredient_id)
        return ingredient.category if ingredient else "unknown"


# Global service instance
_pantry_service: Optional[PantryService] = None


def get_pantry_service(database_service: Optional[DatabaseService] = None) -> PantryService:
    """Get singleton pantry service instance"""
    global _pantry_service
    if _pantry_service is None:
        _pantry_service = PantryService(database_service)
    return _pantry_service