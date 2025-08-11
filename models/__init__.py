"""
Data models for Pans Cookbook application.

This module contains all data model classes including Recipe, Ingredient, User, and Collection.
Models are designed to map directly to SQLite database schema with proper relationships.
"""

from .recipe_models import Recipe, Ingredient, RecipeIngredient, NutritionData
from .user_models import User, UserPreferences, Collection, UserSession, ShoppingList, ShoppingListItem
from .scraped_models import ScrapedRecipe, ParsedRecipe, ValidationResult, ScrapingResult

__all__ = [
    'Recipe',
    'Ingredient', 
    'RecipeIngredient',
    'NutritionData',
    'User',
    'UserPreferences', 
    'Collection',
    'UserSession',
    'ShoppingList',
    'ShoppingListItem',
    'ScrapedRecipe',
    'ParsedRecipe',
    'ValidationResult',
    'ScrapingResult'
]