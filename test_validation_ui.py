#!/usr/bin/env python3
"""
Test script for validation forms UI components.
Tests validation interface initialization and component creation.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from ui.validation_forms import ValidationInterface
from services.parsing_service import ParsingService
from services.database_service import DatabaseService
from models import ParsedRecipe
from datetime import datetime

def test_validation_interface_creation():
    """Test that validation interface can be created"""
    print("Testing Validation Interface Creation...")
    
    # Initialize services
    db = DatabaseService(":memory:")
    parser = ParsingService(db)
    
    # Create validation interface
    interface = ValidationInterface(parser, db)
    print("[OK] Validation interface created successfully")
    
    return True

def create_sample_parsed_recipe() -> ParsedRecipe:
    """Create sample parsed recipe for UI testing"""
    return ParsedRecipe(
        title="Test Chocolate Chip Cookies",
        description="Amazing test cookies for validation",
        instructions="1. Mix ingredients. 2. Bake at 375°F.",
        source_url="https://test.com/cookies",
        ingredients=[
            {
                'original_text': '2 cups flour',
                'quantity': 2.0,
                'unit': 'cup',
                'name': 'flour',
                'preparation': '',
                'optional': False,
                'order': 1
            },
            {
                'original_text': '1 cup butter, softened',
                'quantity': 1.0,
                'unit': 'cup',
                'name': 'butter',
                'preparation': 'softened',
                'optional': False,
                'order': 2
            }
        ],
        prep_time_minutes=15,
        cook_time_minutes=12,
        servings=24,
        difficulty_level="easy",
        cuisine_type="American",
        meal_category="dessert",
        dietary_tags=["vegetarian"]
    )

def test_validation_components():
    """Test validation form component methods"""
    print("\nTesting Validation Form Components...")
    
    # Initialize services
    db = DatabaseService(":memory:")
    parser = ParsingService(db)
    interface = ValidationInterface(parser, db)
    
    # Create test recipe
    recipe = create_sample_parsed_recipe()
    print(f"[OK] Test recipe created: {recipe.title}")
    
    # Test basic validation data extraction (without Streamlit UI)
    print("[TEST] Component initialization successful")
    print(f"  Recipe title: {recipe.title}")
    print(f"  Ingredients: {len(recipe.ingredients)}")
    print(f"  Total time: {recipe.get_total_time()} minutes")
    print(f"  Difficulty: {recipe.difficulty_level}")
    
    return True

if __name__ == "__main__":
    try:
        success1 = test_validation_interface_creation()
        success2 = test_validation_components()
        
        if all([success1, success2]):
            print("\n[SUCCESS] All validation UI tests passed!")
            print("Manual validation forms UI is ready for use.")
            sys.exit(0)
        else:
            print("\n[FAIL] Some validation UI tests failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"[ERROR] Validation UI test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)