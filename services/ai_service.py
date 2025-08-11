"""
AI integration service for Pans Cookbook application.

Provides AI-powered features with primary focus on LM Studio local integration
for scraping assistance and recipe enhancements. Designed to gracefully handle
AI unavailability and provide optional external API integration in the future.
"""

import json
import logging
import requests
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from enum import Enum

from models import Recipe, Ingredient, ParsedRecipe
from services.database_service import DatabaseService, get_database_service
from utils import get_logger, get_config

logger = get_logger(__name__)


class AIProvider(Enum):
    """Supported AI providers"""
    LM_STUDIO = "lm_studio"
    OPENAI = "openai"  # Future enhancement
    ANTHROPIC = "anthropic"  # Future enhancement


class AIService:
    """
    AI integration service with local LM Studio focus.
    
    Provides AI-powered recipe enhancement, scraping assistance, and ingredient
    suggestions using primarily local LM Studio with optional external API support
    for future enhancements.
    """
    
    def __init__(self, database_service: Optional[DatabaseService] = None):
        self.db = database_service or get_database_service()
        self.config = get_config()
        
        # LM Studio configuration (default local setup)
        self.lm_studio_config = {
            'base_url': getattr(self.config, 'lm_studio_url', 'http://localhost:1234/v1'),
            'timeout': getattr(self.config, 'ai_timeout_seconds', 30),
            'max_retries': getattr(self.config, 'ai_max_retries', 2)
        }
        
        # Track AI availability status
        self._ai_available = None
        self._last_health_check = None
        self._health_check_interval = 300  # 5 minutes
        
        # Future external API configurations (placeholder for future enhancement)
        self._external_apis_enabled = False
        
    def is_ai_available(self, force_check: bool = False) -> bool:
        """
        Check if AI services are available (primarily LM Studio).
        
        Args:
            force_check: Force a new health check even if cached result exists
            
        Returns:
            True if AI services are available and responsive
        """
        now = datetime.now()
        
        # Use cached result if recent and not forcing check
        if (not force_check and self._ai_available is not None and 
            self._last_health_check and 
            (now - self._last_health_check).seconds < self._health_check_interval):
            return self._ai_available
        
        # Check LM Studio health
        self._ai_available = self._check_lm_studio_health()
        self._last_health_check = now
        
        if self._ai_available:
            logger.info("AI services available (LM Studio connected)")
        else:
            logger.warning("AI services unavailable (LM Studio not responding)")
        
        return self._ai_available
    
    def _check_lm_studio_health(self) -> bool:
        """Check if LM Studio is running and responsive"""
        try:
            health_url = f"{self.lm_studio_config['base_url']}/models"
            response = requests.get(
                health_url, 
                timeout=5,  # Quick health check
                headers={'Content-Type': 'application/json'}
            )
            return response.status_code == 200
            
        except Exception as e:
            logger.debug(f"LM Studio health check failed: {e}")
            return False
    
    def enhance_scraping_with_ai(self, raw_html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Use AI to enhance scraping results from raw HTML.
        
        Particularly useful for complex or non-standard recipe sites where
        traditional parsing may miss information.
        
        Args:
            raw_html: Raw HTML content from scraped page
            url: Source URL for context
            
        Returns:
            Dictionary with enhanced recipe data or None if AI unavailable
        """
        if not self.is_ai_available():
            logger.info("AI enhancement unavailable, falling back to traditional parsing")
            return None
        
        try:
            prompt = self._create_scraping_enhancement_prompt(raw_html, url)
            response = self._call_lm_studio(prompt, max_tokens=1000)
            
            if response:
                return self._parse_scraping_response(response)
            
        except Exception as e:
            logger.warning(f"AI scraping enhancement failed: {e}")
            
        return None
    
    def suggest_ingredients_for_recipe(self, recipe: ParsedRecipe, 
                                     pantry_ingredients: List[str] = None) -> List[str]:
        """
        Suggest additional or substitute ingredients for a recipe.
        
        Args:
            recipe: Recipe to analyze
            pantry_ingredients: User's available ingredients for substitution suggestions
            
        Returns:
            List of suggested ingredient names
        """
        if not self.is_ai_available():
            logger.info("AI suggestions unavailable")
            return []
        
        try:
            prompt = self._create_ingredient_suggestion_prompt(recipe, pantry_ingredients)
            response = self._call_lm_studio(prompt, max_tokens=500)
            
            if response:
                return self._parse_ingredient_suggestions(response)
            
        except Exception as e:
            logger.warning(f"AI ingredient suggestions failed: {e}")
        
        return []
    
    def improve_recipe_instructions(self, recipe: ParsedRecipe) -> Optional[str]:
        """
        Use AI to improve or clarify recipe instructions.
        
        Args:
            recipe: Recipe with instructions to improve
            
        Returns:
            Improved instructions string or None if AI unavailable
        """
        if not self.is_ai_available():
            return None
        
        try:
            prompt = self._create_instruction_improvement_prompt(recipe)
            response = self._call_lm_studio(prompt, max_tokens=800)
            
            if response:
                return self._parse_instruction_response(response)
                
        except Exception as e:
            logger.warning(f"AI instruction improvement failed: {e}")
        
        return None
    
    def extract_nutrition_estimates(self, recipe: ParsedRecipe) -> Optional[Dict[str, Any]]:
        """
        Use AI to estimate nutritional information for a recipe.
        
        Args:
            recipe: Recipe to analyze
            
        Returns:
            Dictionary with estimated nutrition data or None if unavailable
        """
        if not self.is_ai_available():
            return None
        
        try:
            prompt = self._create_nutrition_estimation_prompt(recipe)
            response = self._call_lm_studio(prompt, max_tokens=400)
            
            if response:
                return self._parse_nutrition_response(response)
                
        except Exception as e:
            logger.warning(f"AI nutrition estimation failed: {e}")
        
        return None
    
    def _call_lm_studio(self, prompt: str, max_tokens: int = 500, 
                       temperature: float = 0.3) -> Optional[str]:
        """
        Make API call to LM Studio local server.
        
        Args:
            prompt: Text prompt to send
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (lower = more focused)
            
        Returns:
            Response text or None if failed
        """
        try:
            url = f"{self.lm_studio_config['base_url']}/chat/completions"
            
            payload = {
                "model": "local-model",  # LM Studio uses this generic name
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful cooking and recipe assistant. Provide clear, accurate, and practical responses. Format responses as requested."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            
            response = requests.post(
                url,
                json=payload,
                timeout=self.lm_studio_config['timeout'],
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                return content.strip()
            else:
                logger.warning(f"LM Studio API returned status {response.status_code}")
                
        except Exception as e:
            logger.error(f"LM Studio API call failed: {e}")
        
        return None
    
    def _create_scraping_enhancement_prompt(self, html: str, url: str) -> str:
        """Create prompt for AI-enhanced scraping"""
        # Truncate HTML if too long
        html_snippet = html[:3000] if len(html) > 3000 else html
        
        return f"""
Analyze this recipe webpage HTML and extract structured recipe information:

URL: {url}
HTML Content: {html_snippet}

Please extract and return ONLY a JSON object with these fields:
{{
    "title": "recipe name",
    "description": "brief description",  
    "ingredients": ["ingredient 1", "ingredient 2"],
    "instructions": "step-by-step instructions",
    "prep_time": "15 minutes",
    "cook_time": "30 minutes", 
    "servings": "4",
    "cuisine": "cuisine type",
    "difficulty": "easy/medium/hard",
    "dietary_tags": ["vegetarian", "gluten-free"]
}}

Focus on accuracy and completeness. Return only valid JSON.
"""
    
    def _create_ingredient_suggestion_prompt(self, recipe: ParsedRecipe, 
                                           pantry_ingredients: List[str] = None) -> str:
        """Create prompt for ingredient suggestions"""
        pantry_text = ""
        if pantry_ingredients:
            pantry_text = f"\nAvailable ingredients: {', '.join(pantry_ingredients)}"
        
        ingredient_list = [ing.get('name', '') for ing in recipe.ingredients if ing.get('name')]
        
        return f"""
Recipe: {recipe.title}
Current ingredients: {', '.join(ingredient_list)}{pantry_text}

Suggest 3-5 additional ingredients that would complement this recipe or substitutes for ingredients the user doesn't have.
Focus on practical, commonly available ingredients.

Return only a JSON array of ingredient names:
["suggestion 1", "suggestion 2", "suggestion 3"]
"""
    
    def _create_instruction_improvement_prompt(self, recipe: ParsedRecipe) -> str:
        """Create prompt for instruction improvement"""
        return f"""
Recipe: {recipe.title}
Current instructions: {recipe.instructions}

Please improve these cooking instructions to be clearer, more detailed, and easier to follow.
Add helpful tips, timing guidance, and visual cues where appropriate.
Keep the same cooking method but make it more accessible for home cooks.

Return only the improved instructions as plain text.
"""
    
    def _create_nutrition_estimation_prompt(self, recipe: ParsedRecipe) -> str:
        """Create prompt for nutrition estimation"""
        ingredient_list = [ing.get('original_text', '') for ing in recipe.ingredients if ing.get('original_text')]
        
        return f"""
Recipe: {recipe.title}
Servings: {recipe.servings}
Ingredients: {'; '.join(ingredient_list)}

Estimate the nutritional information per serving for this recipe.
Return ONLY a JSON object:
{{
    "calories": 350,
    "protein_g": 25,
    "carbs_g": 30,
    "fat_g": 15,
    "fiber_g": 5,
    "sugar_g": 8
}}

Provide reasonable estimates based on typical ingredient nutritional values.
"""
    
    def _parse_scraping_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse AI response for scraping enhancement"""
        try:
            # Try to extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
                
        except Exception as e:
            logger.warning(f"Failed to parse scraping response: {e}")
        
        return None
    
    def _parse_ingredient_suggestions(self, response: str) -> List[str]:
        """Parse AI response for ingredient suggestions"""
        try:
            # Try to extract JSON array from response
            start = response.find('[')
            end = response.rfind(']') + 1
            
            if start >= 0 and end > start:
                json_str = response[start:end]
                suggestions = json.loads(json_str)
                return [s for s in suggestions if isinstance(s, str)]
                
        except Exception as e:
            logger.warning(f"Failed to parse ingredient suggestions: {e}")
        
        return []
    
    def _parse_instruction_response(self, response: str) -> Optional[str]:
        """Parse AI response for instruction improvement"""
        # For instructions, return the cleaned response directly
        return response.strip() if response and response.strip() else None
    
    def _parse_nutrition_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse AI response for nutrition estimation"""
        try:
            # Try to extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = response[start:end]
                nutrition = json.loads(json_str)
                
                # Validate numeric values
                for key, value in nutrition.items():
                    if not isinstance(value, (int, float)) or value < 0:
                        return None
                
                return nutrition
                
        except Exception as e:
            logger.warning(f"Failed to parse nutrition response: {e}")
        
        return None
    
    # Future enhancement methods (placeholder implementations)
    def _validate_external_api_key(self, provider: AIProvider, api_key: str) -> bool:
        """Validate external API key (future enhancement)"""
        logger.info(f"External API validation for {provider.value} - not yet implemented")
        return False
    
    def generate_recipe_variations(self, recipe: ParsedRecipe, api_key: str = None) -> List[Dict[str, Any]]:
        """Generate recipe variations (future enhancement)"""
        logger.info("Recipe variation generation - future enhancement")
        return []
    
    def get_ai_status(self) -> Dict[str, Any]:
        """Get comprehensive AI service status"""
        return {
            'lm_studio_available': self.is_ai_available(),
            'lm_studio_url': self.lm_studio_config['base_url'],
            'external_apis_enabled': self._external_apis_enabled,
            'last_health_check': self._last_health_check.isoformat() if self._last_health_check else None,
            'features_available': {
                'scraping_enhancement': self.is_ai_available(),
                'ingredient_suggestions': self.is_ai_available(),
                'instruction_improvement': self.is_ai_available(),
                'nutrition_estimation': self.is_ai_available(),
                'recipe_variations': False,  # Future enhancement
            }
        }


# Service factory function
def get_ai_service(database_service: Optional[DatabaseService] = None) -> AIService:
    """Factory function to get AI service instance"""
    return AIService(database_service)


# Convenience function for availability checking
def is_ai_available() -> bool:
    """Quick check if AI services are available"""
    service = get_ai_service()
    return service.is_ai_available()