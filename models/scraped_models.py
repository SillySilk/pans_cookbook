"""
Models for web scraping and recipe parsing operations.

Adapted from the Herbalism app scraper models with focus on recipe data validation.
Supports traditional HTML parsing with manual validation workflows.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class ScrapedRecipe:
    """
    Raw recipe data scraped from a website before validation.
    Contains potentially incomplete or incorrectly parsed fields.
    """
    url: str
    title: str = ""
    description: str = ""
    ingredients_raw: List[str] = field(default_factory=list)
    instructions_raw: str = ""
    prep_time_text: str = ""
    cook_time_text: str = ""
    total_time_text: str = ""
    servings_text: str = ""
    nutrition_raw: Dict[str, Any] = field(default_factory=dict)
    cuisine_text: str = ""
    category_text: str = ""
    difficulty_text: str = ""
    rating_text: str = ""
    
    # Metadata about scraping process
    scraped_at: datetime = field(default_factory=datetime.now)
    scraping_method: str = ""  # structured_selectors, fallback_parsing, etc.
    confidence_score: float = 0.0  # 0.0 to 1.0
    parsing_warnings: List[str] = field(default_factory=list)
    
    def add_warning(self, warning: str):
        """Add a parsing warning"""
        self.parsing_warnings.append(warning)
        if self.confidence_score > 0.7:
            self.confidence_score = 0.7  # Lower confidence if warnings present
    
    def has_minimum_data(self) -> bool:
        """Check if scraped data has minimum required fields"""
        return bool(self.title and self.ingredients_raw and self.instructions_raw)


@dataclass
class ParsedRecipe:
    """
    Recipe data after parsing and normalization but before user validation.
    Time and numeric fields are parsed into structured format.
    """
    title: str
    description: str
    instructions: str
    source_url: str = ""
    ingredients: List[Dict[str, Any]] = field(default_factory=list)  # parsed ingredient dicts
    prep_time_minutes: int = 0
    cook_time_minutes: int = 0
    servings: int = 1
    difficulty_level: str = "medium"
    cuisine_type: str = ""
    meal_category: str = ""
    dietary_tags: List[str] = field(default_factory=list)
    
    # Parsing confidence and issues
    parsing_issues: List[str] = field(default_factory=list)
    fields_needing_review: List[str] = field(default_factory=list)
    ingredient_matches: Dict[str, List[str]] = field(default_factory=dict)  # potential matches for unknown ingredients
    
    def add_parsing_issue(self, field_name: str, issue: str):
        """Add a parsing issue for a specific field"""
        self.parsing_issues.append(f"{field_name}: {issue}")
        if field_name not in self.fields_needing_review:
            self.fields_needing_review.append(field_name)
    
    def needs_review(self) -> bool:
        """Check if recipe needs manual review"""
        return len(self.fields_needing_review) > 0 or len(self.parsing_issues) > 0
    
    def get_total_time(self) -> int:
        """Get total cooking time"""
        return self.prep_time_minutes + self.cook_time_minutes


@dataclass
class ValidationResult:
    """
    Result of manual validation process for scraped recipe data.
    Tracks user corrections and final validated state.
    """
    is_valid: bool
    validated_recipe: Optional['ParsedRecipe'] = None
    field_corrections: Dict[str, Any] = field(default_factory=dict)  # field -> corrected_value
    ingredient_assignments: Dict[str, int] = field(default_factory=dict)  # ingredient_name -> ingredient_id
    new_ingredients: List[str] = field(default_factory=list)  # ingredients to add to database
    validation_notes: List[str] = field(default_factory=list)
    validated_by: int = 0  # user_id
    validated_at: datetime = field(default_factory=datetime.now)
    
    def add_correction(self, field_name: str, original_value: Any, corrected_value: Any):
        """Record a field correction"""
        self.field_corrections[field_name] = {
            'original': original_value,
            'corrected': corrected_value
        }
    
    def add_ingredient_assignment(self, ingredient_text: str, ingredient_id: int):
        """Assign parsed ingredient text to existing database ingredient"""
        self.ingredient_assignments[ingredient_text] = ingredient_id
    
    def add_new_ingredient(self, ingredient_name: str):
        """Mark ingredient as needing to be added to database"""
        if ingredient_name not in self.new_ingredients:
            self.new_ingredients.append(ingredient_name)
    
    def get_correction_summary(self) -> str:
        """Get summary of corrections made"""
        if not self.field_corrections:
            return "No corrections needed"
        
        corrections = []
        for field, data in self.field_corrections.items():
            corrections.append(f"{field}: {data['original']} → {data['corrected']}")
        
        return "; ".join(corrections)
    
    def add_field_error(self, field_name: str, error_message: str):
        """Add field validation error"""
        error = f"{field_name}: {error_message}"
        self.validation_notes.append(error)
        self.is_valid = False
    
    def add_safety_warning(self, warning_message: str):
        """Add safety warning"""
        warning = f"WARNING: {warning_message}"
        self.validation_notes.append(warning)
    
    def get_all_errors(self) -> List[str]:
        """Get all validation errors"""
        return [note for note in self.validation_notes if not note.startswith("WARNING:")]
    
    @property
    def safety_warnings(self) -> List[str]:
        """Get all safety warnings"""
        return [note.replace("WARNING: ", "") for note in self.validation_notes if note.startswith("WARNING:")]


@dataclass
class ScrapingResult:
    """
    Complete result of a recipe scraping operation.
    Provides detailed success/failure information for debugging.
    """
    success: bool
    url: str
    scraped_recipe: Optional[ScrapedRecipe] = None
    parsed_recipe: Optional[ParsedRecipe] = None
    validation_result: Optional[ValidationResult] = None
    final_recipe_id: Optional[int] = None
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    scraping_duration_seconds: float = 0.0
    
    # Step tracking
    robots_txt_allowed: bool = False
    html_retrieved: bool = False
    parsing_attempted: bool = False
    validation_completed: bool = False
    database_saved: bool = False
    
    def add_error(self, error: str, step: str = ""):
        """Add error with optional step context"""
        error_msg = f"[{step}] {error}" if step else error
        self.errors.append(error_msg)
        self.success = False
    
    def add_warning(self, warning: str, step: str = ""):
        """Add warning with optional step context"""
        warning_msg = f"[{step}] {warning}" if step else warning
        self.warnings.append(warning_msg)
    
    def get_status_summary(self) -> str:
        """Get human-readable status summary"""
        if self.success:
            return f"✅ Recipe successfully scraped and saved (ID: {self.final_recipe_id})"
        elif self.errors:
            return f"❌ Scraping failed: {self.errors[0]}"
        else:
            return "⚠️ Scraping incomplete - unknown status"