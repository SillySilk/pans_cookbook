#!/usr/bin/env python3
"""
Pans Cookbook - Main Application Entry Point

A recipe finder and manager with web scraping capabilities.
Based on traditional parsing with manual validation workflows.
"""

import sys
import streamlit as st
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from models import ScrapedRecipe
from services import DatabaseService, ParsingService
from ui import ValidationInterface
from datetime import datetime

def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="Pans Cookbook",
        page_icon="🍳",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🍳 Pans Cookbook")
    st.subheader("Recipe Finder & Manager")
    
    # Navigation
    tab1, tab2, tab3 = st.tabs(["📊 Status", "🔍 Validation Demo", "📝 Recipe Manager"])
    
    with tab1:
        st.info("""
        Welcome to Pans Cookbook! This application is currently under development.
        
        **Completed Components:**
        - ✅ Database service with multi-user support
        - ✅ Authentication system with encrypted API keys
        - ✅ Web scraping service with robots.txt compliance
        - ✅ Recipe parsing and validation logic
        - ✅ Manual validation forms for scraped recipes
        
        **Coming Next:**
        - 🔍 Recipe search and filtering interface
        - 🤖 Optional AI integration for recipe suggestions
        - 👥 User management and collections
        """)
        
        # Test connectivity
        with st.expander("System Status", expanded=False):
            try:
                db = DatabaseService(":memory:")
                st.success("✅ Database service: Working")
            except Exception as e:
                st.error(f"❌ Database service: {e}")
            
            try:
                from services import ScrapingService
                scraper = ScrapingService()
                st.success("✅ Scraping service: Working")
            except Exception as e:
                st.error(f"❌ Scraping service: {e}")
            
            try:
                parser = ParsingService()
                st.success("✅ Parsing service: Working")
            except Exception as e:
                st.error(f"❌ Parsing service: {e}")
            
            try:
                validation_ui = ValidationInterface(ParsingService(), DatabaseService(":memory:"))
                st.success("✅ Validation UI: Working")
            except Exception as e:
                st.error(f"❌ Validation UI: {e}")
    
    with tab2:
        demo_validation_interface()
    
    with tab3:
        st.info("Recipe manager coming in future tasks...")
        

def demo_validation_interface():
    """Demo the validation interface with sample data"""
    st.markdown("### 🔍 Recipe Validation Demo")
    st.markdown("This demonstrates how scraped recipes are manually validated before saving.")
    
    # Create sample scraped recipe
    sample_recipe = create_sample_scraped_recipe()
    
    # Initialize services
    db = DatabaseService(":memory:")
    parser = ParsingService(db)
    validation_ui = ValidationInterface(parser, db)
    
    # Parse the sample recipe
    parsed_recipe = parser.parse_scraped_recipe(sample_recipe)
    
    # Show validation interface
    validation_result = validation_ui.validate_recipe(parsed_recipe, user_id=1)
    
    if validation_result:
        if validation_result.is_valid:
            st.success("✅ Recipe validated and ready to save!")
            
            with st.expander("Validation Summary", expanded=True):
                st.write(f"**Corrections Made:** {validation_result.get_correction_summary()}")
                st.write(f"**Ingredient Assignments:** {len(validation_result.ingredient_assignments)}")
                st.write(f"**New Ingredients:** {len(validation_result.new_ingredients)}")
                
                if validation_result.new_ingredients:
                    st.write("**New ingredients to create:**")
                    for ing in validation_result.new_ingredients:
                        st.write(f"• {ing}")
        else:
            st.warning("❌ Recipe was rejected during validation.")


def create_sample_scraped_recipe() -> ScrapedRecipe:
    """Create sample scraped recipe for demo"""
    return ScrapedRecipe(
        url="https://example.com/chocolate-chip-cookies",
        title="Amazing Chocolate Chip Cookies - Best Recipe Ever!",
        description="These cookies are absolutely incredible and everyone will love them!",
        ingredients_raw=[
            "2 1/4 cups all-purpose flour",
            "1 tsp baking soda",
            "1 tsp salt",
            "1 cup butter, softened",
            "3/4 cup granulated sugar", 
            "3/4 cup packed brown sugar",
            "2 large eggs",
            "2 tsp vanilla extract",
            "2 cups chocolate chips"
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
        total_time_text="26 minutes",
        servings_text="48 cookies",
        cuisine_text="American",
        category_text="Dessert",
        difficulty_text="Easy",
        rating_text="4.8 stars",
        confidence_score=0.85,
        scraped_at=datetime.now(),
        scraping_method="demo_data"
    )

if __name__ == "__main__":
    main()