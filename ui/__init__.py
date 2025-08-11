"""
UI components for Pans Cookbook application.

Contains Streamlit-based user interface components for recipe management,
validation forms, and user interactions.
"""

from .validation_forms import ValidationInterface
from .recipe_browser import RecipeBrowser, create_recipe_browser
from .recipe_details import RecipeDetailsInterface, create_recipe_details_interface
from .auth import AuthenticationInterface, create_auth_interface
from .collections import CollectionsInterface, create_collections_interface

__all__ = [
    'ValidationInterface',
    'RecipeBrowser',
    'create_recipe_browser',
    'RecipeDetailsInterface',
    'create_recipe_details_interface',
    'AuthenticationInterface',
    'create_auth_interface',
    'CollectionsInterface',
    'create_collections_interface'
]