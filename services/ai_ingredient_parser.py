"""
AI-powered ingredient parsing service for Pans Cookbook.

Uses AI models to accurately extract quantity, unit, ingredient name, and preparation
from raw ingredient text with custom recipe-specific prompting.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from services.ai_service import AIService
from services.database_service import DatabaseService
from utils import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedIngredient:
    """Single parsed ingredient with all components"""
    original_text: str
    quantity: float
    unit: str
    name: str
    preparation: str
    optional: bool = False
    confidence: float = 0.0
    exists_in_db: bool = False
    suggested_ingredient_id: Optional[int] = None


class AIIngredientParser:
    """
    AI-powered ingredient parsing service.
    
    Uses custom prompting to accurately parse recipe ingredients into
    structured components with high accuracy for cooking measurements.
    """
    
    INGREDIENT_PARSING_PROMPT = """You are an expert recipe ingredient parser. Parse each ingredient into these exact components:

RULES:
1. Extract QUANTITY as a decimal number (convert fractions: 1/2 = 0.5, 1 1/2 = 1.5)
2. Extract UNIT (cup, tablespoon, tsp, oz, pound, etc. - use standard abbreviations)
3. Extract NAME (the main ingredient without descriptors like "large", "fresh")
4. Extract PREPARATION (chopped, diced, minced, optional, etc.)
5. OPTIONAL: true if ingredient says "optional", "to taste", or similar

EXAMPLES:
Input: "2 1/2 cups all-purpose flour"
Output: {"quantity": 2.5, "unit": "cup", "name": "all-purpose flour", "preparation": "", "optional": false}

Input: "1 large onion, diced"  
Output: {"quantity": 1, "unit": "large", "name": "onion", "preparation": "diced", "optional": false}

Input: "3 tablespoons olive oil"
Output: {"quantity": 3, "unit": "tbsp", "name": "olive oil", "preparation": "", "optional": false}

Input: "Salt and pepper to taste"
Output: [
  {"quantity": 0, "unit": "", "name": "salt", "preparation": "to taste", "optional": true},
  {"quantity": 0, "unit": "", "name": "pepper", "preparation": "to taste", "optional": true}
]

Input: "2 pounds ground beef (85% lean)"
Output: {"quantity": 2, "unit": "lb", "name": "ground beef", "preparation": "85% lean", "optional": false}

Parse these ingredients and return valid JSON array:"""

    def __init__(self, ai_service: AIService, database_service: DatabaseService):
        self.ai_service = ai_service
        self.db = database_service
        
        # Load ingredient database for matching
        self._ingredient_cache = self._load_ingredient_cache()
    
    def parse_ingredients_with_ai(self, raw_ingredients: List[str]) -> List[ParsedIngredient]:
        """
        Parse raw ingredient strings using AI with database matching.
        
        Args:
            raw_ingredients: List of raw ingredient strings
            
        Returns:
            List of ParsedIngredient objects with database matching
        """
        if not self.ai_service.is_ai_available():
            logger.warning("AI not available, falling back to basic parsing")
            return self._fallback_parse_ingredients(raw_ingredients)
        
        parsed_ingredients = []
        
        # Process ingredients in batches for better AI accuracy
        batch_size = 10
        for i in range(0, len(raw_ingredients), batch_size):
            batch = raw_ingredients[i:i + batch_size]
            batch_results = self._parse_ingredient_batch(batch)
            parsed_ingredients.extend(batch_results)
        
        # Match with database ingredients
        for ingredient in parsed_ingredients:
            self._match_with_database(ingredient)
        
        return parsed_ingredients
    
    def _parse_ingredient_batch(self, ingredient_batch: List[str]) -> List[ParsedIngredient]:
        """Parse a batch of ingredients using AI"""
        try:
            # Create AI prompt
            ingredients_text = "\n".join([f"{i+1}. {ing}" for i, ing in enumerate(ingredient_batch)])
            full_prompt = f"{self.INGREDIENT_PARSING_PROMPT}\n\n{ingredients_text}"
            
            # Get AI response
            response = self.ai_service.get_completion(
                prompt=full_prompt,
                max_tokens=2000,
                temperature=0.1  # Low temperature for consistent parsing
            )
            
            if not response:
                logger.warning("No AI response received, falling back")
                return self._fallback_parse_ingredients(ingredient_batch)
            
            # Parse JSON response
            try:
                parsed_data = json.loads(response)
                if not isinstance(parsed_data, list):
                    parsed_data = [parsed_data]
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI JSON response: {e}")
                return self._fallback_parse_ingredients(ingredient_batch)
            
            # Convert to ParsedIngredient objects
            results = []
            for i, ingredient_data in enumerate(parsed_data):
                if i < len(ingredient_batch):  # Make sure we don't exceed batch
                    original_text = ingredient_batch[i]
                    parsed_ingredient = self._create_parsed_ingredient(original_text, ingredient_data)
                    results.append(parsed_ingredient)
            
            return results
            
        except Exception as e:
            logger.error(f"AI ingredient parsing failed: {e}")
            return self._fallback_parse_ingredients(ingredient_batch)
    
    def _create_parsed_ingredient(self, original_text: str, ai_data: Dict[str, Any]) -> ParsedIngredient:
        """Create ParsedIngredient from AI response data"""
        return ParsedIngredient(
            original_text=original_text,
            quantity=float(ai_data.get('quantity', 0.0)),
            unit=str(ai_data.get('unit', '')).strip(),
            name=str(ai_data.get('name', '')).strip(),
            preparation=str(ai_data.get('preparation', '')).strip(),
            optional=bool(ai_data.get('optional', False)),
            confidence=0.9  # High confidence for AI parsing
        )
    
    def _match_with_database(self, ingredient: ParsedIngredient):
        """Match parsed ingredient with database entries"""
        if not ingredient.name:
            return
        
        # Look for exact matches first
        exact_matches = [ing for ing in self._ingredient_cache if ing['name'].lower() == ingredient.name.lower()]
        if exact_matches:
            ingredient.exists_in_db = True
            ingredient.suggested_ingredient_id = exact_matches[0]['id']
            return
        
        # Look for partial matches
        name_words = ingredient.name.lower().split()
        best_match = None
        best_score = 0
        
        for db_ingredient in self._ingredient_cache:
            db_name = db_ingredient['name'].lower()
            
            # Calculate match score
            score = 0
            for word in name_words:
                if word in db_name:
                    score += len(word) / len(db_name)
            
            if score > best_score and score > 0.3:  # Minimum 30% match
                best_score = score
                best_match = db_ingredient
        
        if best_match:
            ingredient.exists_in_db = True
            ingredient.suggested_ingredient_id = best_match['id']
            ingredient.confidence *= best_score  # Reduce confidence based on match quality
    
    def _fallback_parse_ingredients(self, raw_ingredients: List[str]) -> List[ParsedIngredient]:
        """Fallback parsing when AI is not available"""
        import re
        
        results = []
        for original_text in raw_ingredients:
            # Basic regex parsing as fallback
            ingredient = ParsedIngredient(
                original_text=original_text,
                quantity=0.0,
                unit="",
                name=original_text.strip(),
                preparation="",
                optional="optional" in original_text.lower() or "to taste" in original_text.lower(),
                confidence=0.3  # Lower confidence for fallback
            )
            
            # Basic quantity extraction
            quantity_match = re.match(r'^(\d+(?:\.\d+)?|\d+\s+\d+/\d+|\d+/\d+)', original_text)
            if quantity_match:
                quantity_str = quantity_match.group(1)
                try:
                    # Handle fractions
                    if '/' in quantity_str:
                        if ' ' in quantity_str:  # Mixed fraction like "1 1/2"
                            whole, frac = quantity_str.split(' ', 1)
                            num, den = frac.split('/')
                            ingredient.quantity = int(whole) + (int(num) / int(den))
                        else:  # Simple fraction like "1/2"
                            num, den = quantity_str.split('/')
                            ingredient.quantity = int(num) / int(den)
                    else:
                        ingredient.quantity = float(quantity_str)
                    
                    # Remove quantity from name
                    ingredient.name = original_text[len(quantity_match.group(0)):].strip()
                except:
                    pass
            
            # Match with database
            self._match_with_database(ingredient)
            results.append(ingredient)
        
        return results
    
    def _load_ingredient_cache(self) -> List[Dict[str, Any]]:
        """Load ingredient database for matching"""
        try:
            ingredients = self.db.get_all_ingredients()
            return [{'id': ing.id, 'name': ing.name, 'category': ing.category} for ing in ingredients]
        except Exception as e:
            logger.error(f"Failed to load ingredient cache: {e}")
            return []


# Convenience functions
def get_ai_ingredient_parser(ai_service: Optional[AIService] = None, 
                           database_service: Optional[DatabaseService] = None) -> AIIngredientParser:
    """Get AI ingredient parser instance"""
    if ai_service is None:
        from services.ai_service import get_ai_service
        ai_service = get_ai_service()
    
    if database_service is None:
        from services.database_service import get_database_service
        database_service = get_database_service()
    
    return AIIngredientParser(ai_service, database_service)