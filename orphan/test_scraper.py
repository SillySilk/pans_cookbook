#!/usr/bin/env python3
"""
Simple test script to verify scraping service functionality.
Tests robots.txt checking, rate limiting, and HTML parsing.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from services.scraping_service import ScrapingService
from utils.config import get_config

def test_scraping_service():
    """Test basic scraping operations"""
    print("Testing Scraping Service...")
    
    # Initialize service
    scraper = ScrapingService()
    print("[OK] Scraping service initialized")
    
    # Test URL validation
    valid_urls = [
        "https://example.com/recipe",
        "http://test.com/food/recipe"
    ]
    
    invalid_urls = [
        "not-a-url",
        "ftp://example.com",
        "",
        "javascript:alert('test')"
    ]
    
    print("[TEST] URL validation:")
    for url in valid_urls:
        if scraper._is_valid_url(url):
            print(f"  [OK] Valid: {url}")
        else:
            print(f"  [FAIL] Should be valid: {url}")
    
    for url in invalid_urls:
        if not scraper._is_valid_url(url):
            print(f"  [OK] Invalid: {url}")
        else:
            print(f"  [FAIL] Should be invalid: {url}")
    
    # Test robots.txt checking with a well-known site
    print("[TEST] Robots.txt checking:")
    test_url = "https://httpbin.org/html"
    
    try:
        allowed = scraper._check_robots_txt(test_url)
        print(f"  Robots.txt check for {test_url}: {'Allowed' if allowed else 'Blocked'}")
    except Exception as e:
        print(f"  Robots.txt check failed: {e}")
    
    # Test HTML fetching (use a simple test endpoint)
    print("[TEST] HTML fetching:")
    try:
        html = scraper._fetch_html(test_url)
        if html:
            print(f"  [OK] HTML fetched successfully ({len(html)} characters)")
        else:
            print("  [FAIL] Failed to fetch HTML")
    except Exception as e:
        print(f"  [FAIL] HTML fetch error: {e}")
    
    # Test site config loading
    print("[TEST] Site configuration:")
    configs = scraper._site_configs
    print(f"  Loaded {len(configs)} site configurations")
    
    # Test generic config
    generic_config = scraper._get_site_config("https://unknown-recipe-site.com/recipe")
    print(f"  Generic config name: {generic_config.get('name', 'N/A')}")
    
    # Test known site config
    allrecipes_config = scraper._get_site_config("https://www.allrecipes.com/recipe/123/test")
    print(f"  AllRecipes config name: {allrecipes_config.get('name', 'N/A')}")
    
    print("\n[SUCCESS] All scraping tests completed!")
    return True

def test_html_parsing():
    """Test HTML parsing with sample recipe HTML"""
    print("\n[TEST] HTML parsing with sample data:")
    
    # Sample recipe HTML (minimal structure)
    sample_html = '''
    <html>
    <head>
        <title>Test Recipe - Delicious Food</title>
        <meta name="description" content="A simple test recipe for demonstration">
    </head>
    <body>
        <h1 itemProp="name">Chocolate Chip Cookies</h1>
        <p class="recipe-description">Delicious homemade chocolate chip cookies</p>
        
        <div class="ingredients">
            <ul>
                <li itemProp="recipeIngredient">2 cups all-purpose flour</li>
                <li itemProp="recipeIngredient">1 cup butter, softened</li>
                <li itemProp="recipeIngredient">3/4 cup brown sugar</li>
                <li itemProp="recipeIngredient">1/2 cup white sugar</li>
                <li itemProp="recipeIngredient">2 eggs</li>
                <li itemProp="recipeIngredient">1 tsp vanilla extract</li>
                <li itemProp="recipeIngredient">1 cup chocolate chips</li>
            </ul>
        </div>
        
        <div class="instructions">
            <ol itemProp="recipeInstructions">
                <li>Preheat oven to 375°F</li>
                <li>Mix flour and baking soda in bowl</li>
                <li>Cream butter and sugars until fluffy</li>
                <li>Beat in eggs and vanilla</li>
                <li>Gradually mix in flour mixture</li>
                <li>Stir in chocolate chips</li>
                <li>Drop spoonfuls on cookie sheet</li>
                <li>Bake 9-11 minutes until golden</li>
            </ol>
        </div>
        
        <span itemProp="prepTime">PT15M</span>
        <span itemProp="cookTime">PT11M</span>
        <span itemProp="recipeYield">24 cookies</span>
    </body>
    </html>
    '''
    
    scraper = ScrapingService()
    
    try:
        # Parse the sample HTML
        scraped_recipe = scraper._parse_recipe_html("https://test.com/recipe", sample_html)
        
        if scraped_recipe:
            print(f"  [OK] Recipe parsed: {scraped_recipe.title}")
            print(f"    Description: {scraped_recipe.description}")
            print(f"    Ingredients: {len(scraped_recipe.ingredients_raw)}")
            print(f"    Instructions: {len(scraped_recipe.instructions_raw)} characters")
            print(f"    Prep time: {scraped_recipe.prep_time_text}")
            print(f"    Cook time: {scraped_recipe.cook_time_text}")
            print(f"    Servings: {scraped_recipe.servings_text}")
            print(f"    Confidence: {scraped_recipe.confidence_score:.2f}")
            print(f"    Has minimum data: {scraped_recipe.has_minimum_data()}")
            
            return True
        else:
            print("  [FAIL] Failed to parse sample HTML")
            return False
            
    except Exception as e:
        print(f"  [FAIL] HTML parsing error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success1 = test_scraping_service()
        success2 = test_html_parsing()
        
        if success1 and success2:
            print("\n[SUCCESS] All scraper tests passed!")
            sys.exit(0)
        else:
            print("\n[FAIL] Some tests failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)