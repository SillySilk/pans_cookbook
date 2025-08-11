"""
User and collection models for the Pans Cookbook application.

Handles user accounts, preferences, API key storage, and recipe collections.
Designed for multi-user web deployment with secure credential management.
"""

from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional, Any
from datetime import datetime
import json


@dataclass 
class UserPreferences:
    """User preferences and settings"""
    preferred_units: str = "imperial"  # imperial, metric
    dietary_restrictions: List[str] = field(default_factory=list)
    preferred_cuisines: List[str] = field(default_factory=list)
    default_servings: int = 4
    hide_complex_recipes: bool = False
    max_cook_time_minutes: Optional[int] = None
    email_notifications: bool = True
    
    def to_json(self) -> str:
        """Serialize preferences for database storage"""
        return json.dumps({
            'preferred_units': self.preferred_units,
            'dietary_restrictions': self.dietary_restrictions,
            'preferred_cuisines': self.preferred_cuisines,
            'default_servings': self.default_servings,
            'hide_complex_recipes': self.hide_complex_recipes,
            'max_cook_time_minutes': self.max_cook_time_minutes,
            'email_notifications': self.email_notifications
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'UserPreferences':
        """Deserialize preferences from database"""
        try:
            data = json.loads(json_str)
            return cls(**data)
        except (json.JSONDecodeError, TypeError):
            return cls()  # Return defaults if parsing fails


@dataclass
class User:
    """
    User model for authentication and account management.
    Supports secure API key storage for optional AI features.
    """
    id: int
    email: str
    password_hash: str
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    is_active: bool = True
    is_verified: bool = False
    api_keys: Dict[str, str] = field(default_factory=dict)  # encrypted API keys by service
    preferences: UserPreferences = field(default_factory=UserPreferences)
    created_at: datetime = field(default_factory=datetime.now)
    last_login: datetime = field(default_factory=datetime.now)
    login_count: int = 0
    
    def get_display_name(self) -> str:
        """Get user's display name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.username:
            return self.username
        else:
            return self.email.split('@')[0]
    
    def has_api_key(self, service: str) -> bool:
        """Check if user has configured API key for a service"""
        return service in self.api_keys and self.api_keys[service]
    
    def get_ai_enabled_services(self) -> List[str]:
        """Get list of AI services user has configured"""
        return [service for service, key in self.api_keys.items() if key]


@dataclass
class Collection:
    """
    Recipe collection model for organizing favorite recipes and meal plans.
    Supports both private collections and shareable meal plans.
    """
    id: int
    name: str
    description: str
    user_id: int
    recipe_ids: Set[int] = field(default_factory=set)
    tags: List[str] = field(default_factory=list)  # meal-plan, favorites, etc.
    is_public: bool = False
    is_favorite: bool = False  # user's favorite collection
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    share_token: Optional[str] = None  # for sharing collections
    
    def __post_init__(self):
        """Ensure recipe_ids is a set"""
        if isinstance(self.recipe_ids, list):
            self.recipe_ids = set(self.recipe_ids)
        if isinstance(self.tags, str):
            self.tags = [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    def add_recipe(self, recipe_id: int) -> bool:
        """Add recipe to collection"""
        if recipe_id not in self.recipe_ids:
            self.recipe_ids.add(recipe_id)
            self.updated_at = datetime.now()
            return True
        return False
    
    def remove_recipe(self, recipe_id: int) -> bool:
        """Remove recipe from collection"""
        if recipe_id in self.recipe_ids:
            self.recipe_ids.discard(recipe_id)
            self.updated_at = datetime.now()
            return True
        return False
    
    def get_recipe_count(self) -> int:
        """Get number of recipes in collection"""
        return len(self.recipe_ids)
    
    def has_tag(self, tag: str) -> bool:
        """Check if collection has a specific tag"""
        return tag.lower() in [t.lower() for t in self.tags]


@dataclass
class UserSession:
    """Session data for logged-in users"""
    user_id: int
    email: str
    username: str
    session_token: str
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    last_activity: datetime = field(default_factory=datetime.now)
    ip_address: str = ""
    user_agent: str = ""
    
    def is_expired(self) -> bool:
        """Check if session has expired"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    def refresh_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()


@dataclass
class ShoppingListItem:
    """Individual item in a shopping list"""
    ingredient_name: str
    total_quantity: float
    unit: str
    recipe_names: List[str] = field(default_factory=list)  # Which recipes need this ingredient
    category: str = ""  # ingredient category for grouping
    
    def add_recipe(self, recipe_name: str, quantity: float):
        """Add a recipe that uses this ingredient"""
        if recipe_name not in self.recipe_names:
            self.recipe_names.append(recipe_name)
        self.total_quantity += quantity


@dataclass
class ShoppingList:
    """
    Shopping list generated from recipe collections.
    Consolidates ingredients across multiple recipes with quantities.
    """
    collection_id: int
    collection_name: str
    items: List[ShoppingListItem] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    total_recipes: int = 0
    
    def add_ingredient(self, ingredient_name: str, quantity: float, unit: str, 
                      recipe_name: str, category: str = ""):
        """Add ingredient to shopping list, consolidating quantities"""
        # Look for existing item
        existing_item = None
        for item in self.items:
            if item.ingredient_name.lower() == ingredient_name.lower() and item.unit.lower() == unit.lower():
                existing_item = item
                break
        
        if existing_item:
            existing_item.add_recipe(recipe_name, quantity)
        else:
            new_item = ShoppingListItem(
                ingredient_name=ingredient_name,
                total_quantity=quantity,
                unit=unit,
                recipe_names=[recipe_name],
                category=category
            )
            self.items.append(new_item)
    
    def get_items_by_category(self) -> Dict[str, List[ShoppingListItem]]:
        """Group shopping list items by category"""
        categories = {}
        for item in self.items:
            category = item.category or "Other"
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        return categories
    
    def get_total_items(self) -> int:
        """Get total number of unique ingredients"""
        return len(self.items)