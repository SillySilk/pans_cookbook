"""
Advanced search and filtering service for Pans Cookbook application.

Provides comprehensive recipe search functionality with time range filtering,
cuisine type filtering, dietary restriction filtering with inclusive logic,
and fuzzy search capabilities. Leverages Herbalism app filtering patterns.
"""

import re
import logging
from typing import List, Optional, Dict, Any, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

from models import Recipe, Ingredient, RecipeIngredient
from services.database_service import DatabaseService, get_database_service
from utils import get_logger

logger = get_logger(__name__)


class SortOrder(Enum):
    """Sort order options for search results"""
    RELEVANCE = "relevance"
    TITLE_ASC = "title_asc"
    TITLE_DESC = "title_desc"
    PREP_TIME_ASC = "prep_time_asc"
    PREP_TIME_DESC = "prep_time_desc"
    TOTAL_TIME_ASC = "total_time_asc"
    TOTAL_TIME_DESC = "total_time_desc"
    CREATED_ASC = "created_asc"
    CREATED_DESC = "created_desc"
    RATING_DESC = "rating_desc"


class DifficultyLevel(Enum):
    """Recipe difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium" 
    HARD = "hard"


@dataclass
class TimeRange:
    """Time range for filtering recipes"""
    min_minutes: Optional[int] = None
    max_minutes: Optional[int] = None
    
    def contains(self, minutes: int) -> bool:
        """Check if a time value falls within this range"""
        if self.min_minutes is not None and minutes < self.min_minutes:
            return False
        if self.max_minutes is not None and minutes > self.max_minutes:
            return False
        return True


@dataclass
class SearchFilters:
    """Comprehensive search filters for recipes"""
    
    # Text search
    query: Optional[str] = None
    search_in_ingredients: bool = True
    search_in_instructions: bool = True
    
    # Time-based filters
    prep_time_range: Optional[TimeRange] = None
    cook_time_range: Optional[TimeRange] = None
    total_time_range: Optional[TimeRange] = None
    
    # Category filters
    cuisine_types: Optional[List[str]] = None
    meal_categories: Optional[List[str]] = None
    difficulty_levels: Optional[List[DifficultyLevel]] = None
    
    # Dietary restrictions (inclusive logic)
    dietary_tags: Optional[List[str]] = None
    include_dietary_supersets: bool = True  # vegan shows in vegetarian
    
    # Ingredient-based filters
    required_ingredients: Optional[List[str]] = None  # Must have ALL
    optional_ingredients: Optional[List[str]] = None  # Can have ANY
    excluded_ingredients: Optional[List[str]] = None  # Must NOT have
    
    # Serving size filters
    min_servings: Optional[int] = None
    max_servings: Optional[int] = None
    
    # Rating and popularity
    min_rating: Optional[float] = None
    only_favorites: bool = False
    
    # Date filters
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    
    # Collection filters
    collection_ids: Optional[List[int]] = None
    
    def has_filters(self) -> bool:
        """Check if any filters are applied"""
        return any([
            self.query,
            self.prep_time_range,
            self.cook_time_range,
            self.total_time_range,
            self.cuisine_types,
            self.meal_categories,
            self.difficulty_levels,
            self.dietary_tags,
            self.required_ingredients,
            self.optional_ingredients,
            self.excluded_ingredients,
            self.min_servings,
            self.max_servings,
            self.min_rating,
            self.only_favorites,
            self.created_after,
            self.created_before,
            self.collection_ids
        ])


@dataclass 
class SearchResult:
    """Single search result with relevance scoring"""
    recipe: Recipe
    relevance_score: float = 0.0
    matched_terms: List[str] = None
    missing_ingredients: List[str] = None
    
    def __post_init__(self):
        if self.matched_terms is None:
            self.matched_terms = []
        if self.missing_ingredients is None:
            self.missing_ingredients = []


@dataclass
class SearchResults:
    """Complete search results with metadata"""
    results: List[SearchResult]
    total_count: int
    filtered_count: int
    execution_time_ms: float
    applied_filters: SearchFilters
    
    @property
    def has_results(self) -> bool:
        return len(self.results) > 0


class SearchService:
    """
    Advanced recipe search and filtering service.
    
    Provides fuzzy text search, comprehensive filtering, and intelligent
    result ranking with support for complex dietary and ingredient logic.
    """
    
    def __init__(self, database_service: Optional[DatabaseService] = None):
        self.db = database_service or get_database_service()
        
        # Common dietary tag hierarchies (for inclusive filtering)
        self.dietary_hierarchies = {
            'vegan': ['vegetarian', 'plant-based'],
            'vegetarian': ['plant-based'],
            'gluten-free': ['wheat-free'],
            'dairy-free': ['lactose-free'],
            'keto': ['low-carb'],
            'paleo': ['grain-free', 'dairy-free']
        }
        
        # Common time range presets
        self.time_presets = {
            'quick': TimeRange(max_minutes=30),
            'moderate': TimeRange(min_minutes=30, max_minutes=60),
            'long': TimeRange(min_minutes=60),
            'weeknight': TimeRange(max_minutes=45),
            'weekend': TimeRange(min_minutes=60)
        }
    
    def search_recipes(self, filters: SearchFilters, 
                      sort_by: SortOrder = SortOrder.RELEVANCE,
                      limit: int = 50, offset: int = 0,
                      user_id: Optional[int] = None) -> SearchResults:
        """
        Execute comprehensive recipe search with filtering.
        
        Args:
            filters: Search filters to apply
            sort_by: Sort order for results
            limit: Maximum number of results
            offset: Pagination offset
            user_id: User ID for personalized results
            
        Returns:
            SearchResults with recipes and metadata
        """
        start_time = datetime.now()
        
        try:
            # Get base recipe set
            all_recipes = self._get_base_recipes(user_id)
            total_count = len(all_recipes)
            
            # Apply filters
            filtered_recipes = self._apply_filters(all_recipes, filters, user_id)
            filtered_count = len(filtered_recipes)
            
            # Calculate relevance scores for text search
            if filters.query:
                scored_results = self._calculate_relevance_scores(filtered_recipes, filters.query)
            else:
                scored_results = [SearchResult(recipe=r) for r in filtered_recipes]
            
            # Sort results
            sorted_results = self._sort_results(scored_results, sort_by)
            
            # Apply pagination
            paginated_results = sorted_results[offset:offset + limit]
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            logger.info(f"Search completed: {len(paginated_results)}/{filtered_count} results in {execution_time:.2f}ms")
            
            return SearchResults(
                results=paginated_results,
                total_count=total_count,
                filtered_count=filtered_count,
                execution_time_ms=execution_time,
                applied_filters=filters
            )
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return SearchResults(
                results=[],
                total_count=0,
                filtered_count=0,
                execution_time_ms=0.0,
                applied_filters=filters
            )
    
    def get_filter_suggestions(self, user_id: Optional[int] = None) -> Dict[str, List[str]]:
        """
        Get available filter options based on current recipe database.
        
        Args:
            user_id: User ID for personalized suggestions
            
        Returns:
            Dictionary with available filter options
        """
        try:
            recipes = self._get_base_recipes(user_id)
            
            # Extract unique values for filters
            cuisines = set()
            categories = set()
            dietary_tags = set()
            difficulties = set()
            
            for recipe in recipes:
                if recipe.cuisine_type:
                    cuisines.add(recipe.cuisine_type)
                if recipe.meal_category:
                    categories.add(recipe.meal_category)
                if recipe.dietary_tags:
                    dietary_tags.update(recipe.dietary_tags)
                if recipe.difficulty_level:
                    difficulties.add(recipe.difficulty_level)
            
            return {
                'cuisines': sorted(list(cuisines)),
                'categories': sorted(list(categories)),
                'dietary_tags': sorted(list(dietary_tags)),
                'difficulties': sorted(list(difficulties)),
                'time_presets': list(self.time_presets.keys())
            }
            
        except Exception as e:
            logger.error(f"Failed to get filter suggestions: {e}")
            return {}
    
    def get_time_preset(self, preset_name: str) -> Optional[TimeRange]:
        """Get predefined time range by name"""
        return self.time_presets.get(preset_name.lower())
    
    def suggest_similar_recipes(self, recipe: Recipe, limit: int = 5) -> List[Recipe]:
        """
        Find recipes similar to the given recipe.
        
        Args:
            recipe: Recipe to find similar recipes for
            limit: Maximum number of suggestions
            
        Returns:
            List of similar recipes
        """
        try:
            filters = SearchFilters(
                cuisine_types=[recipe.cuisine_type] if recipe.cuisine_type else None,
                meal_categories=[recipe.meal_category] if recipe.meal_category else None,
                dietary_tags=recipe.dietary_tags if recipe.dietary_tags else None,
                difficulty_levels=[DifficultyLevel(recipe.difficulty_level)] if recipe.difficulty_level else None
            )
            
            results = self.search_recipes(filters, limit=limit + 1)  # +1 to exclude original
            
            # Remove the original recipe from results
            similar_recipes = [
                r.recipe for r in results.results 
                if r.recipe.id != recipe.id
            ][:limit]
            
            return similar_recipes
            
        except Exception as e:
            logger.error(f"Failed to find similar recipes: {e}")
            return []
    
    def _get_base_recipes(self, user_id: Optional[int] = None) -> List[Recipe]:
        """Get base set of recipes for searching"""
        if user_id:
            # Get user's accessible recipes (including public ones)
            return self.db.get_recipes_for_user(user_id)
        else:
            # Get all public recipes
            return self.db.get_all_recipes()
    
    def _apply_filters(self, recipes: List[Recipe], filters: SearchFilters, user_id: Optional[int] = None) -> List[Recipe]:
        """Apply all filters to recipe list"""
        filtered = recipes
        
        # Time-based filters
        if filters.prep_time_range:
            filtered = [r for r in filtered if filters.prep_time_range.contains(r.prep_time_minutes)]
        
        if filters.cook_time_range:
            filtered = [r for r in filtered if filters.cook_time_range.contains(r.cook_time_minutes)]
            
        if filters.total_time_range:
            total_time = lambda r: r.prep_time_minutes + r.cook_time_minutes
            filtered = [r for r in filtered if filters.total_time_range.contains(total_time(r))]
        
        # Category filters
        if filters.cuisine_types:
            filtered = [r for r in filtered if r.cuisine_type in filters.cuisine_types]
            
        if filters.meal_categories:
            filtered = [r for r in filtered if r.meal_category in filters.meal_categories]
            
        if filters.difficulty_levels:
            difficulty_strings = [d.value for d in filters.difficulty_levels]
            filtered = [r for r in filtered if r.difficulty_level in difficulty_strings]
        
        # Dietary restrictions with inclusive logic
        if filters.dietary_tags:
            filtered = self._apply_dietary_filters(filtered, filters.dietary_tags, filters.include_dietary_supersets)
        
        # Ingredient filters
        if filters.required_ingredients:
            filtered = self._apply_ingredient_filters(filtered, filters.required_ingredients, 'required')
        
        if filters.optional_ingredients:
            filtered = self._apply_ingredient_filters(filtered, filters.optional_ingredients, 'optional')
            
        if filters.excluded_ingredients:
            filtered = self._apply_ingredient_filters(filtered, filters.excluded_ingredients, 'excluded')
        
        # Serving size filters
        if filters.min_servings:
            filtered = [r for r in filtered if r.servings >= filters.min_servings]
            
        if filters.max_servings:
            filtered = [r for r in filtered if r.servings <= filters.max_servings]
        
        # Rating filter
        if filters.min_rating:
            filtered = [r for r in filtered if (r.rating or 0) >= filters.min_rating]
        
        # Favorites filter
        if filters.only_favorites and user_id:
            favorite_recipe_ids = self.db.get_user_favorite_recipe_ids(user_id)
            filtered = [r for r in filtered if r.id in favorite_recipe_ids]
        
        # Date filters
        if filters.created_after:
            filtered = [r for r in filtered if r.created_at >= filters.created_after]
            
        if filters.created_before:
            filtered = [r for r in filtered if r.created_at <= filters.created_before]
        
        # Collection filters
        if filters.collection_ids:
            collection_recipe_ids = set()
            for collection_id in filters.collection_ids:
                collection_recipe_ids.update(self.db.get_collection_recipe_ids(collection_id))
            filtered = [r for r in filtered if r.id in collection_recipe_ids]
        
        return filtered
    
    def _apply_dietary_filters(self, recipes: List[Recipe], dietary_tags: List[str], inclusive: bool) -> List[Recipe]:
        """Apply dietary restriction filters with inclusive logic"""
        if not dietary_tags:
            return recipes
        
        def recipe_matches_dietary_requirements(recipe: Recipe) -> bool:
            if not recipe.dietary_tags:
                return False
            
            recipe_tags = set(recipe.dietary_tags)
            required_tags = set(dietary_tags)
            
            # Direct match
            if required_tags.issubset(recipe_tags):
                return True
            
            # Inclusive logic: check if recipe satisfies dietary requirements
            if inclusive:
                for required_tag in required_tags:
                    # Check if recipe has a tag that implies the required tag
                    for recipe_tag in recipe_tags:
                        if recipe_tag in self.dietary_hierarchies:
                            implied_tags = self.dietary_hierarchies[recipe_tag]
                            if required_tag in implied_tags:
                                continue  # This requirement is satisfied
                    else:
                        # Required tag not satisfied by any recipe tag
                        return False
                return True
            
            return False
        
        return [r for r in recipes if recipe_matches_dietary_requirements(r)]
    
    def _apply_ingredient_filters(self, recipes: List[Recipe], ingredients: List[str], filter_type: str) -> List[Recipe]:
        """Apply ingredient-based filters"""
        if not ingredients:
            return recipes
        
        def get_recipe_ingredients(recipe: Recipe) -> Set[str]:
            """Get set of ingredient names for a recipe"""
            recipe_ingredients = self.db.get_recipe_ingredients(recipe.id)
            ingredient_ids = [ri.ingredient_id for ri in recipe_ingredients]
            ingredient_names = set()
            
            for ingredient_id in ingredient_ids:
                ingredient = self.db.get_ingredient_by_id(ingredient_id)
                if ingredient:
                    ingredient_names.add(ingredient.name.lower())
            
            return ingredient_names
        
        filtered = []
        ingredient_set = set(ing.lower() for ing in ingredients)
        
        for recipe in recipes:
            recipe_ingredients = get_recipe_ingredients(recipe)
            
            if filter_type == 'required':
                # Must have ALL required ingredients
                if ingredient_set.issubset(recipe_ingredients):
                    filtered.append(recipe)
                    
            elif filter_type == 'optional':
                # Must have at least ONE optional ingredient
                if ingredient_set.intersection(recipe_ingredients):
                    filtered.append(recipe)
                    
            elif filter_type == 'excluded':
                # Must NOT have any excluded ingredients
                if not ingredient_set.intersection(recipe_ingredients):
                    filtered.append(recipe)
        
        return filtered
    
    def _calculate_relevance_scores(self, recipes: List[Recipe], query: str) -> List[SearchResult]:
        """Calculate relevance scores for text search"""
        results = []
        query_terms = self._normalize_query(query)
        
        for recipe in recipes:
            score = 0.0
            matched_terms = []
            
            # Score against title (highest weight)
            title_score, title_matches = self._score_text_match(recipe.title, query_terms, weight=3.0)
            score += title_score
            matched_terms.extend(title_matches)
            
            # Score against description
            if recipe.description:
                desc_score, desc_matches = self._score_text_match(recipe.description, query_terms, weight=2.0)
                score += desc_score
                matched_terms.extend(desc_matches)
            
            # Score against ingredients
            recipe_ingredients = self.db.get_recipe_ingredients(recipe.id)
            for recipe_ingredient in recipe_ingredients:
                ingredient = self.db.get_ingredient_by_id(recipe_ingredient.ingredient_id)
                if ingredient:
                    ing_score, ing_matches = self._score_text_match(ingredient.name, query_terms, weight=2.5)
                    score += ing_score
                    matched_terms.extend(ing_matches)
            
            # Score against instructions
            if recipe.instructions:
                inst_score, inst_matches = self._score_text_match(recipe.instructions, query_terms, weight=1.0)
                score += inst_score
                matched_terms.extend(inst_matches)
            
            # Boost score for exact phrase matches
            if query.lower() in recipe.title.lower():
                score *= 1.5
            
            results.append(SearchResult(
                recipe=recipe,
                relevance_score=score,
                matched_terms=list(set(matched_terms))
            ))
        
        return results
    
    def _normalize_query(self, query: str) -> List[str]:
        """Normalize search query into terms"""
        # Remove special characters and split on whitespace
        normalized = re.sub(r'[^\w\s]', ' ', query.lower())
        terms = [term.strip() for term in normalized.split() if len(term.strip()) > 2]
        return terms
    
    def _score_text_match(self, text: str, query_terms: List[str], weight: float = 1.0) -> Tuple[float, List[str]]:
        """Score text match against query terms"""
        if not text or not query_terms:
            return 0.0, []
        
        text_lower = text.lower()
        score = 0.0
        matched_terms = []
        
        for term in query_terms:
            if term in text_lower:
                # Exact match
                score += weight
                matched_terms.append(term)
            elif any(term in word for word in text_lower.split()):
                # Partial match
                score += weight * 0.5
                matched_terms.append(term)
        
        return score, matched_terms
    
    def _sort_results(self, results: List[SearchResult], sort_by: SortOrder) -> List[SearchResult]:
        """Sort search results by specified order"""
        if sort_by == SortOrder.RELEVANCE:
            return sorted(results, key=lambda r: r.relevance_score, reverse=True)
        elif sort_by == SortOrder.TITLE_ASC:
            return sorted(results, key=lambda r: r.recipe.title.lower())
        elif sort_by == SortOrder.TITLE_DESC:
            return sorted(results, key=lambda r: r.recipe.title.lower(), reverse=True)
        elif sort_by == SortOrder.PREP_TIME_ASC:
            return sorted(results, key=lambda r: r.recipe.prep_time_minutes)
        elif sort_by == SortOrder.PREP_TIME_DESC:
            return sorted(results, key=lambda r: r.recipe.prep_time_minutes, reverse=True)
        elif sort_by == SortOrder.TOTAL_TIME_ASC:
            return sorted(results, key=lambda r: r.recipe.prep_time_minutes + r.recipe.cook_time_minutes)
        elif sort_by == SortOrder.TOTAL_TIME_DESC:
            return sorted(results, key=lambda r: r.recipe.prep_time_minutes + r.recipe.cook_time_minutes, reverse=True)
        elif sort_by == SortOrder.CREATED_ASC:
            return sorted(results, key=lambda r: r.recipe.created_at or datetime.min)
        elif sort_by == SortOrder.CREATED_DESC:
            return sorted(results, key=lambda r: r.recipe.created_at or datetime.min, reverse=True)
        elif sort_by == SortOrder.RATING_DESC:
            return sorted(results, key=lambda r: r.recipe.rating or 0, reverse=True)
        else:
            return results


# Service factory function
def get_search_service(database_service: Optional[DatabaseService] = None) -> SearchService:
    """Factory function to get search service instance"""
    return SearchService(database_service)