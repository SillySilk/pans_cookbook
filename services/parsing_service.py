"""
Recipe parsing and validation service for Pans Cookbook application.

Converts scraped recipe data into structured, normalized format with
comprehensive validation. Adapted from Herbalism app validation patterns
with recipe-specific data handling and ingredient categorization.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import asdict

from models import ScrapedRecipe, ParsedRecipe, ValidationResult, Ingredient
from services.database_service import DatabaseService, get_database_service
from utils import get_logger

logger = get_logger(__name__)


class ParsingService:
    """
    Recipe parsing and validation service.
    
    Normalizes scraped recipe data into structured format and validates
    completeness and accuracy. Includes ingredient matching and time parsing.
    """
    
    def __init__(self, database_service: Optional[DatabaseService] = None):
        self.db = database_service or get_database_service()
        
        # Preload ingredients for matching
        self._ingredients_cache = self._load_ingredients_cache()
        
        # Common time units for parsing
        self._time_patterns = self._compile_time_patterns()
        
        # Common measurement units
        self._measurement_units = self._load_measurement_units()
    
    def parse_scraped_recipe(self, scraped_recipe: ScrapedRecipe) -> ParsedRecipe:
        """
        Convert scraped recipe data to structured parsed format.
        
        Args:
            scraped_recipe: Raw scraped data from web scraping
            
        Returns:
            ParsedRecipe with normalized and validated data
        """
        parsed_recipe = ParsedRecipe(
            title=self._clean_title(scraped_recipe.title),
            description=self._clean_description(scraped_recipe.description),
            instructions=self._clean_instructions(scraped_recipe.instructions_raw),
            source_url=scraped_recipe.url
        )
        
        # Parse time fields
        parsed_recipe.prep_time_minutes = self._parse_time_to_minutes(scraped_recipe.prep_time_text)
        parsed_recipe.cook_time_minutes = self._parse_time_to_minutes(scraped_recipe.cook_time_text)
        
        # If no individual times but total time exists, split it
        if parsed_recipe.prep_time_minutes == 0 and parsed_recipe.cook_time_minutes == 0:
            total_time = self._parse_time_to_minutes(scraped_recipe.total_time_text)
            if total_time > 0:
                # Assume 25% prep, 75% cook time if not specified
                parsed_recipe.prep_time_minutes = int(total_time * 0.25)
                parsed_recipe.cook_time_minutes = total_time - parsed_recipe.prep_time_minutes
        
        # Parse servings
        parsed_recipe.servings = self._parse_servings(scraped_recipe.servings_text)
        
        # Parse categorical data
        parsed_recipe.difficulty_level = self._parse_difficulty(scraped_recipe.difficulty_text)
        parsed_recipe.cuisine_type = self._clean_cuisine(scraped_recipe.cuisine_text)
        parsed_recipe.meal_category = self._parse_meal_category(scraped_recipe.category_text)
        parsed_recipe.dietary_tags = self._extract_dietary_tags(scraped_recipe, parsed_recipe)
        
        # Parse and match ingredients
        parsed_recipe.ingredients, parsed_recipe.ingredient_matches = self._parse_ingredients(
            scraped_recipe.ingredients_raw
        )
        
        # Identify parsing issues
        self._identify_parsing_issues(scraped_recipe, parsed_recipe)
        
        logger.info(f"Parsed recipe: {parsed_recipe.title} with {len(parsed_recipe.ingredients)} ingredients")
        
        return parsed_recipe
    
    def validate_parsed_recipe(self, parsed_recipe: ParsedRecipe) -> ValidationResult:
        """
        Validate parsed recipe data for completeness and accuracy.
        
        Args:
            parsed_recipe: Structured recipe data to validate
            
        Returns:
            ValidationResult with validation status and issues
        """
        result = ValidationResult(is_valid=True)
        
        # Validate required fields
        self._validate_required_fields(parsed_recipe, result)
        
        # Validate data ranges and formats
        self._validate_data_ranges(parsed_recipe, result)
        
        # Validate ingredient consistency
        self._validate_ingredients(parsed_recipe, result)
        
        # Check for common parsing issues
        self._check_parsing_quality(parsed_recipe, result)
        
        # Add validation notes
        if result.is_valid:
            result.validation_notes.append("Recipe validation passed")
        else:
            result.validation_notes.append(f"Recipe validation failed with {len(result.get_all_errors())} errors")
        
        result.validated_at = datetime.now()
        
        return result
    
    def suggest_ingredient_matches(self, ingredient_text: str, max_suggestions: int = 5) -> List[Tuple[Ingredient, float]]:
        """
        Suggest matching ingredients from database for unknown ingredient text.
        
        Args:
            ingredient_text: Raw ingredient text to match
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            List of (Ingredient, confidence_score) tuples, sorted by confidence
        """
        ingredient_text = ingredient_text.lower().strip()
        suggestions = []
        
        for ingredient in self._ingredients_cache:
            confidence = self._calculate_ingredient_similarity(ingredient_text, ingredient)
            if confidence > 0.3:  # Minimum confidence threshold
                suggestions.append((ingredient, confidence))
        
        # Sort by confidence score, descending
        suggestions.sort(key=lambda x: x[1], reverse=True)
        
        return suggestions[:max_suggestions]
    
    def _clean_title(self, title: str) -> str:
        """Clean and normalize recipe title"""
        if not title:
            return ""
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', title.strip())
        
        # Remove common recipe site suffixes
        suffixes_to_remove = [
            r'\s*-\s*[^-]+\.com$',  # - sitename.com
            r'\s*|\s*[^|]+$',      # | Site Name
            r'\s*recipe\s*$',       # Recipe (case insensitive)
        ]
        
        for pattern in suffixes_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _clean_description(self, description: str) -> str:
        """Clean and normalize recipe description"""
        if not description:
            return ""
        
        # Remove extra whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', description.strip())
        
        # Limit length to reasonable size
        if len(cleaned) > 500:
            cleaned = cleaned[:497] + "..."
        
        return cleaned
    
    def _clean_instructions(self, instructions: str) -> str:
        """Clean and normalize cooking instructions"""
        if not instructions:
            return ""
        
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', instructions.strip())
        
        # Add periods after numbered steps if missing
        cleaned = re.sub(r'(\d+)\s*([^.!?])', r'\1. \2', cleaned)
        
        # Ensure steps are separated by newlines
        cleaned = re.sub(r'(\.)(\s*)(\d+)', r'\1\n\2\3', cleaned)
        
        return cleaned
    
    def _parse_time_to_minutes(self, time_text: str) -> int:
        """Parse time text to minutes"""
        if not time_text:
            return 0
        
        time_text = time_text.lower().strip()
        
        # Check for ISO 8601 duration format (PT15M, PT1H30M)
        iso_match = re.search(r'pt(?:(\d+)h)?(?:(\d+)m)?', time_text)
        if iso_match:
            hours = int(iso_match.group(1) or 0)
            minutes = int(iso_match.group(2) or 0)
            return hours * 60 + minutes
        
        # Parse various time formats
        total_minutes = 0
        
        # Hours
        hour_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h\b)', time_text)
        if hour_match:
            total_minutes += int(float(hour_match.group(1)) * 60)
        
        # Minutes
        min_match = re.search(r'(\d+)\s*(?:minutes?|mins?|m\b)', time_text)
        if min_match:
            total_minutes += int(min_match.group(1))
        
        # Time format like "1:30" (hour:minute)
        time_format_match = re.search(r'(\d+):(\d+)', time_text)
        if time_format_match and total_minutes == 0:
            hours = int(time_format_match.group(1))
            minutes = int(time_format_match.group(2))
            total_minutes = hours * 60 + minutes
        
        # Just digits (assume minutes if reasonable, hours if large)
        if total_minutes == 0:
            digit_match = re.search(r'\b(\d+)\b', time_text)
            if digit_match:
                value = int(digit_match.group(1))
                if value <= 180:  # Assume minutes if <= 3 hours
                    total_minutes = value
                elif value <= 12:  # Assume hours if reasonable
                    total_minutes = value * 60
        
        return total_minutes
    
    def _parse_servings(self, servings_text: str) -> int:
        """Parse servings text to integer"""
        if not servings_text:
            return 1
        
        # Extract first number found
        match = re.search(r'(\d+)', servings_text)
        if match:
            servings = int(match.group(1))
            # Reasonable range check
            if 1 <= servings <= 50:
                return servings
        
        return 1  # Default to 1 serving
    
    def _parse_difficulty(self, difficulty_text: str) -> str:
        """Parse difficulty level"""
        if not difficulty_text:
            return "medium"
        
        difficulty_text = difficulty_text.lower()
        
        if any(word in difficulty_text for word in ['easy', 'simple', 'basic', 'beginner']):
            return "easy"
        elif any(word in difficulty_text for word in ['hard', 'difficult', 'advanced', 'expert']):
            return "hard"
        else:
            return "medium"
    
    def _clean_cuisine(self, cuisine_text: str) -> str:
        """Clean and normalize cuisine type"""
        if not cuisine_text:
            return ""
        
        cuisine_text = cuisine_text.strip().title()
        
        # Normalize common variations
        cuisine_mapping = {
            'American': ['American', 'USA', 'US'],
            'Italian': ['Italian', 'Italia'],
            'Mexican': ['Mexican', 'Mexico'],
            'Chinese': ['Chinese', 'China'],
            'Indian': ['Indian', 'India'],
            'French': ['French', 'France'],
            'Thai': ['Thai', 'Thailand'],
            'Japanese': ['Japanese', 'Japan'],
            'Mediterranean': ['Mediterranean', 'Med'],
        }
        
        for normalized, variations in cuisine_mapping.items():
            if any(var.lower() in cuisine_text.lower() for var in variations):
                return normalized
        
        return cuisine_text
    
    def _parse_meal_category(self, category_text: str) -> str:
        """Parse meal category"""
        if not category_text:
            return ""
        
        category_text = category_text.lower()
        
        category_mapping = {
            'breakfast': ['breakfast', 'brunch'],
            'lunch': ['lunch'],
            'dinner': ['dinner', 'supper', 'main'],
            'snack': ['snack', 'appetizer'],
            'dessert': ['dessert', 'sweet', 'cake', 'cookie'],
        }
        
        for category, keywords in category_mapping.items():
            if any(keyword in category_text for keyword in keywords):
                return category
        
        return ""
    
    def _extract_dietary_tags(self, scraped_recipe: ScrapedRecipe, parsed_recipe: ParsedRecipe) -> List[str]:
        """Extract dietary tags from recipe content"""
        tags = []
        
        # Combine all text for analysis
        all_text = " ".join([
            scraped_recipe.title.lower(),
            scraped_recipe.description.lower(),
            scraped_recipe.instructions_raw.lower(),
            " ".join(scraped_recipe.ingredients_raw).lower()
        ])
        
        # Check for dietary indicators
        dietary_indicators = {
            'vegetarian': ['vegetarian', 'veggie'],
            'vegan': ['vegan'],
            'gluten-free': ['gluten-free', 'gluten free', 'gf'],
            'dairy-free': ['dairy-free', 'dairy free', 'lactose free'],
            'low-carb': ['low-carb', 'low carb', 'keto'],
            'high-protein': ['high-protein', 'high protein', 'protein'],
            'healthy': ['healthy', 'light', 'nutritious'],
        }
        
        for tag, indicators in dietary_indicators.items():
            if any(indicator in all_text for indicator in indicators):
                tags.append(tag)
        
        # Ingredient-based detection
        ingredient_text = " ".join(scraped_recipe.ingredients_raw).lower()
        
        # Check for meat indicators
        meat_indicators = ['chicken', 'beef', 'pork', 'fish', 'lamb', 'turkey', 'bacon', 'sausage']
        has_meat = any(meat in ingredient_text for meat in meat_indicators)
        
        if not has_meat and 'vegetarian' not in tags:
            # Could be vegetarian - but don't auto-add, let user decide
            pass
        
        # Check for dairy
        dairy_indicators = ['milk', 'cheese', 'butter', 'cream', 'yogurt']
        has_dairy = any(dairy in ingredient_text for dairy in dairy_indicators)
        
        if not has_dairy and 'dairy-free' not in tags:
            # Could be dairy-free
            pass
        
        return list(set(tags))  # Remove duplicates
    
    def _parse_ingredients(self, ingredients_raw: List[str]) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
        """Parse raw ingredient strings into structured data"""
        parsed_ingredients = []
        ingredient_matches = {}
        
        for i, ingredient_text in enumerate(ingredients_raw):
            if not ingredient_text.strip():
                continue
            
            # Parse quantity, unit, and ingredient name
            parsed_ingredient = self._parse_single_ingredient(ingredient_text, i + 1)
            parsed_ingredients.append(parsed_ingredient)
            
            # Find potential matches in database
            ingredient_name = parsed_ingredient.get('name', '').lower()
            if ingredient_name:
                matches = self.suggest_ingredient_matches(ingredient_name, max_suggestions=3)
                if matches:
                    ingredient_matches[ingredient_text] = [ing.name for ing, _ in matches]
        
        return parsed_ingredients, ingredient_matches
    
    def _parse_single_ingredient(self, ingredient_text: str, order: int) -> Dict[str, Any]:
        """Parse a single ingredient string into components"""
        original_text = ingredient_text.strip()
        
        # Initialize result
        result = {
            'original_text': original_text,
            'quantity': 0.0,
            'unit': '',
            'name': '',
            'preparation': '',
            'optional': False,
            'order': order
        }
        
        # Check for optional indicators
        if any(indicator in original_text.lower() for indicator in ['optional', '(optional)', 'to taste']):
            result['optional'] = True
        
        # Improved regex for quantity + unit parsing
        # Handle mixed fractions, decimals, and ranges
        quantity_pattern = r'^(\d+(?:\s+\d+/\d+|\.\d+|/\d+)?(?:\s*-\s*\d+(?:\s+\d+/\d+|\.\d+|/\d+)?)?)\s+([a-zA-Z-]+(?:\s+[a-zA-Z-]+)*?)\s+(.*)'
        
        # Try main pattern first
        match = re.match(quantity_pattern, original_text)
        
        if match:
            quantity_str, unit_str, remainder = match.groups()
            
            # Parse quantity
            result['quantity'] = self._parse_quantity(quantity_str.strip())
            
            # Check if unit is actually a descriptor (size/type)
            unit_clean = unit_str.strip().lower()
            if self._is_descriptor_not_unit(unit_clean):
                # This is a descriptor, not a unit - include it with the ingredient name
                result['unit'] = ''
                result['name'], result['preparation'] = self._parse_ingredient_name_and_prep(f"{unit_str} {remainder}".strip())
            else:
                result['unit'] = self._normalize_unit(unit_clean)
                result['name'], result['preparation'] = self._parse_ingredient_name_and_prep(remainder.strip())
        else:
            # Try simpler pattern for cases like "3 large eggs" or "salt to taste"
            simple_pattern = r'^(\d+(?:\s+\d+/\d+|\.\d+|/\d+)?)\s+(.*)'
            simple_match = re.match(simple_pattern, original_text)
            
            if simple_match:
                quantity_str, remainder = simple_match.groups()
                result['quantity'] = self._parse_quantity(quantity_str.strip())
                result['name'], result['preparation'] = self._parse_ingredient_name_and_prep(remainder.strip())
            else:
                # No quantity found - treat as ingredient name only
                result['name'], result['preparation'] = self._parse_ingredient_name_and_prep(original_text)
        
        return result
    
    def _parse_quantity(self, quantity_str: str) -> float:
        """Parse quantity string to float"""
        try:
            # Handle ranges like "2-3" - take the first value
            if '-' in quantity_str:
                quantity_str = quantity_str.split('-')[0].strip()
            
            # Handle fractions like "1 1/2" or "1/2"
            if '/' in quantity_str:
                # Mixed number like "1 1/2" or "2 1/4"
                if ' ' in quantity_str.strip():
                    parts = quantity_str.strip().split()
                    if len(parts) == 2:
                        whole = float(parts[0])
                        if '/' in parts[1]:
                            fraction_parts = parts[1].split('/')
                            fraction = float(fraction_parts[0]) / float(fraction_parts[1])
                            return whole + fraction
                else:
                    # Simple fraction like "1/2"
                    parts = quantity_str.split('/')
                    if len(parts) == 2:
                        return float(parts[0]) / float(parts[1])
            else:
                return float(quantity_str)
        except (ValueError, ZeroDivisionError, IndexError):
            return 0.0
    
    def _is_descriptor_not_unit(self, text: str) -> bool:
        """Check if text is a size/type descriptor rather than a measurement unit"""
        descriptors = {
            'large', 'medium', 'small', 'extra-large', 'jumbo',
            'fresh', 'dried', 'frozen', 'canned', 'whole',
            'lean', 'boneless', 'skinless', 'ground',
            'ripe', 'green', 'red', 'yellow', 'white',
            'thick', 'thin', 'fine', 'coarse'
        }
        return text in descriptors
    
    def _normalize_unit(self, unit_str: str) -> str:
        """Normalize measurement unit"""
        unit_str = unit_str.lower()
        
        unit_mapping = {
            # Volume
            'cup': ['cup', 'cups', 'c'],
            'tablespoon': ['tablespoon', 'tablespoons', 'tbsp', 'tbs'],
            'teaspoon': ['teaspoon', 'teaspoons', 'tsp'],
            'liter': ['liter', 'liters', 'l', 'litre', 'litres'],
            'milliliter': ['milliliter', 'milliliters', 'ml'],
            'fluid-ounce': ['fl-oz', 'fl oz', 'fluid ounce'],
            
            # Weight
            'pound': ['pound', 'pounds', 'lb', 'lbs'],
            'ounce': ['ounce', 'ounces', 'oz'],
            'gram': ['gram', 'grams', 'g'],
            'kilogram': ['kilogram', 'kilograms', 'kg'],
            
            # Count
            'piece': ['piece', 'pieces', 'pc', 'pcs'],
            'item': ['item', 'items'],
            'clove': ['clove', 'cloves'],
            'slice': ['slice', 'slices'],
        }
        
        for normalized, variations in unit_mapping.items():
            if unit_str in variations:
                return normalized
        
        return unit_str
    
    def _parse_ingredient_name_and_prep(self, text: str) -> Tuple[str, str]:
        """Parse ingredient name and preparation instructions"""
        # Common preparation indicators
        prep_patterns = [
            r',\s*(chopped|diced|sliced|minced|grated|shredded|crushed|ground|softened)',
            r',\s*(fresh|dried|frozen|canned|room\s+temperature)',
            r',\s*(peeled|seeded|stemmed|trimmed|pitted)',
            r'\((.*?)\)',  # Parenthetical instructions
        ]
        
        name = text
        preparations = []
        
        for pattern in prep_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Handle nested matches from parentheses
                for match in matches:
                    if isinstance(match, str):
                        preparations.append(match.strip())
                    else:
                        # This handles tuple results from groups
                        preparations.extend([m.strip() for m in match if m.strip()])
                
                # Remove matched preparation from name
                name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        # Clean up name - remove extra commas and whitespace
        name = re.sub(r'\s*,\s*$', '', name.strip())
        name = re.sub(r'\s+', ' ', name)
        
        return name, ', '.join(preparations) if preparations else ''
    
    def _calculate_ingredient_similarity(self, input_text: str, ingredient: Ingredient) -> float:
        """Calculate similarity between input text and database ingredient"""
        input_text = input_text.lower()
        ingredient_name = ingredient.name.lower()
        
        # Exact match
        if input_text == ingredient_name:
            return 1.0
        
        # Check if one contains the other
        if input_text in ingredient_name or ingredient_name in input_text:
            return 0.8
        
        # Word overlap scoring
        input_words = set(input_text.split())
        ingredient_words = set(ingredient_name.split())
        
        if input_words and ingredient_words:
            overlap = len(input_words & ingredient_words)
            total = len(input_words | ingredient_words)
            return overlap / total if total > 0 else 0.0
        
        return 0.0
    
    def _identify_parsing_issues(self, scraped_recipe: ScrapedRecipe, parsed_recipe: ParsedRecipe):
        """Identify potential parsing issues that need review"""
        # Check for missing essential data
        if not parsed_recipe.title:
            parsed_recipe.add_parsing_issue("title", "Recipe title is missing")
        
        if not parsed_recipe.ingredients:
            parsed_recipe.add_parsing_issue("ingredients", "No ingredients found")
        elif len(parsed_recipe.ingredients) < 2:
            parsed_recipe.add_parsing_issue("ingredients", "Very few ingredients found")
        
        if not parsed_recipe.instructions:
            parsed_recipe.add_parsing_issue("instructions", "Cooking instructions are missing")
        elif len(parsed_recipe.instructions) < 50:
            parsed_recipe.add_parsing_issue("instructions", "Instructions seem too short")
        
        # Check for unreasonable values
        if parsed_recipe.prep_time_minutes > 300:  # > 5 hours
            parsed_recipe.add_parsing_issue("prep_time", "Prep time seems unusually long")
        
        if parsed_recipe.cook_time_minutes > 720:  # > 12 hours
            parsed_recipe.add_parsing_issue("cook_time", "Cook time seems unusually long")
        
        if parsed_recipe.servings > 20:
            parsed_recipe.add_parsing_issue("servings", "Serving count seems unusually high")
    
    def _validate_required_fields(self, parsed_recipe: ParsedRecipe, result: ValidationResult):
        """Validate required fields are present"""
        if not parsed_recipe.title.strip():
            result.add_field_error("title", "Recipe title is required")
        
        if not parsed_recipe.instructions.strip():
            result.add_field_error("instructions", "Cooking instructions are required")
        
        if not parsed_recipe.ingredients:
            result.add_field_error("ingredients", "At least one ingredient is required")
    
    def _validate_data_ranges(self, parsed_recipe: ParsedRecipe, result: ValidationResult):
        """Validate data is within reasonable ranges"""
        if parsed_recipe.servings < 1 or parsed_recipe.servings > 50:
            result.add_field_error("servings", "Servings must be between 1 and 50")
        
        if parsed_recipe.prep_time_minutes < 0 or parsed_recipe.prep_time_minutes > 600:
            result.add_field_error("prep_time", "Prep time must be between 0 and 600 minutes")
        
        if parsed_recipe.cook_time_minutes < 0 or parsed_recipe.cook_time_minutes > 1440:
            result.add_field_error("cook_time", "Cook time must be between 0 and 1440 minutes")
    
    def _validate_ingredients(self, parsed_recipe: ParsedRecipe, result: ValidationResult):
        """Validate ingredient data"""
        if len(parsed_recipe.ingredients) < 2:
            result.add_field_error("ingredients", "Recipe should have at least 2 ingredients")
        
        for i, ingredient in enumerate(parsed_recipe.ingredients):
            if not ingredient.get('name', '').strip():
                result.add_field_error("ingredients", f"Ingredient {i+1} is missing a name")
    
    def _check_parsing_quality(self, parsed_recipe: ParsedRecipe, result: ValidationResult):
        """Check overall parsing quality"""
        if parsed_recipe.needs_review():
            for issue in parsed_recipe.parsing_issues:
                result.add_safety_warning(f"Parsing issue: {issue}")
    
    def _load_ingredients_cache(self) -> List[Ingredient]:
        """Load ingredients from database for matching"""
        try:
            return self.db.get_all_ingredients()
        except Exception as e:
            logger.error(f"Failed to load ingredients cache: {e}")
            return []
    
    def _compile_time_patterns(self) -> Dict[str, str]:
        """Compile regex patterns for time parsing"""
        return {
            'iso_duration': r'PT(?:(\d+)H)?(?:(\d+)M)?',
            'hours_minutes': r'(\d+)\s*(?:hours?|hrs?|h)\s*(?:(\d+)\s*(?:minutes?|mins?|m))?',
            'minutes_only': r'(\d+)\s*(?:minutes?|mins?|m)',
            'time_format': r'(\d+):(\d+)',
        }
    
    def _load_measurement_units(self) -> Dict[str, List[str]]:
        """Load measurement unit mappings"""
        return {
            'volume': ['cup', 'tablespoon', 'teaspoon', 'liter', 'milliliter', 'fluid-ounce'],
            'weight': ['pound', 'ounce', 'gram', 'kilogram'],
            'count': ['piece', 'item', 'clove', 'slice', 'whole'],
        }


def get_parsing_service(database_service: Optional[DatabaseService] = None) -> ParsingService:
    """Get singleton parsing service instance"""
    global _parsing_service
    if '_parsing_service' not in globals():
        globals()['_parsing_service'] = ParsingService(database_service)
    return globals()['_parsing_service']
