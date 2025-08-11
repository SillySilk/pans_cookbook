"""
Services package for Pans Cookbook application.

Contains all business logic services including database operations, scraping,
authentication, and optional AI integrations.
"""

from .database_service import DatabaseService, get_database_service
from .auth_service import AuthService
from .scraping_service import ScrapingService, get_scraping_service
from .parsing_service import ParsingService, get_parsing_service
from .ingredient_service import IngredientService, get_ingredient_service
from .collection_service import CollectionService, get_collection_service
from .ai_service import AIService, get_ai_service, is_ai_available
from .search_service import SearchService, get_search_service, SearchFilters, TimeRange, SortOrder

__all__ = [
    'DatabaseService',
    'get_database_service',
    'AuthService',
    'ScrapingService',
    'get_scraping_service',
    'ParsingService',
    'get_parsing_service',
    'IngredientService',
    'get_ingredient_service',
    'CollectionService',
    'get_collection_service',
    'AIService',
    'get_ai_service',
    'is_ai_available',
    'SearchService',
    'get_search_service',
    'SearchFilters',
    'TimeRange',
    'SortOrder'
]