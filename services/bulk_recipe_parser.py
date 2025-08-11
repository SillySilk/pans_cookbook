"""
Bulk recipe parsing service for handling multiple recipes in one text dump.

Uses AI to identify recipe boundaries, extract individual recipes, and parse each one
separately. Perfect for importing recipe collections, cookbooks, or large text files.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from models import ScrapedRecipe
from services.ai_service import AIService
from utils import get_logger

logger = get_logger(__name__)


@dataclass
class RecipeBoundary:
    """Represents a detected recipe boundary in text"""
    title: str
    start_position: int
    end_position: int
    confidence: float


class BulkRecipeParser:
    """
    Bulk recipe parsing service using AI.
    
    Can handle:
    - Multiple recipes in one text file
    - Different recipe formats mixed together
    - Recipe collections from websites or books
    - Unstructured text with recipes mixed with other content
    """
    
    RECIPE_DETECTION_PROMPT = """You are an expert at finding recipes in text. Analyze this text and identify ALL individual recipes.

For each recipe found, extract:
1. TITLE: The recipe name/title
2. START: Character position where recipe begins (approximate)
3. END: Character position where recipe ends (approximate)
4. CONFIDENCE: How confident you are this is a complete recipe (0.0-1.0)

RULES:
- Look for recipe titles (often capitalized or on their own line)
- Recipes typically have ingredient lists and instructions
- Recipe boundaries are often marked by titles, extra spacing, or clear transitions
- Ignore partial recipes, ingredient lists without instructions, or just ingredient mentions
- Only include recipes that seem complete (have both ingredients AND instructions)

Return JSON array format:
[
  {
    "title": "Chocolate Chip Cookies",
    "start": 0,
    "end": 500,
    "confidence": 0.95
  },
  {
    "title": "Banana Bread", 
    "start": 501,
    "end": 850,
    "confidence": 0.90
  }
]

Text to analyze:"""

    RECIPE_EXTRACTION_PROMPT = """You are an expert recipe parser. Extract this recipe into structured data.

Extract these fields:
- title: Recipe name
- description: Brief description (if any)
- ingredients: Array of ingredient strings exactly as written
- instructions: Complete cooking instructions
- prep_time: Preparation time mentioned
- cook_time: Cooking time mentioned  
- total_time: Total time (if different from prep+cook)
- servings: Number of servings/yield
- difficulty: Difficulty level mentioned
- cuisine: Cuisine type if mentioned
- category: Meal category (breakfast, lunch, dinner, dessert, etc.)

Return valid JSON format. If a field is not found, use empty string or appropriate default.

EXAMPLE:
{
  "title": "Chocolate Chip Cookies",
  "description": "Classic homemade cookies",
  "ingredients": [
    "2 1/4 cups all-purpose flour",
    "1 tsp baking soda",
    "1 cup butter, softened",
    "3/4 cup granulated sugar",
    "2 large eggs"
  ],
  "instructions": "1. Preheat oven to 375°F. 2. Mix flour and baking soda...",
  "prep_time": "15 minutes",
  "cook_time": "10 minutes", 
  "total_time": "25 minutes",
  "servings": "36 cookies",
  "difficulty": "easy",
  "cuisine": "American",
  "category": "dessert"
}

Recipe text to extract:"""

    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
    
    def parse_bulk_text(self, text: str, source_name: str = "bulk_import") -> List[ScrapedRecipe]:
        """
        Parse bulk text containing multiple recipes.
        
        Args:
            text: Raw text containing one or more recipes
            source_name: Name/description of the source
            
        Returns:
            List of ScrapedRecipe objects for each detected recipe
        """
        if not self.ai_service.is_ai_available():
            logger.error("AI service not available for bulk parsing")
            return []
        
        # Step 1: Detect recipe boundaries
        recipe_boundaries = self._detect_recipe_boundaries(text)
        
        if not recipe_boundaries:
            logger.warning("No recipes detected in bulk text")
            return []
        
        logger.info(f"Detected {len(recipe_boundaries)} potential recipes")
        
        # Step 2: Extract each recipe individually
        scraped_recipes = []
        
        for i, boundary in enumerate(recipe_boundaries):
            try:
                # Extract text for this recipe
                recipe_text = text[boundary.start_position:boundary.end_position].strip()
                
                if len(recipe_text) < 50:  # Too short to be a real recipe
                    continue
                
                # Parse this individual recipe
                scraped_recipe = self._extract_single_recipe(
                    recipe_text, 
                    f"{source_name}_recipe_{i+1}",
                    boundary.title,
                    boundary.confidence
                )
                
                if scraped_recipe:
                    scraped_recipes.append(scraped_recipe)
                    logger.info(f"Successfully parsed: {scraped_recipe.title}")
                
            except Exception as e:
                logger.error(f"Failed to parse recipe {i+1} ({boundary.title}): {e}")
                continue
        
        logger.info(f"Successfully parsed {len(scraped_recipes)} recipes from bulk text")
        return scraped_recipes
    
    def _detect_recipe_boundaries(self, text: str) -> List[RecipeBoundary]:
        """Detect recipe boundaries using AI"""
        try:
            # Limit text size for AI processing
            max_chars = 50000  # ~50k characters max
            if len(text) > max_chars:
                logger.warning(f"Text too long ({len(text)} chars), truncating to {max_chars}")
                text = text[:max_chars]
            
            # Create AI prompt
            full_prompt = f"{self.RECIPE_DETECTION_PROMPT}\n\n{text}"
            
            # Get AI response
            response = self.ai_service.get_completion(
                prompt=full_prompt,
                max_tokens=2000,
                temperature=0.2  # Low temperature for consistent detection
            )
            
            if not response:
                logger.error("No AI response for recipe detection")
                return []
            
            # Parse JSON response
            try:
                boundaries_data = json.loads(response)
                if not isinstance(boundaries_data, list):
                    logger.error("AI response not a list")
                    return []
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI JSON for boundaries: {e}")
                return []
            
            # Convert to RecipeBoundary objects
            boundaries = []
            for boundary_data in boundaries_data:
                try:
                    boundary = RecipeBoundary(
                        title=str(boundary_data.get('title', 'Unknown Recipe')),
                        start_position=int(boundary_data.get('start', 0)),
                        end_position=int(boundary_data.get('end', len(text))),
                        confidence=float(boundary_data.get('confidence', 0.5))
                    )
                    
                    # Validate boundary positions
                    if boundary.end_position > len(text):
                        boundary.end_position = len(text)
                    if boundary.start_position >= boundary.end_position:
                        continue
                    
                    boundaries.append(boundary)
                    
                except (ValueError, KeyError) as e:
                    logger.warning(f"Invalid boundary data: {e}")
                    continue
            
            return boundaries
            
        except Exception as e:
            logger.error(f"Recipe boundary detection failed: {e}")
            return []
    
    def _extract_single_recipe(self, recipe_text: str, source_url: str, 
                              detected_title: str, confidence: float) -> Optional[ScrapedRecipe]:
        """Extract single recipe from text using AI"""
        try:
            # Create AI prompt for extraction
            full_prompt = f"{self.RECIPE_EXTRACTION_PROMPT}\n\n{recipe_text}"
            
            # Get AI response
            response = self.ai_service.get_completion(
                prompt=full_prompt,
                max_tokens=3000,
                temperature=0.1  # Very low temperature for consistent extraction
            )
            
            if not response:
                logger.error(f"No AI response for recipe extraction: {detected_title}")
                return None
            
            # Parse JSON response
            try:
                recipe_data = json.loads(response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI JSON for recipe {detected_title}: {e}")
                return None
            
            # Create ScrapedRecipe object
            scraped_recipe = ScrapedRecipe(
                url=source_url,
                title=str(recipe_data.get('title', detected_title)),
                description=str(recipe_data.get('description', '')),
                
                # Ingredients
                ingredients_raw=self._extract_ingredients_list(recipe_data.get('ingredients', [])),
                
                # Instructions
                instructions_raw=str(recipe_data.get('instructions', '')),
                
                # Times
                prep_time_text=str(recipe_data.get('prep_time', '')),
                cook_time_text=str(recipe_data.get('cook_time', '')),
                total_time_text=str(recipe_data.get('total_time', '')),
                
                # Other metadata
                servings_text=str(recipe_data.get('servings', '')),
                difficulty_text=str(recipe_data.get('difficulty', '')),
                cuisine_text=str(recipe_data.get('cuisine', '')),
                category_text=str(recipe_data.get('category', '')),
                
                # Confidence and metadata
                confidence_score=min(confidence, 0.9),  # Cap at 0.9 for AI parsing
                scraped_at=datetime.now(),
                scraping_method="ai_bulk_parser"
            )
            
            return scraped_recipe
            
        except Exception as e:
            logger.error(f"Single recipe extraction failed for {detected_title}: {e}")
            return None
    
    def _extract_ingredients_list(self, ingredients_data: Any) -> List[str]:
        """Extract ingredients list from AI response data"""
        if not ingredients_data:
            return []
        
        if isinstance(ingredients_data, list):
            return [str(ing).strip() for ing in ingredients_data if str(ing).strip()]
        elif isinstance(ingredients_data, str):
            # If AI returned a string, try to split it
            lines = ingredients_data.strip().split('\n')
            ingredients = []
            for line in lines:
                line = line.strip()
                if line and not line.lower().startswith('ingredients'):
                    # Remove bullet points or numbers
                    line = re.sub(r'^[-•*\d+\.)\s]+', '', line).strip()
                    if line:
                        ingredients.append(line)
            return ingredients
        
        return []
    
    def parse_recipe_collection_file(self, file_path: str) -> List[ScrapedRecipe]:
        """
        Parse a file containing multiple recipes.
        
        Args:
            file_path: Path to text file with recipes
            
        Returns:
            List of ScrapedRecipe objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            source_name = f"file_{file_path.split('/')[-1]}"
            return self.parse_bulk_text(content, source_name)
            
        except Exception as e:
            logger.error(f"Failed to read recipe file {file_path}: {e}")
            return []
    
    def split_recipe_text_manually(self, text: str, split_markers: List[str] = None) -> List[str]:
        """
        Manually split text into potential recipe sections.
        
        Fallback method when AI detection is not available or fails.
        
        Args:
            text: Raw text content
            split_markers: Custom markers to split on
            
        Returns:
            List of text sections that might contain recipes
        """
        if split_markers is None:
            split_markers = [
                '\n\n\n',  # Multiple line breaks
                '---',     # Horizontal rules
                '***',     # Alternative horizontal rules
                'Recipe:',  # Explicit recipe markers
                'RECIPE:',
                '\nNext recipe',
                '\nRecipe #'
            ]
        
        sections = [text]
        
        for marker in split_markers:
            new_sections = []
            for section in sections:
                parts = section.split(marker)
                new_sections.extend([part.strip() for part in parts if part.strip()])
            sections = new_sections
        
        # Filter out sections that are too short to be recipes
        recipe_sections = []
        for section in sections:
            if len(section) > 200 and self._looks_like_recipe(section):
                recipe_sections.append(section)
        
        return recipe_sections
    
    def _looks_like_recipe(self, text: str) -> bool:
        """Simple heuristic to check if text looks like a recipe"""
        text_lower = text.lower()
        
        # Check for recipe indicators
        recipe_indicators = [
            'ingredients:', 'instructions:', 'directions:', 'method:',
            'cup', 'tablespoon', 'teaspoon', 'ounce', 'pound',
            'preheat', 'bake', 'cook', 'mix', 'stir', 'heat'
        ]
        
        indicator_count = sum(1 for indicator in recipe_indicators if indicator in text_lower)
        
        # If we find several indicators and the text is substantial, it's likely a recipe
        return indicator_count >= 3 and len(text) > 300


# Convenience function
def get_bulk_recipe_parser(ai_service: Optional[AIService] = None) -> BulkRecipeParser:
    """Get bulk recipe parser instance"""
    if ai_service is None:
        from services.ai_service import get_ai_service
        ai_service = get_ai_service()
    
    return BulkRecipeParser(ai_service)