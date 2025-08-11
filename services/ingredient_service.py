"""
Ingredient management service for Pans Cookbook application.

Provides comprehensive ingredient CRUD operations, duplicate detection,
merging functionality, and bulk categorization features.
Leverages Herbalism app ingredient loading patterns with recipe-specific enhancements.
"""

import re
import json
import logging
from typing import List, Optional, Dict, Set, Tuple, Any
from collections import defaultdict, Counter
from datetime import datetime

from models import Ingredient, NutritionData
from services.database_service import DatabaseService, get_database_service
from utils import get_logger

logger = get_logger(__name__)


class IngredientService:
    """
    Comprehensive ingredient management service.
    
    Handles CRUD operations, duplicate detection, merging, and bulk categorization
    with automatic recipe reference updates. Designed to maintain data integrity
    across all recipe-ingredient relationships.
    """
    
    def __init__(self, database_service: Optional[DatabaseService] = None):
        self.db = database_service or get_database_service()
        
        # Cache for performance
        self._ingredient_cache = {}
        self._cache_timestamp = None
        self._cache_ttl_seconds = 300  # 5 minutes
        
        # Common ingredient categories for auto-categorization
        self._category_keywords = self._load_category_keywords()
        
        # Similarity thresholds for duplicate detection
        self._similarity_thresholds = {
            'exact_match': 1.0,
            'high_confidence': 0.9,
            'medium_confidence': 0.7,
            'low_confidence': 0.5
        }
    
    # CRUD Operations
    
    def create_ingredient(self, name: str, category: str = "", **kwargs) -> Optional[Ingredient]:
        """
        Create a new ingredient with duplicate detection.
        
        Args:
            name: Ingredient name
            category: Ingredient category 
            **kwargs: Additional fields (common_substitutes, storage_tips, nutritional_data)
            
        Returns:
            Created Ingredient or None if creation failed
        """
        # Check for duplicates before creating
        duplicates = self.find_duplicate_ingredients(name)
        if duplicates:
            logger.warning(f"Potential duplicates found for '{name}': {[d.name for d in duplicates]}")
            
        # Auto-categorize if no category provided
        if not category:
            category = self.auto_categorize_ingredient(name)
        
        # Create ingredient via database service
        ingredient = self.db.create_ingredient(name, category, **kwargs)
        
        if ingredient:
            self._invalidate_cache()
            logger.info(f"Created ingredient: {name} (category: {category})")
        
        return ingredient
    
    def get_ingredient(self, ingredient_id: int) -> Optional[Ingredient]:
        """Get ingredient by ID with caching"""
        return self.db.get_ingredient_by_id(ingredient_id)
    
    def get_all_ingredients(self, use_cache: bool = True) -> List[Ingredient]:
        """Get all ingredients with optional caching"""
        if use_cache and self._is_cache_valid():
            return list(self._ingredient_cache.values())
        
        ingredients = self.db.get_all_ingredients()
        self._update_cache(ingredients)
        return ingredients
    
    def update_ingredient(self, ingredient_id: int, **updates) -> Optional[Ingredient]:
        """
        Update ingredient with validation.
        
        Args:
            ingredient_id: ID of ingredient to update
            **updates: Fields to update
            
        Returns:
            Updated Ingredient or None if update failed
        """
        try:
            with self.db.get_connection() as conn:
                # Get current ingredient
                current = self.db.get_ingredient_by_id(ingredient_id)
                if not current:
                    logger.error(f"Ingredient {ingredient_id} not found for update")
                    return None
                
                # Prepare update query
                update_fields = []
                update_values = []
                
                for field, value in updates.items():
                    if field in ['name', 'category', 'storage_tips']:
                        update_fields.append(f"{field} = ?")
                        update_values.append(value)
                    elif field == 'common_substitutes':
                        if isinstance(value, list):
                            value = ','.join(value)
                        update_fields.append("common_substitutes = ?")
                        update_values.append(value)
                    elif field == 'nutritional_data':
                        update_fields.append("nutritional_data = ?")
                        update_values.append(json.dumps(value if value else {}))
                
                if not update_fields:
                    logger.warning(f"No valid fields to update for ingredient {ingredient_id}")
                    return current
                
                update_values.append(ingredient_id)
                
                # Execute update
                cursor = conn.cursor()
                cursor.execute(f"""
                    UPDATE ingredients 
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                """, update_values)
                
                conn.commit()
                
                if cursor.rowcount == 0:
                    logger.error(f"Failed to update ingredient {ingredient_id}")
                    return None
                
                self._invalidate_cache()
                logger.info(f"Updated ingredient {ingredient_id}: {list(updates.keys())}")
                
                # Return updated ingredient
                return self.db.get_ingredient_by_id(ingredient_id)
                
        except Exception as e:
            logger.error(f"Error updating ingredient {ingredient_id}: {e}")
            return None
    
    def delete_ingredient(self, ingredient_id: int, force: bool = False) -> bool:
        """
        Delete ingredient with safety checks.
        
        Args:
            ingredient_id: ID of ingredient to delete
            force: If True, delete even if used in recipes
            
        Returns:
            True if successfully deleted
        """
        try:
            with self.db.get_connection() as conn:
                # Check if ingredient is used in recipes
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as usage_count 
                    FROM recipe_ingredients 
                    WHERE ingredient_id = ?
                """, (ingredient_id,))
                
                usage_count = cursor.fetchone()['usage_count']
                
                if usage_count > 0 and not force:
                    logger.warning(f"Cannot delete ingredient {ingredient_id}: used in {usage_count} recipes")
                    return False
                
                # Delete ingredient (CASCADE will handle recipe_ingredients)
                cursor.execute("DELETE FROM ingredients WHERE id = ?", (ingredient_id,))
                
                if cursor.rowcount == 0:
                    logger.error(f"Ingredient {ingredient_id} not found for deletion")
                    return False
                
                conn.commit()
                self._invalidate_cache()
                
                logger.info(f"Deleted ingredient {ingredient_id} (was used in {usage_count} recipes)")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting ingredient {ingredient_id}: {e}")
            return False
    
    # Duplicate Detection and Merging
    
    def find_duplicate_ingredients(self, name: str, threshold: float = 0.7) -> List[Ingredient]:
        """
        Find potential duplicate ingredients using similarity scoring.
        
        Args:
            name: Ingredient name to check
            threshold: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            List of potential duplicate ingredients
        """
        all_ingredients = self.get_all_ingredients()
        duplicates = []
        
        name_normalized = self._normalize_ingredient_name(name)
        
        for ingredient in all_ingredients:
            similarity = self._calculate_ingredient_similarity(name_normalized, ingredient.name)
            if similarity >= threshold and ingredient.name.lower() != name.lower():
                duplicates.append(ingredient)
        
        # Sort by similarity score (highest first)
        duplicates.sort(key=lambda ing: self._calculate_ingredient_similarity(name_normalized, ing.name), reverse=True)
        
        return duplicates
    
    def find_all_duplicates(self, threshold: float = 0.8) -> Dict[str, List[Ingredient]]:
        """
        Find all potential duplicates in the database.
        
        Args:
            threshold: Minimum similarity score
            
        Returns:
            Dict mapping ingredient names to lists of similar ingredients
        """
        all_ingredients = self.get_all_ingredients()
        duplicate_groups = defaultdict(list)
        processed = set()
        
        for i, ingredient1 in enumerate(all_ingredients):
            if ingredient1.id in processed:
                continue
                
            similar_ingredients = []
            name1_normalized = self._normalize_ingredient_name(ingredient1.name)
            
            for j, ingredient2 in enumerate(all_ingredients[i+1:], i+1):
                if ingredient2.id in processed:
                    continue
                    
                similarity = self._calculate_ingredient_similarity(name1_normalized, ingredient2.name)
                if similarity >= threshold:
                    similar_ingredients.append(ingredient2)
                    processed.add(ingredient2.id)
            
            if similar_ingredients:
                duplicate_groups[ingredient1.name] = [ingredient1] + similar_ingredients
                processed.add(ingredient1.id)
        
        return dict(duplicate_groups)
    
    def merge_ingredients(self, primary_id: int, duplicate_ids: List[int]) -> bool:
        """
        Merge duplicate ingredients into a primary ingredient.
        Updates all recipe references to point to the primary ingredient.
        
        Args:
            primary_id: ID of ingredient to keep
            duplicate_ids: IDs of ingredients to merge and delete
            
        Returns:
            True if merge was successful
        """
        try:
            with self.db.get_connection() as conn:
                # Verify primary ingredient exists
                primary = self.db.get_ingredient_by_id(primary_id)
                if not primary:
                    logger.error(f"Primary ingredient {primary_id} not found")
                    return False
                
                # Verify all duplicate ingredients exist
                duplicates = []
                for dup_id in duplicate_ids:
                    duplicate = self.db.get_ingredient_by_id(dup_id)
                    if duplicate:
                        duplicates.append(duplicate)
                    else:
                        logger.warning(f"Duplicate ingredient {dup_id} not found, skipping")
                
                if not duplicates:
                    logger.warning("No valid duplicate ingredients to merge")
                    return False
                
                cursor = conn.cursor()
                
                # Update recipe_ingredients references
                for duplicate in duplicates:
                    # Check for conflicts (recipes that use both primary and duplicate)
                    cursor.execute("""
                        SELECT recipe_id FROM recipe_ingredients 
                        WHERE ingredient_id = ? AND recipe_id IN (
                            SELECT recipe_id FROM recipe_ingredients 
                            WHERE ingredient_id = ?
                        )
                    """, (duplicate.id, primary_id))
                    
                    conflicted_recipes = cursor.fetchall()
                    
                    if conflicted_recipes:
                        logger.warning(f"Found {len(conflicted_recipes)} recipes using both primary and duplicate ingredient {duplicate.name}")
                        # For now, just delete the duplicate entries (user will need to manually resolve)
                        cursor.execute("""
                            DELETE FROM recipe_ingredients 
                            WHERE ingredient_id = ? AND recipe_id IN (
                                SELECT recipe_id FROM recipe_ingredients 
                                WHERE ingredient_id = ?
                            )
                        """, (duplicate.id, primary_id))
                    
                    # Update remaining references
                    cursor.execute("""
                        UPDATE recipe_ingredients 
                        SET ingredient_id = ? 
                        WHERE ingredient_id = ?
                    """, (primary_id, duplicate.id))
                
                # Merge additional data from duplicates into primary
                self._merge_ingredient_data(primary, duplicates, conn)
                
                # Delete duplicate ingredients
                for duplicate in duplicates:
                    cursor.execute("DELETE FROM ingredients WHERE id = ?", (duplicate.id,))
                
                conn.commit()
                self._invalidate_cache()
                
                logger.info(f"Successfully merged {len(duplicates)} ingredients into {primary.name}")
                return True
                
        except Exception as e:
            logger.error(f"Error merging ingredients: {e}")
            return False
    
    def _merge_ingredient_data(self, primary: Ingredient, duplicates: List[Ingredient], conn):
        """Merge data from duplicate ingredients into primary ingredient"""
        try:
            # Combine common substitutes
            all_substitutes = set(primary.common_substitutes)
            for duplicate in duplicates:
                all_substitutes.update(duplicate.common_substitutes)
            
            # Combine storage tips (if primary doesn't have any)
            storage_tips = primary.storage_tips
            if not storage_tips:
                for duplicate in duplicates:
                    if duplicate.storage_tips:
                        storage_tips = duplicate.storage_tips
                        break
            
            # Update primary ingredient with merged data
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE ingredients 
                SET common_substitutes = ?, storage_tips = ?
                WHERE id = ?
            """, (
                ','.join(all_substitutes) if all_substitutes else '',
                storage_tips,
                primary.id
            ))
            
        except Exception as e:
            logger.error(f"Error merging ingredient data: {e}")
    
    # Bulk Operations and Categorization
    
    def bulk_categorize_ingredients(self, category_mappings: Dict[str, str] = None) -> Dict[str, int]:
        """
        Bulk categorize ingredients using automatic categorization or provided mappings.
        
        Args:
            category_mappings: Optional dict of ingredient_name -> category
            
        Returns:
            Dict with categorization results: {'updated': count, 'skipped': count, 'errors': count}
        """
        results = {'updated': 0, 'skipped': 0, 'errors': 0}
        
        ingredients = self.get_all_ingredients()
        
        for ingredient in ingredients:
            try:
                # Skip if already has category
                if ingredient.category and ingredient.category.strip():
                    results['skipped'] += 1
                    continue
                
                # Determine new category
                new_category = ''
                if category_mappings and ingredient.name in category_mappings:
                    new_category = category_mappings[ingredient.name]
                else:
                    new_category = self.auto_categorize_ingredient(ingredient.name)
                
                if new_category:
                    updated = self.update_ingredient(ingredient.id, category=new_category)
                    if updated:
                        results['updated'] += 1
                    else:
                        results['errors'] += 1
                else:
                    results['skipped'] += 1
                    
            except Exception as e:
                logger.error(f"Error categorizing ingredient {ingredient.name}: {e}")
                results['errors'] += 1
        
        logger.info(f"Bulk categorization completed: {results}")
        return results
    
    def auto_categorize_ingredient(self, name: str) -> str:
        """
        Automatically categorize ingredient based on name patterns.
        
        Args:
            name: Ingredient name
            
        Returns:
            Suggested category or empty string if no match
        """
        name_lower = name.lower()
        
        for category, keywords in self._category_keywords.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return category
        
        return ""
    
    def get_ingredient_stats(self) -> Dict[str, Any]:
        """Get comprehensive ingredient statistics"""
        ingredients = self.get_all_ingredients()
        
        # Category distribution
        category_counts = Counter(ing.category for ing in ingredients if ing.category)
        
        # Find uncategorized
        uncategorized = [ing for ing in ingredients if not ing.category or not ing.category.strip()]
        
        # Find potential duplicates
        duplicates = self.find_all_duplicates(threshold=0.8)
        
        return {
            'total_ingredients': len(ingredients),
            'categorized': len(ingredients) - len(uncategorized),
            'uncategorized': len(uncategorized),
            'categories': dict(category_counts),
            'potential_duplicate_groups': len(duplicates),
            'ingredients_in_duplicate_groups': sum(len(group) for group in duplicates.values())
        }
    
    # Utility Methods
    
    def _normalize_ingredient_name(self, name: str) -> str:
        """Normalize ingredient name for comparison"""
        # Remove common prefixes/suffixes and normalize
        normalized = name.lower().strip()
        
        # Remove articles and common cooking terms
        remove_words = ['fresh', 'dried', 'ground', 'whole', 'chopped', 'diced', 'minced']
        for word in remove_words:
            normalized = re.sub(rf'\b{word}\b', '', normalized)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _calculate_ingredient_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two ingredient names"""
        name1_normalized = self._normalize_ingredient_name(name1)
        name2_normalized = self._normalize_ingredient_name(name2)
        
        # Exact match
        if name1_normalized == name2_normalized:
            return 1.0
        
        # Check if one contains the other
        if name1_normalized in name2_normalized or name2_normalized in name1_normalized:
            return 0.9
        
        # Word overlap scoring
        words1 = set(name1_normalized.split())
        words2 = set(name2_normalized.split())
        
        if not words1 or not words2:
            return 0.0
        
        overlap = len(words1 & words2)
        total = len(words1 | words2)
        
        return overlap / total if total > 0 else 0.0
    
    def _load_category_keywords(self) -> Dict[str, List[str]]:
        """Load category keyword mappings for auto-categorization"""
        return {
            'protein': [
                'chicken', 'beef', 'pork', 'lamb', 'turkey', 'fish', 'salmon', 'tuna',
                'shrimp', 'egg', 'eggs', 'tofu', 'beans', 'lentils', 'quinoa'
            ],
            'vegetable': [
                'onion', 'garlic', 'carrot', 'celery', 'tomato', 'potato', 'pepper',
                'broccoli', 'spinach', 'lettuce', 'cucumber', 'mushroom', 'zucchini'
            ],
            'fruit': [
                'apple', 'banana', 'orange', 'lemon', 'lime', 'berry', 'strawberry',
                'blueberry', 'grape', 'cherry', 'peach', 'pear', 'avocado'
            ],
            'dairy': [
                'milk', 'butter', 'cheese', 'cream', 'yogurt', 'sour cream',
                'cottage cheese', 'ricotta', 'mozzarella', 'cheddar', 'parmesan'
            ],
            'grain': [
                'flour', 'rice', 'pasta', 'bread', 'oats', 'barley', 'wheat',
                'quinoa', 'couscous', 'bulgur', 'cornmeal', 'semolina'
            ],
            'seasoning': [
                'salt', 'pepper', 'garlic powder', 'onion powder', 'paprika',
                'cumin', 'oregano', 'basil', 'thyme', 'rosemary', 'sage', 'parsley'
            ],
            'oil': [
                'oil', 'olive oil', 'vegetable oil', 'coconut oil', 'canola oil',
                'sesame oil', 'avocado oil', 'sunflower oil'
            ],
            'sweetener': [
                'sugar', 'honey', 'maple syrup', 'brown sugar', 'powdered sugar',
                'corn syrup', 'agave', 'stevia', 'molasses'
            ],
            'condiment': [
                'ketchup', 'mustard', 'mayonnaise', 'soy sauce', 'vinegar',
                'hot sauce', 'worcestershire', 'bbq sauce', 'ranch'
            ]
        }
    
    def _is_cache_valid(self) -> bool:
        """Check if ingredient cache is still valid"""
        if not self._cache_timestamp or not self._ingredient_cache:
            return False
        
        cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
        return cache_age < self._cache_ttl_seconds
    
    def _update_cache(self, ingredients: List[Ingredient]):
        """Update ingredient cache"""
        self._ingredient_cache = {ing.id: ing for ing in ingredients}
        self._cache_timestamp = datetime.now()
    
    def _invalidate_cache(self):
        """Invalidate ingredient cache"""
        self._ingredient_cache.clear()
        self._cache_timestamp = None


def get_ingredient_service(database_service: Optional[DatabaseService] = None) -> IngredientService:
    """Get singleton ingredient service instance"""
    global _ingredient_service
    if '_ingredient_service' not in globals():
        globals()['_ingredient_service'] = IngredientService(database_service)
    return globals()['_ingredient_service']