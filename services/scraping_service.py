"""
Web scraping service for Pans Cookbook application.

Traditional HTML parsing approach with BeautifulSoup and structured selectors.
Includes robots.txt compliance, rate limiting, and comprehensive error handling.
Adapted from Herbalism app scraper patterns with recipe-specific enhancements.
"""

import requests
import time
import logging
import re
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from pathlib import Path

from models import ScrapedRecipe, ParsedRecipe, ScrapingResult
from utils import get_config, get_logger

logger = get_logger(__name__)


class ScrapingService:
    """
    Traditional web scraping service for recipe data extraction.
    
    Uses structured HTML selectors and BeautifulSoup for reliable parsing
    without AI dependencies. Includes comprehensive rate limiting and
    robots.txt compliance.
    """
    
    def __init__(self):
        self.config = get_config()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PansCookbook/1.0 (+https://panscookbook.com/bot)'
        })
        
        # Rate limiting tracking
        self._last_request_times: Dict[str, datetime] = {}
        self._robots_cache: Dict[str, RobotFileParser] = {}
        
        # Load recipe site configurations
        self._site_configs = self._load_site_configs()
    
    def scrape_recipe_url(self, url: str, user_id: int = None) -> ScrapingResult:
        """
        Scrape a recipe from a URL with full validation and error handling.
        
        Args:
            url: Recipe URL to scrape
            user_id: User requesting the scrape (for logging)
            
        Returns:
            ScrapingResult with success status and extracted data
        """
        result = ScrapingResult(success=False, url=url)
        start_time = time.time()
        
        try:
            # Step 1: Validate URL
            if not self._is_valid_url(url):
                result.add_error("Invalid URL format", "validation")
                return result
            
            # Step 2: Check robots.txt
            if not self._check_robots_txt(url):
                result.add_error("Scraping disallowed by robots.txt", "robots")
                return result
            
            result.robots_txt_allowed = True
            
            # Step 3: Apply rate limiting
            self._apply_rate_limiting(url)
            
            # Step 4: Fetch HTML content
            html_content = self._fetch_html(url)
            if not html_content:
                result.add_error("Failed to retrieve HTML content", "fetch")
                return result
            
            result.html_retrieved = True
            
            # Step 5: Parse recipe data
            scraped_recipe = self._parse_recipe_html(url, html_content)
            if not scraped_recipe:
                result.add_error("Failed to parse recipe data from HTML", "parsing")
                return result
            
            result.scraped_recipe = scraped_recipe
            result.parsing_attempted = True
            
            # Step 6: Validate minimum data requirements
            if not scraped_recipe.has_minimum_data():
                result.add_error("Insufficient recipe data extracted", "validation")
                result.add_warning("Recipe may need manual review")
            
            result.success = True
            logger.info(f"Successfully scraped recipe: {scraped_recipe.title}")
            
        except Exception as e:
            result.add_error(f"Unexpected error during scraping: {str(e)}", "exception")
            logger.error(f"Scraping error for {url}: {e}")
        
        finally:
            result.scraping_duration_seconds = time.time() - start_time
        
        return result
    
    def _check_robots_txt(self, url: str) -> bool:
        """Check if scraping is allowed by robots.txt"""
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Check cache first
            if base_url in self._robots_cache:
                rp = self._robots_cache[base_url]
            else:
                # Fetch and parse robots.txt
                robots_url = urljoin(base_url, "/robots.txt")
                rp = RobotFileParser()
                rp.set_url(robots_url)
                
                try:
                    rp.read()
                    self._robots_cache[base_url] = rp
                except Exception as e:
                    logger.warning(f"Could not read robots.txt for {base_url}: {e}")
                    # Fail safely - assume allowed if robots.txt can't be read
                    return True
            
            # Check if our user agent can fetch the URL
            user_agent = self.session.headers.get('User-Agent', '*')
            allowed = rp.can_fetch(user_agent, url)
            
            if not allowed:
                logger.info(f"Scraping disallowed by robots.txt: {url}")
            
            return allowed
            
        except Exception as e:
            logger.error(f"Error checking robots.txt: {e}")
            # Fail safely - assume allowed on error
            return True
    
    def _apply_rate_limiting(self, url: str):
        """Apply rate limiting based on domain"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Check when we last accessed this domain
        if domain in self._last_request_times:
            time_since_last = datetime.now() - self._last_request_times[domain]
            min_delay = timedelta(seconds=self.config.scraping_delay_seconds)
            
            if time_since_last < min_delay:
                sleep_time = (min_delay - time_since_last).total_seconds()
                logger.info(f"Rate limiting: sleeping {sleep_time:.1f}s for {domain}")
                time.sleep(sleep_time)
        
        # Update last request time
        self._last_request_times[domain] = datetime.now()
    
    def _fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL with error handling"""
        try:
            response = self.session.get(
                url,
                timeout=self.config.scraping_timeout_seconds,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'html' not in content_type:
                logger.warning(f"Non-HTML content type: {content_type}")
                return None
            
            return response.text
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            return None
    
    def _parse_recipe_html(self, url: str, html_content: str) -> Optional[ScrapedRecipe]:
        """Parse recipe data from HTML using structured selectors"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Determine site-specific configuration
            site_config = self._get_site_config(url)
            
            # Extract recipe data using selectors
            recipe_data = {
                'url': url,
                'scraped_at': datetime.now(),
                'scraping_method': site_config.get('name', 'generic'),
                'confidence_score': 0.5
            }
            
            # Title extraction
            recipe_data['title'] = self._extract_title(soup, site_config)
            
            # Description extraction
            recipe_data['description'] = self._extract_description(soup, site_config)
            
            # Ingredients extraction
            recipe_data['ingredients_raw'] = self._extract_ingredients(soup, site_config)
            
            # Instructions extraction
            recipe_data['instructions_raw'] = self._extract_instructions(soup, site_config)
            
            # Time information
            recipe_data['prep_time_text'] = self._extract_prep_time(soup, site_config)
            recipe_data['cook_time_text'] = self._extract_cook_time(soup, site_config)
            recipe_data['total_time_text'] = self._extract_total_time(soup, site_config)
            
            # Servings
            recipe_data['servings_text'] = self._extract_servings(soup, site_config)
            
            # Additional metadata
            recipe_data['cuisine_text'] = self._extract_cuisine(soup, site_config)
            recipe_data['category_text'] = self._extract_category(soup, site_config)
            recipe_data['difficulty_text'] = self._extract_difficulty(soup, site_config)
            recipe_data['rating_text'] = self._extract_rating(soup, site_config)
            recipe_data['nutrition_raw'] = self._extract_nutrition(soup, site_config)
            
            # Create scraped recipe object
            scraped_recipe = ScrapedRecipe(**recipe_data)
            
            # Calculate confidence score based on extracted data
            scraped_recipe.confidence_score = self._calculate_confidence(scraped_recipe)
            
            return scraped_recipe
            
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return None
    
    def _get_site_config(self, url: str) -> Dict[str, Any]:
        """Get site-specific configuration for parsing"""
        domain = urlparse(url).netloc.lower()
        
        # Remove www prefix for matching
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Check for exact match first
        if domain in self._site_configs:
            return self._site_configs[domain]
        
        # Check for partial matches (subdomains)
        for config_domain, config in self._site_configs.items():
            if domain.endswith(config_domain):
                return config
        
        # Return generic configuration
        return self._site_configs.get('generic', {})
    
    def _extract_title(self, soup: BeautifulSoup, site_config: Dict) -> str:
        """Extract recipe title using prioritized selectors"""
        selectors = site_config.get('title_selectors', [
            '[itemProp="name"]',
            '.recipe-title',
            '.entry-title',
            'h1.recipe',
            'h1',
            'title'
        ])
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element and element.get_text(strip=True):
                    return element.get_text(strip=True)
            except Exception:
                continue
        
        return ""
    
    def _extract_description(self, soup: BeautifulSoup, site_config: Dict) -> str:
        """Extract recipe description"""
        selectors = site_config.get('description_selectors', [
            '[itemProp="description"]',
            '.recipe-description',
            '.recipe-summary',
            '.entry-summary',
            'meta[name="description"]'
        ])
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    if element.name == 'meta':
                        text = element.get('content', '').strip()
                    else:
                        text = element.get_text(strip=True)
                    
                    if text and len(text) > 10:  # Reasonable minimum length
                        return text
            except Exception:
                continue
        
        return ""
    
    def _extract_ingredients(self, soup: BeautifulSoup, site_config: Dict) -> List[str]:
        """Extract ingredients list"""
        selectors = site_config.get('ingredients_selectors', [
            '[itemProp="recipeIngredient"]',
            '.recipe-ingredient',
            '.ingredient',
            'ul.ingredients li',
            '.ingredients li'
        ])
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    ingredients = []
                    for element in elements:
                        text = element.get_text(strip=True)
                        if text and len(text) > 2:  # Filter out empty or too-short items
                            ingredients.append(text)
                    
                    if len(ingredients) >= 2:  # Need at least 2 ingredients
                        return ingredients
            except Exception:
                continue
        
        return []
    
    def _extract_instructions(self, soup: BeautifulSoup, site_config: Dict) -> str:
        """Extract cooking instructions"""
        selectors = site_config.get('instructions_selectors', [
            '[itemProp="recipeInstructions"]',
            '.recipe-instructions',
            '.instructions',
            '.method',
            '.directions'
        ])
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    # Handle both single element and list of steps
                    instructions = []
                    
                    for element in elements:
                        text = element.get_text(strip=True)
                        if text:
                            instructions.append(text)
                    
                    if instructions:
                        combined = '\n'.join(instructions)
                        if len(combined) > 20:  # Minimum reasonable length
                            return combined
            except Exception:
                continue
        
        return ""
    
    def _extract_prep_time(self, soup: BeautifulSoup, site_config: Dict) -> str:
        """Extract preparation time"""
        return self._extract_time_field(soup, site_config, 'prep_time', 'prepTime')
    
    def _extract_cook_time(self, soup: BeautifulSoup, site_config: Dict) -> str:
        """Extract cooking time"""
        return self._extract_time_field(soup, site_config, 'cook_time', 'cookTime')
    
    def _extract_total_time(self, soup: BeautifulSoup, site_config: Dict) -> str:
        """Extract total time"""
        return self._extract_time_field(soup, site_config, 'total_time', 'totalTime')
    
    def _extract_time_field(self, soup: BeautifulSoup, site_config: Dict, 
                          field_name: str, itemprop: str) -> str:
        """Extract time field with multiple selector strategies"""
        selectors = site_config.get(f'{field_name}_selectors', [
            f'[itemProp="{itemprop}"]',
            f'.{field_name.replace("_", "-")}',
            f'.recipe-{field_name.replace("_", "-")}',
            f'time[datetime]'
        ])
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    # Check for datetime attribute first
                    datetime_attr = element.get('datetime')
                    if datetime_attr:
                        return datetime_attr
                    
                    # Fall back to text content
                    text = element.get_text(strip=True)
                    if text and ('min' in text.lower() or 'hour' in text.lower() or ':' in text):
                        return text
            except Exception:
                continue
        
        return ""
    
    def _extract_servings(self, soup: BeautifulSoup, site_config: Dict) -> str:
        """Extract number of servings"""
        selectors = site_config.get('servings_selectors', [
            '[itemProp="recipeYield"]',
            '.recipe-yield',
            '.servings',
            '.serves'
        ])
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    # Look for numbers in the text
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        return text
            except Exception:
                continue
        
        return ""
    
    def _extract_cuisine(self, soup: BeautifulSoup, site_config: Dict) -> str:
        """Extract cuisine type"""
        selectors = site_config.get('cuisine_selectors', [
            '[itemProp="recipeCuisine"]',
            '.recipe-cuisine',
            '.cuisine'
        ])
        
        return self._extract_simple_field(soup, selectors)
    
    def _extract_category(self, soup: BeautifulSoup, site_config: Dict) -> str:
        """Extract recipe category"""
        selectors = site_config.get('category_selectors', [
            '[itemProp="recipeCategory"]',
            '.recipe-category',
            '.category'
        ])
        
        return self._extract_simple_field(soup, selectors)
    
    def _extract_difficulty(self, soup: BeautifulSoup, site_config: Dict) -> str:
        """Extract difficulty level"""
        selectors = site_config.get('difficulty_selectors', [
            '.difficulty',
            '.recipe-difficulty',
            '.level'
        ])
        
        return self._extract_simple_field(soup, selectors)
    
    def _extract_rating(self, soup: BeautifulSoup, site_config: Dict) -> str:
        """Extract recipe rating"""
        selectors = site_config.get('rating_selectors', [
            '[itemProp="ratingValue"]',
            '.rating',
            '.stars'
        ])
        
        return self._extract_simple_field(soup, selectors)
    
    def _extract_nutrition(self, soup: BeautifulSoup, site_config: Dict) -> Dict[str, Any]:
        """Extract nutrition information"""
        nutrition = {}
        
        nutrition_selectors = {
            'calories': '[itemProp="calories"], .calories',
            'protein': '[itemProp="proteinContent"], .protein',
            'carbs': '[itemProp="carbohydrateContent"], .carbs, .carbohydrates',
            'fat': '[itemProp="fatContent"], .fat',
            'fiber': '[itemProp="fiberContent"], .fiber',
            'sodium': '[itemProp="sodiumContent"], .sodium'
        }
        
        for nutrient, selector in nutrition_selectors.items():
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text and any(char.isdigit() for char in text):
                        nutrition[nutrient] = text
            except Exception:
                continue
        
        return nutrition
    
    def _extract_simple_field(self, soup: BeautifulSoup, selectors: List[str]) -> str:
        """Extract simple text field using selector list"""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text:
                        return text
            except Exception:
                continue
        
        return ""
    
    def _calculate_confidence(self, scraped_recipe: ScrapedRecipe) -> float:
        """Calculate confidence score based on extracted data completeness"""
        score = 0.0
        max_score = 10.0
        
        # Essential fields
        if scraped_recipe.title:
            score += 3.0
        if scraped_recipe.ingredients_raw and len(scraped_recipe.ingredients_raw) >= 2:
            score += 3.0
        if scraped_recipe.instructions_raw and len(scraped_recipe.instructions_raw) >= 50:
            score += 2.0
        
        # Optional but valuable fields
        if scraped_recipe.description:
            score += 0.5
        if scraped_recipe.prep_time_text or scraped_recipe.cook_time_text:
            score += 0.5
        if scraped_recipe.servings_text:
            score += 0.5
        if scraped_recipe.cuisine_text:
            score += 0.3
        if scraped_recipe.category_text:
            score += 0.2
        
        return min(score / max_score, 1.0)
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format and scheme"""
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except Exception:
            return False
    
    def _load_site_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load site-specific parsing configurations"""
        # This could be loaded from a JSON file in production
        return {
            'generic': {
                'name': 'generic',
                'confidence_modifier': 0.0
            },
            'allrecipes.com': {
                'name': 'AllRecipes',
                'confidence_modifier': 0.2,
                'title_selectors': ['h1.recipe-summary__h1'],
                'ingredients_selectors': ['.recipe-ingred_txt'],
                'instructions_selectors': ['.recipe-directions__list--item']
            },
            'foodnetwork.com': {
                'name': 'Food Network',
                'confidence_modifier': 0.2,
                'title_selectors': ['.o-AssetTitle__a-HeadlineText'],
                'ingredients_selectors': ['.o-RecipeIngredient__a-Ingredient'],
                'instructions_selectors': ['.o-Method__m-Step']
            },
            'epicurious.com': {
                'name': 'Epicurious',
                'confidence_modifier': 0.1,
                'ingredients_selectors': ['[data-testid="IngredientList"] li'],
                'instructions_selectors': ['[data-testid="InstructionsWrapper"] li']
            }
        }


def get_scraping_service() -> ScrapingService:
    """Get singleton scraping service instance"""
    global _scraping_service
    if '_scraping_service' not in globals():
        globals()['_scraping_service'] = ScrapingService()
    return globals()['_scraping_service']