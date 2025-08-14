"""
Recipe-related data models for the Pans Cookbook application.

Models follow the design from the Herbalism app with adaptations for culinary recipes.
All models use dataclasses for clean, type-safe data structures that map to SQLite tables.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict, Any
from datetime import datetime


@dataclass
class NutritionData:
    """Nutritional information per serving"""
    calories: Optional[int] = None
    protein_grams: Optional[float] = None
    carbs_grams: Optional[float] = None
    fat_grams: Optional[float] = None
    fiber_grams: Optional[float] = None
    sodium_milligrams: Optional[float] = None
    sugar_grams: Optional[float] = None


@dataclass
class Ingredient:
    """
    Ingredient model mapping to ingredients table.
    Adapted from Herbalism app Herb model with recipe-specific fields.
    """
    id: int
    name: str
    category: str  # protein, vegetable, spice, dairy, grain, etc.
    common_substitutes: List[str] = field(default_factory=list)
    storage_tips: str = ""
    nutritional_data: Optional[NutritionData] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Ensure common_substitutes is a list"""
        if isinstance(self.common_substitutes, str):
            self.common_substitutes = [sub.strip() for sub in self.common_substitutes.split(',') if sub.strip()]


@dataclass
class RecipeIngredient:
    """
    Junction table model for recipe-ingredient relationships with quantities.
    Enables many-to-many relationship between recipes and ingredients.
    """
    recipe_id: int
    ingredient_id: int
    quantity: float
    unit: str  # cup, tablespoon, gram, ounce, etc.
    preparation_note: str = ""  # diced, minced, optional, etc.
    ingredient_order: int = 0  # for display ordering
    is_optional: bool = False  # whether ingredient is optional
    
    def get_display_text(self) -> str:
        """Format ingredient for display in recipe"""
        quantity_str = f"{self.quantity:g}" if self.quantity != int(self.quantity) else str(int(self.quantity))
        text = f"{quantity_str} {self.unit}"
        if self.preparation_note:
            text += f" ({self.preparation_note})"
        return text


@dataclass
class Recipe:
    """
    Core recipe model mapping to recipes table.
    Simplified for single-household use - no user tracking or timestamps.
    """
    id: int
    name: str
    description: str
    instructions: str
    prep_time_minutes: int
    cook_time_minutes: int
    servings: int
    nutritional_info: Optional[NutritionData] = None
    source_url: Optional[str] = None
    image_path: Optional[str] = None
    
    # Relationship fields (populated by database service)
    ingredients: List[RecipeIngredient] = field(default_factory=list)
    required_ingredient_ids: Set[int] = field(default_factory=set)
    
    def __post_init__(self):
        """Basic validation"""
        pass
    
    def get_total_time_minutes(self) -> int:
        """Calculate total cooking time"""
        return self.prep_time_minutes + self.cook_time_minutes
    
    def has_dietary_tag(self, tag: str) -> bool:
        """Check if recipe has a specific dietary tag (case-insensitive)"""
        # This method is kept for compatibility but always returns False
        # since we removed dietary_tags from the simplified model
        return False
    
    def can_make_with_ingredients(self, available_ingredient_ids: Set[int]) -> tuple[bool, Set[int]]:
        """
        Check if recipe can be made with available ingredients.
        Returns (can_make, missing_ingredient_ids)
        """
        missing = self.required_ingredient_ids - available_ingredient_ids
        return len(missing) == 0, missing
    
    def get_missing_ingredients_count(self, available_ingredient_ids: Set[int]) -> int:
        """Get count of missing ingredients"""
        return len(self.required_ingredient_ids - available_ingredient_ids)