#!/usr/bin/env python3
"""
Test script for recipe parsing and validation service.
Tests parsing of scraped recipe data and validation logic.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from services.parsing_service import ParsingService
from services.database_service import DatabaseService
from models import ScrapedRecipe
from datetime import datetime

def create_sample_scraped_recipe() -> ScrapedRecipe:
    """Create sample scraped recipe for testing"""
    return ScrapedRecipe(
        url="https://test.com/chocolate-chip-cookies",
        title="Best Chocolate Chip Cookies - Recipe Site",
        description="These are the most amazing chocolate chip cookies you'll ever make!",
        ingredients_raw=[
            "2 1/4 cups all-purpose flour",
            "1 tsp baking soda",
            "1 cup butter, softened",
            "3/4 cup granulated sugar", 
            "3/4 cup packed brown sugar",
            "2 large eggs",
            "2 tsp vanilla extract",
            "2 cups chocolate chips",
            "1 tsp salt (optional)"
        ],
        instructions_raw="""1. Preheat oven to 375°F (190°C).
2. In medium bowl, mix flour, baking soda and salt; set aside.
3. In large bowl, beat butter and sugars with electric mixer until light and fluffy.
4. Beat in eggs one at a time, then vanilla.
5. Gradually beat in flour mixture until just combined.
6. Stir in chocolate chips.
7. Drop rounded tablespoons of dough onto ungreased cookie sheets.
8. Bake 9 to 11 minutes or until golden brown.
9. Cool on baking sheet 2 minutes; remove to wire rack.""",
        prep_time_text="15 minutes",
        cook_time_text="11 minutes",
        total_time_text="",
        servings_text="48 cookies",
        cuisine_text="American",
        category_text="Dessert",
        difficulty_text="Easy",
        rating_text="4.5 stars",
        confidence_score=0.9,
        scraped_at=datetime.now(),
        scraping_method="test_data"
    )

def test_parsing_service():
    """Test basic parsing operations"""
    print("Testing Recipe Parsing Service...")
    
    # Initialize services with in-memory database
    db = DatabaseService(":memory:")
    parser = ParsingService(db)
    print("[OK] Parsing service initialized")
    
    # Create sample scraped recipe
    scraped = create_sample_scraped_recipe()
    print(f"[OK] Sample recipe created: {scraped.title}")
    
    # Test recipe parsing
    parsed = parser.parse_scraped_recipe(scraped)
    print(f"[OK] Recipe parsed: {parsed.title}")
    
    # Validate parsing results
    print("[TEST] Parsing results:")
    print(f"  Title: {parsed.title}")
    print(f"  Prep time: {parsed.prep_time_minutes} minutes")
    print(f"  Cook time: {parsed.cook_time_minutes} minutes") 
    print(f"  Servings: {parsed.servings}")
    print(f"  Difficulty: {parsed.difficulty_level}")
    print(f"  Cuisine: {parsed.cuisine_type}")
    print(f"  Category: {parsed.meal_category}")
    print(f"  Dietary tags: {parsed.dietary_tags}")
    print(f"  Ingredients: {len(parsed.ingredients)}")
    print(f"  Parsing issues: {len(parsed.parsing_issues)}")
    
    # Test ingredient parsing
    print("[TEST] Sample ingredients:")
    for i, ingredient in enumerate(parsed.ingredients[:3]):
        print(f"  {i+1}. {ingredient['quantity']} {ingredient['unit']} {ingredient['name']}")
        if ingredient['preparation']:
            print(f"     Prep: {ingredient['preparation']}")
    
    # Test validation
    validation_result = parser.validate_parsed_recipe(parsed)
    print(f"[TEST] Validation result: {'PASS' if validation_result.is_valid else 'FAIL'}")
    
    if not validation_result.is_valid:
        print("  Validation errors:")
        for error in validation_result.get_all_errors():
            print(f"    - {error}")
    
    if validation_result.safety_warnings:
        print("  Safety warnings:")
        for warning in validation_result.safety_warnings:
            print(f"    - {warning}")
    
    return True

def test_time_parsing():
    """Test time parsing functionality"""
    print("\n[TEST] Time parsing:")
    
    parser = ParsingService(DatabaseService(":memory:"))
    
    test_times = [
        ("15 minutes", 15),
        ("1 hour 30 minutes", 90),
        ("2 hrs", 120),
        ("PT15M", 15),
        ("PT1H30M", 90),
        ("45 min", 45),
        ("1:30", 90),
        ("2.5 hours", 150),
    ]
    
    for time_text, expected in test_times:
        result = parser._parse_time_to_minutes(time_text)
        status = "OK" if result == expected else "FAIL"
        print(f"  [{status}] '{time_text}' -> {result} min (expected {expected})")
    
    return True

def test_ingredient_parsing():
    """Test ingredient parsing functionality"""
    print("\n[TEST] Ingredient parsing:")
    
    parser = ParsingService(DatabaseService(":memory:"))
    
    test_ingredients = [
        "2 cups all-purpose flour",
        "1 tsp vanilla extract",
        "1/2 cup butter, softened",
        "3 large eggs",
        "2 1/4 cups sugar",
        "1 medium onion, diced",
        "Salt to taste (optional)"
    ]
    
    for ingredient_text in test_ingredients:
        parsed = parser._parse_single_ingredient(ingredient_text, 1)
        print(f"  '{ingredient_text}'")
        print(f"    Quantity: {parsed['quantity']}, Unit: {parsed['unit']}")
        print(f"    Name: {parsed['name']}, Prep: {parsed['preparation']}")
        print(f"    Optional: {parsed['optional']}")
    
    return True

def test_ingredient_matching():
    """Test ingredient matching against database"""
    print("\n[TEST] Ingredient matching:")
    
    # Use database with some sample ingredients
    db = DatabaseService(":memory:")
    
    # Add some test ingredients
    db.create_ingredient("All-Purpose Flour", "grain")
    db.create_ingredient("Vanilla Extract", "flavoring")
    db.create_ingredient("Butter", "dairy")
    db.create_ingredient("Large Eggs", "protein")
    
    parser = ParsingService(db)
    
    test_queries = [
        "flour",
        "vanilla",
        "eggs",
        "unknown ingredient"
    ]
    
    for query in test_queries:
        matches = parser.suggest_ingredient_matches(query, max_suggestions=3)
        print(f"  Query: '{query}'")
        if matches:
            for ingredient, confidence in matches:
                print(f"    - {ingredient.name} ({confidence:.2f})")
        else:
            print(f"    - No matches found")
    
    return True

if __name__ == "__main__":
    try:
        success1 = test_parsing_service()
        success2 = test_time_parsing()
        success3 = test_ingredient_parsing() 
        success4 = test_ingredient_matching()
        
        if all([success1, success2, success3, success4]):
            print("\n[SUCCESS] All parsing tests passed!")
            sys.exit(0)
        else:
            print("\n[FAIL] Some tests failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)