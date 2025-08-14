#!/usr/bin/env python3
"""
Script to retrofit existing recipes with structured ingredient mappings.
Extracts ingredients from recipe text and creates proper database relationships.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config.database_config import get_database_service
from services import get_ingredient_service
from main import parse_ingredient_text, auto_match_ingredient

def extract_ingredients_from_recipes():
    """Extract and structure ingredients from existing recipes"""
    
    # Recipe ingredient data manually extracted from the instructions
    recipe_ingredients = {
        2: [  # Simple Baked Chicken Breast
            "4 boneless skinless chicken breasts",
            "2 tbsp olive oil", 
            "1 tsp salt",
            "1/2 tsp black pepper",
            "1 tsp garlic powder",
            "1 tsp paprika",
            "1/2 tsp dried thyme"
        ],
        3: [  # Pork Tenderloin Spice Rub
            "1 pork tenderloin",
            "1 tsp paprika",
            "1 tsp brown sugar",
            "1/2 tsp garlic powder",
            "1/2 tsp onion powder", 
            "1/2 tsp salt",
            "1/4 tsp black pepper",
            "1/4 tsp cayenne pepper"
        ],
        5: [  # Ricotta & Garlic Stuffed Mini Portobello Mushrooms
            "8 mini portobello mushrooms",
            "1 cup ricotta cheese",
            "1/2 cup parmesan cheese",
            "1/2 cup mozzarella cheese",
            "1/4 cup breadcrumbs",
            "3 cloves garlic, minced",
            "2 tbsp olive oil",
            "1/4 tsp salt",
            "1/4 tsp black pepper",
            "2 tbsp fresh parsley"
        ],
        6: [  # Chicken Piccata with Mushrooms and Creamy Sauce Over Pasta
            "4 boneless skinless chicken breasts",
            "1/2 cup flour",
            "3 tbsp olive oil",
            "2 tbsp butter",
            "8 oz mushrooms, sliced",
            "3 cloves garlic, minced",
            "1/2 cup white wine",
            "1/2 cup chicken broth",
            "1/4 cup lemon juice",
            "1/2 cup heavy cream",
            "12 oz fettuccine pasta",
            "1/4 tsp salt",
            "1/4 tsp black pepper",
            "2 tbsp capers"
        ]
    }
    
    db = get_database_service()
    ingredient_service = get_ingredient_service()
    all_ingredients = ingredient_service.get_all_ingredients()
    
    print("Retrofitting existing recipes with structured ingredients...")
    print("=" * 60)
    
    for recipe_id, ingredient_list in recipe_ingredients.items():
        print(f"\nProcessing Recipe ID {recipe_id}:")
        
        # Clear any existing ingredient mappings for this recipe
        with db.get_connection() as conn:
            conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
            conn.commit()
        
        successful_mappings = 0
        
        for order, ingredient_text in enumerate(ingredient_list):
            print(f"  Processing: {ingredient_text}")
            
            # Parse the ingredient text
            parsed = parse_ingredient_text(ingredient_text)
            print(f"    Parsed: {parsed['quantity']} {parsed['unit']} {parsed['ingredient_name']} ({parsed['preparation']})")
            
            # Try to auto-match to existing ingredients
            matched_ingredient = auto_match_ingredient(parsed['ingredient_name'], all_ingredients)
            
            if matched_ingredient:
                print(f"    MATCHED to: {matched_ingredient.name} ({matched_ingredient.category})")
                
                # Save to database
                success = db.add_recipe_ingredient(
                    recipe_id=recipe_id,
                    ingredient_id=matched_ingredient.id,
                    quantity=parsed['quantity'],
                    unit=parsed['unit'],
                    preparation_note=parsed['preparation'],
                    ingredient_order=order,
                    is_optional=False
                )
                
                if success:
                    successful_mappings += 1
                    print(f"    SAVED to database")
                else:
                    print(f"    FAILED to save to database")
            else:
                print(f"    NO MATCH found for: {parsed['ingredient_name']}")
                print(f"        You may need to create this ingredient manually")
        
        print(f"  Recipe {recipe_id}: {successful_mappings}/{len(ingredient_list)} ingredients mapped")
        print("-" * 40)
    
    print("\nRetrofit complete!")
    
    # Verify the results
    print("\nVerification - Recipe ingredient counts:")
    for recipe_id in recipe_ingredients.keys():
        with db.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
            count = cursor.fetchone()[0]
            print(f"  Recipe {recipe_id}: {count} ingredients in database")

if __name__ == "__main__":
    extract_ingredients_from_recipes()