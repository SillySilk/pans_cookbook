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
    
    def parse_recipe_text(self, text: str) -> Optional[ScrapedRecipe]:
        """
        Parse recipe text directly without web scraping.
        
        Args:
            text: Raw recipe text (from paste, file, etc.)
            
        Returns:
            ScrapedRecipe object or None if parsing fails
        """
        try:
            logger.info("Parsing recipe from text input")
            
            # Initialize scraped recipe with basic data
            scraped_recipe = ScrapedRecipe(
                url="text-input",
                title="Untitled Recipe",
                scraping_method="text_parsing",
                scraped_at=datetime.now(),
                confidence_score=0.5
            )
            
            # Parse the text using regex and text analysis
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Extract title (usually first line or line before "Ingredients:")
            title_line = None
            for i, line in enumerate(lines):
                # Look for a likely title - first substantial line or one before ingredients
                if (i == 0 and len(line) > 3 and not any(word in line.lower() for word in ['ingredient', 'instruction', 'step', 'prep', 'cook'])) or \
                   (i > 0 and i < len(lines) - 1 and 'ingredient' in lines[i + 1].lower() and len(line) > 3):
                    title_line = line
                    break
            
            if title_line:
                scraped_recipe.title = title_line.strip()
                scraped_recipe.confidence_score += 0.1
            
            # Extract ingredients section
            ingredients_start = -1
            ingredients_end = -1
            
            for i, line in enumerate(lines):
                if re.search(r'ingredients?:?', line, re.IGNORECASE) and len(line) < 30:
                    ingredients_start = i + 1
                elif ingredients_start >= 0 and re.search(r'(instructions?:?|directions?:?|method:?|steps?:?)', line, re.IGNORECASE):
                    ingredients_end = i
                    break
            
            if ingredients_start >= 0:
                ingredients_end = ingredients_end if ingredients_end > 0 else len(lines)
                ingredient_lines = lines[ingredients_start:ingredients_end]
                
                # Filter and clean ingredient lines
                ingredients = []
                for line in ingredient_lines:
                    # Skip empty lines and lines that look like headers
                    if line and not re.search(r'^(ingredients?:?|directions?:?|instructions?:?)$', line, re.IGNORECASE):
                        # Remove bullet points and numbers
                        clean_line = re.sub(r'^[-•*\d+\.)]\s*', '', line)
                        if clean_line and len(clean_line) > 2:
                            ingredients.append(clean_line)
                
                scraped_recipe.ingredients_raw = ingredients
                if ingredients:
                    scraped_recipe.confidence_score += 0.2
            
            # Extract instructions section
            instructions_start = -1
            for i, line in enumerate(lines):
                if re.search(r'(instructions?:?|directions?:?|method:?|steps?:?)', line, re.IGNORECASE) and len(line) < 30:
                    instructions_start = i + 1
                    break
            
            if instructions_start >= 0:
                instruction_lines = lines[instructions_start:]
                
                # Clean and join instructions
                instructions = []
                for line in instruction_lines:
                    if line and not re.search(r'^(prep:?|cook:?|total:?|serves?:?|yield:?)', line, re.IGNORECASE):
                        # Remove step numbers
                        clean_line = re.sub(r'^\d+[\.)]\s*', '', line)
                        if clean_line and len(clean_line) > 5:
                            instructions.append(clean_line)
                
                scraped_recipe.instructions_raw = '\n'.join(instructions)
                if instructions:
                    scraped_recipe.confidence_score += 0.1
            
            # Extract timing information
            full_text = text.lower()
            
            # Look for prep time
            prep_match = re.search(r'prep(?:\s+time)?:?\s*(\d+)\s*(?:min|minutes|hrs?|hours?)', full_text)
            if prep_match:
                scraped_recipe.prep_time_text = prep_match.group(0)
                scraped_recipe.confidence_score += 0.05
            
            # Look for cook time
            cook_match = re.search(r'cook(?:\s+time)?:?\s*(\d+)\s*(?:min|minutes|hrs?|hours?)', full_text)
            if cook_match:
                scraped_recipe.cook_time_text = cook_match.group(0)
                scraped_recipe.confidence_score += 0.05
            
            # Look for servings
            serves_match = re.search(r'(?:serves?|yield):?\s*(\d+)', full_text)
            if serves_match:
                scraped_recipe.servings_text = serves_match.group(0)
                scraped_recipe.confidence_score += 0.05
            
            # Look for description (lines after title but before ingredients)
            if ingredients_start > 1:
                potential_desc_lines = lines[1:ingredients_start]
                desc_lines = [line for line in potential_desc_lines 
                             if not re.search(r'(ingredients?:?|prep:?|cook:?|serves?:?)', line, re.IGNORECASE)]
                if desc_lines:
                    scraped_recipe.description = ' '.join(desc_lines)
                    scraped_recipe.confidence_score += 0.05
            
            logger.info(f"Text parsing completed with confidence: {scraped_recipe.confidence_score:.2f}")
            return scraped_recipe
            
        except Exception as e:
            logger.error(f"Failed to parse recipe text: {e}")
            return None
    
    def parse_html_content(self, html_content: str) -> Optional[ScrapedRecipe]:
        """
        Parse HTML content directly (from uploaded files).
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            ScrapedRecipe object or None if parsing fails
        """
        try:
            logger.info("Parsing recipe from HTML content")
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Initialize scraped recipe
            scraped_recipe = ScrapedRecipe(
                url="html-upload",
                title="Untitled Recipe",
                scraping_method="html_parsing",
                scraped_at=datetime.now(),
                confidence_score=0.4  # Start with decent confidence for HTML
            )
            
            # Try to extract recipe using JSON-LD structured data first
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    
                    if isinstance(data, list):
                        data = data[0]
                    
                    if data.get('@type') in ['Recipe', 'recipe']:
                        scraped_recipe.title = data.get('name', scraped_recipe.title)
                        scraped_recipe.description = data.get('description', '')
                        
                        # Extract ingredients
                        if 'recipeIngredient' in data:
                            scraped_recipe.ingredients_raw = data['recipeIngredient']
                            scraped_recipe.confidence_score += 0.3
                        
                        # Extract instructions
                        if 'recipeInstructions' in data:
                            instructions = []
                            for instruction in data['recipeInstructions']:
                                if isinstance(instruction, dict):
                                    instructions.append(instruction.get('text', ''))
                                else:
                                    instructions.append(str(instruction))
                            scraped_recipe.instructions_raw = '\n'.join(instructions)
                            scraped_recipe.confidence_score += 0.2
                        
                        # Extract timing
                        if 'prepTime' in data:
                            scraped_recipe.prep_time_text = data['prepTime']
                            scraped_recipe.confidence_score += 0.05
                        
                        if 'cookTime' in data:
                            scraped_recipe.cook_time_text = data['cookTime']
                            scraped_recipe.confidence_score += 0.05
                        
                        # Extract servings
                        if 'recipeYield' in data:
                            scraped_recipe.servings_text = str(data['recipeYield'])
                            scraped_recipe.confidence_score += 0.05
                        
                        logger.info(f"Successfully parsed JSON-LD recipe data with confidence: {scraped_recipe.confidence_score:.2f}")
                        return scraped_recipe
                        
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
            
            # Fallback to HTML parsing with common selectors
            # Title extraction
            title_selectors = ['h1', '.recipe-title', '.entry-title', '[itemprop="name"]', 'title']
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem and title_elem.get_text().strip():
                    scraped_recipe.title = title_elem.get_text().strip()
                    scraped_recipe.confidence_score += 0.1
                    break
            
            # Ingredients extraction
            ingredient_selectors = [
                '.recipe-ingredient', '.ingredients li', '[itemprop="recipeIngredient"]',
                '.ingredient', 'ul.ingredients li', '.recipe-ingredients li'
            ]
            ingredients = []
            for selector in ingredient_selectors:
                elements = soup.select(selector)
                if elements:
                    ingredients = [elem.get_text().strip() for elem in elements if elem.get_text().strip()]
                    if ingredients:
                        scraped_recipe.ingredients_raw = ingredients
                        scraped_recipe.confidence_score += 0.2
                        break
            
            # Instructions extraction
            instruction_selectors = [
                '.recipe-instruction', '.instructions li', '[itemprop="recipeInstructions"]',
                '.method li', '.directions li', '.recipe-directions li'
            ]
            for selector in instruction_selectors:
                elements = soup.select(selector)
                if elements:
                    instructions = [elem.get_text().strip() for elem in elements if elem.get_text().strip()]
                    if instructions:
                        scraped_recipe.instructions_raw = '\n'.join(instructions)
                        scraped_recipe.confidence_score += 0.1
                        break
            
            # Description extraction
            desc_selectors = ['.recipe-description', '.entry-content p', '[itemprop="description"]']
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem and desc_elem.get_text().strip():
                    scraped_recipe.description = desc_elem.get_text().strip()
                    scraped_recipe.confidence_score += 0.05
                    break
            
            # If we still don't have good data, try parsing as text
            if scraped_recipe.confidence_score < 0.5:
                text_content = soup.get_text()
                text_result = self.parse_recipe_text(text_content)
                if text_result and text_result.confidence_score > scraped_recipe.confidence_score:
                    return text_result
            
            logger.info(f"HTML parsing completed with confidence: {scraped_recipe.confidence_score:.2f}")
            return scraped_recipe
            
        except Exception as e:
            logger.error(f"Failed to parse HTML content: {e}")
            return None

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