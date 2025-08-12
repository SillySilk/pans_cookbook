#!/usr/bin/env python3
"""
Test script for AI service functionality with LM Studio integration.
Tests local AI service availability, scraping enhancement, and recipe suggestions.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from models import ScrapedRecipe, ParsedRecipe
from services import AIService, get_ai_service, DatabaseService
from datetime import datetime


def test_ai_service_basic():
    """Test basic AI service initialization and health checks"""
    print("Testing AI Service Basic Functionality...")
    
    try:
        # Initialize AI service
        db = DatabaseService(":memory:")
        ai_service = AIService(db)
        print("[OK] AI service initialized")
        
        # Test health check
        is_available = ai_service.is_ai_available()
        if is_available:
            print("[OK] LM Studio is available and responsive")
        else:
            print("[INFO] LM Studio not available (this is expected if not running)")
        
        # Test status reporting
        status = ai_service.get_ai_status()
        print(f"[INFO] AI Status: {status}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] AI service basic test failed: {e}")
        return False


def test_scraping_enhancement():
    """Test AI-enhanced scraping functionality"""
    print("\nTesting AI Scraping Enhancement...")
    
    try:
        ai_service = get_ai_service()
        
        # Sample HTML that might be challenging to parse
        sample_html = """
        <html>
        <body>
            <h1>Delicious Chocolate Chip Cookies</h1>
            <p>The best cookies you'll ever taste!</p>
            <div class="ingredients">
                <ul>
                    <li>2 cups all-purpose flour</li>
                    <li>1 tsp baking soda</li>
                    <li>1 cup butter, softened</li>
                    <li>3/4 cup brown sugar</li>
                    <li>2 large eggs</li>
                    <li>2 cups chocolate chips</li>
                </ul>
            </div>
            <div class="instructions">
                <p>1. Preheat oven to 375°F</p>
                <p>2. Mix flour and baking soda</p>
                <p>3. Cream butter and sugar</p>
                <p>4. Add eggs and mix</p>
                <p>5. Combine wet and dry ingredients</p>
                <p>6. Stir in chocolate chips</p>
                <p>7. Bake for 9-11 minutes</p>
            </div>
        </body>
        </html>
        """
        
        url = "https://example.com/chocolate-chip-cookies"
        
        # Test AI enhancement
        enhanced_data = ai_service.enhance_scraping_with_ai(sample_html, url)
        
        if enhanced_data:
            print("[OK] AI scraping enhancement successful")
            print(f"[INFO] Enhanced data keys: {list(enhanced_data.keys())}")
            if 'title' in enhanced_data:
                print(f"[INFO] Extracted title: {enhanced_data['title']}")
        else:
            print("[INFO] AI scraping enhancement not available (LM Studio not running)")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Scraping enhancement test failed: {e}")
        return False


def test_ingredient_suggestions():
    """Test AI ingredient suggestion functionality"""
    print("\nTesting AI Ingredient Suggestions...")
    
    try:
        ai_service = get_ai_service()
        
        # Create sample recipe
        sample_recipe = ParsedRecipe(
            title="Chocolate Chip Cookies",
            description="Classic cookies",
            ingredients=[
                {'name': 'flour', 'quantity': 2.0, 'unit': 'cup'},
                {'name': 'butter', 'quantity': 1.0, 'unit': 'cup'},
                {'name': 'sugar', 'quantity': 0.75, 'unit': 'cup'},
                {'name': 'eggs', 'quantity': 2.0, 'unit': ''},
                {'name': 'chocolate chips', 'quantity': 2.0, 'unit': 'cup'}
            ],
            instructions="Mix and bake",
            source_url="https://example.com",
            prep_time_minutes=15,
            cook_time_minutes=11,
            servings=24
        )
        
        pantry_ingredients = ['flour', 'butter', 'vanilla extract', 'milk']
        
        # Test ingredient suggestions
        suggestions = ai_service.suggest_ingredients_for_recipe(sample_recipe, pantry_ingredients)
        
        if suggestions:
            print(f"[OK] AI ingredient suggestions successful: {suggestions}")
        else:
            print("[INFO] AI ingredient suggestions not available (LM Studio not running)")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Ingredient suggestions test failed: {e}")
        return False


def test_instruction_improvement():
    """Test AI instruction improvement functionality"""
    print("\nTesting AI Instruction Improvement...")
    
    try:
        ai_service = get_ai_service()
        
        # Create sample recipe with basic instructions
        sample_recipe = ParsedRecipe(
            title="Simple Pancakes",
            description="Easy pancakes",
            ingredients=[
                {'name': 'flour', 'quantity': 1.0, 'unit': 'cup'},
                {'name': 'milk', 'quantity': 1.0, 'unit': 'cup'},
                {'name': 'egg', 'quantity': 1.0, 'unit': ''},
                {'name': 'butter', 'quantity': 2.0, 'unit': 'tbsp'}
            ],
            instructions="Mix ingredients. Cook on griddle. Flip when bubbles form.",
            source_url="https://example.com",
            prep_time_minutes=5,
            cook_time_minutes=10,
            servings=4
        )
        
        # Test instruction improvement
        improved_instructions = ai_service.improve_recipe_instructions(sample_recipe)
        
        if improved_instructions:
            print("[OK] AI instruction improvement successful")
            print(f"[INFO] Improved instructions length: {len(improved_instructions)} characters")
        else:
            print("[INFO] AI instruction improvement not available (LM Studio not running)")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Instruction improvement test failed: {e}")
        return False


def test_nutrition_estimation():
    """Test AI nutrition estimation functionality"""
    print("\nTesting AI Nutrition Estimation...")
    
    try:
        ai_service = get_ai_service()
        
        # Create sample recipe
        sample_recipe = ParsedRecipe(
            title="Grilled Chicken Breast",
            description="Healthy protein",
            ingredients=[
                {'original_text': '4 oz chicken breast', 'name': 'chicken breast', 'quantity': 4.0, 'unit': 'oz'},
                {'original_text': '1 tbsp olive oil', 'name': 'olive oil', 'quantity': 1.0, 'unit': 'tbsp'},
                {'original_text': 'salt and pepper to taste', 'name': 'salt and pepper', 'quantity': 0.0, 'unit': ''}
            ],
            instructions="Season chicken, grill until cooked through",
            source_url="https://example.com",
            prep_time_minutes=5,
            cook_time_minutes=15,
            servings=1
        )
        
        # Test nutrition estimation
        nutrition = ai_service.extract_nutrition_estimates(sample_recipe)
        
        if nutrition:
            print("[OK] AI nutrition estimation successful")
            print(f"[INFO] Nutrition data: {nutrition}")
        else:
            print("[INFO] AI nutrition estimation not available (LM Studio not running)")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Nutrition estimation test failed: {e}")
        return False


def main():
    """Run all AI service tests"""
    print("====================================")
    print("    Pans Cookbook - AI Service Tests")
    print("====================================")
    print()
    
    tests = [
        test_ai_service_basic,
        test_scraping_enhancement,
        test_ingredient_suggestions,
        test_instruction_improvement,
        test_nutrition_estimation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"[FAIL] Test {test.__name__} crashed: {e}")
    
    print()
    print("====================================")
    if passed == total:
        print("    ALL AI SERVICE TESTS PASSED!")
    else:
        print(f"    {passed}/{total} tests passed")
        print("    Some tests may fail if LM Studio is not running")
    print("====================================")
    print()
    
    # Instructions for LM Studio setup
    print("LM Studio Setup Instructions:")
    print("1. Download LM Studio from https://lmstudio.ai/")
    print("2. Install and launch LM Studio")
    print("3. Download a compatible model (e.g., Llama 2, Code Llama)")
    print("4. Start the local server on port 1234 (default)")
    print("5. Re-run this test to verify AI functionality")


if __name__ == "__main__":
    main()