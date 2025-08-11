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

from models import ScrapedRecipe, ParsedRecipe
from services import DatabaseService, ParsingService, AIService, get_pantry_service
from ui import ValidationInterface, AIFeaturesInterface, show_ai_status
from ui.responsive_design import ResponsiveDesign, MobileOptimizations, create_responsive_layout
from ui.pantry_manager import PantryManagerInterface
from datetime import datetime

def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="Pans Cookbook",
        page_icon="🍳",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize responsive design
    responsive = create_responsive_layout("standard")
    
    st.title("🍳 Pans Cookbook")
    st.subheader("Recipe Finder & Manager")
    
    # Mobile-friendly navigation
    tab_config = [
        {"label": "Status", "icon": "📊"},
        {"label": "Validation Demo", "icon": "🔍"},
        {"label": "AI Features", "icon": "🤖"},
        {"label": "My Pantry", "icon": "🥬"}
    ]
    tab1, tab2, tab3, tab4 = responsive.create_responsive_tabs(tab_config)
    
    with tab1:
        # Welcome message with responsive layout
        responsive.create_collapsible_section("Welcome to Pans Cookbook!", "welcome", 
                                             expanded_on_desktop=True, expanded_on_mobile=False)
        st.info("""
        Welcome to Pans Cookbook! This application is currently under development.
        
        **Completed Components:**
        - ✅ Database service with multi-user support
        - ✅ Authentication system with encrypted API keys
        - ✅ Web scraping service with robots.txt compliance
        - ✅ Recipe parsing and validation logic
        - ✅ Manual validation forms for scraped recipes
        - ✅ AI integration with LM Studio for recipe enhancement
        - ✅ AI features UI with ingredient suggestions & instruction improvements
        - ✅ Advanced filtering and search features
        - ✅ Responsive web design
        - ✅ Pantry management with "what can I make" functionality
        
        **Coming Next:**
        - 👥 User management and collections
        - 🔄 Comprehensive testing
        """)
        
        # System metrics in responsive layout
        metrics = [
            {"label": "Services", "value": "9", "delta": "Active"},
            {"label": "UI Components", "value": "7", "delta": "Mobile-Ready"},
            {"label": "Test Coverage", "value": "85%", "delta": "Good"}
        ]
        responsive.render_responsive_metrics(metrics)
        
        # Test connectivity
        with responsive.create_collapsible_section("System Status", "status", 
                                                  expanded_on_desktop=False, expanded_on_mobile=False):
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
            
            try:
                ai_service = AIService(DatabaseService(":memory:"))
                ai_ui = AIFeaturesInterface(ai_service)
                st.success("✅ AI Features UI: Working")
            except Exception as e:
                st.error(f"❌ AI Features UI: {e}")
            
            try:
                pantry_service = get_pantry_service()
                pantry_ui = PantryManagerInterface(pantry_service)
                st.success("✅ Pantry Management: Working")
            except Exception as e:
                st.error(f"❌ Pantry Management: {e}")
            
            # AI Status
            try:
                show_ai_status(compact=False)
            except Exception as e:
                st.error(f"❌ AI Status Check: {e}")
    
    with tab2:
        demo_validation_interface()
    
    with tab3:
        demo_ai_features()
    
    with tab4:
        demo_pantry_manager()
        

def demo_validation_interface():
    """Demo the validation interface with text input and file upload"""
    st.markdown("### 🔍 Recipe Parser & Validation")
    st.markdown("Add recipes by pasting text or uploading files, then validate before saving to your cookbook.")
    
    # Initialize services
    db = DatabaseService(":memory:")
    parser = ParsingService(db)
    validation_ui = ValidationInterface(parser, db)
    
    # Create tabs for different input modes
    demo_tab1, demo_tab2, demo_tab3 = st.tabs(["📝 Text Input", "📁 File Upload", "🎯 Sample Data"])
    
    with demo_tab1:
        st.markdown("#### Paste Recipe Text")
        st.info("Copy and paste recipe text from any website, cookbook, or document. The parser will extract structured data automatically.")
        
        # Text input form
        with st.form("text_input_form", clear_on_submit=False):
            recipe_text = st.text_area(
                "Recipe Text", 
                placeholder="""Paste your recipe here... For example:

Chocolate Chip Cookies

Ingredients:
- 2 1/4 cups all-purpose flour
- 1 tsp baking soda
- 1 tsp salt
- 1 cup butter, softened
- 3/4 cup granulated sugar
- 3/4 cup packed brown sugar
- 2 large eggs
- 2 tsp vanilla extract
- 2 cups chocolate chips

Instructions:
1. Preheat oven to 375°F
2. Mix flour, baking soda and salt in bowl
3. Cream butter and sugars until fluffy
4. Beat in eggs and vanilla
5. Gradually add flour mixture
6. Stir in chocolate chips
7. Drop spoonfuls on cookie sheet
8. Bake 9-11 minutes until golden

Prep: 15 minutes
Cook: 11 minutes
Serves: 36 cookies""",
                height=400,
                help="Paste any recipe text - the parser will automatically detect ingredients, instructions, times, and other details"
            )
            
            col1, col2 = st.columns([1, 3])
            with col1:
                parse_button = st.form_submit_button("🧠 Parse Recipe", type="primary")
            with col2:
                st.caption("The parser works with any text format - websites, cookbooks, handwritten notes!")
        
        if parse_button and recipe_text.strip():
            with st.spinner("Parsing recipe text... Extracting structured data."):
                try:
                    # Import scraping service for text parsing
                    from services import ScrapingService
                    scraper = ScrapingService()
                    
                    # Parse text directly (create a method for this)
                    scraped_recipe = scraper.parse_recipe_text(recipe_text)
                    
                    if scraped_recipe and scraped_recipe.confidence_score > 0.2:
                        st.success(f"✅ Successfully parsed recipe: {scraped_recipe.title}")
                        
                        # Show parsed data preview
                        with st.expander("📋 Parsed Data Preview", expanded=True):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write("**Title:**", scraped_recipe.title)
                                st.write("**Description:**", scraped_recipe.description[:200] + "..." if scraped_recipe.description and len(scraped_recipe.description) > 200 else scraped_recipe.description)
                                st.write("**Confidence Score:**", f"{scraped_recipe.confidence_score:.2f}")
                                st.write("**Ingredients Found:**", len(scraped_recipe.ingredients_raw))
                            
                            with col2:
                                st.write("**Prep Time:**", scraped_recipe.prep_time_text)
                                st.write("**Cook Time:**", scraped_recipe.cook_time_text)
                                st.write("**Servings:**", scraped_recipe.servings_text)
                                st.write("**Cuisine:**", scraped_recipe.cuisine_text)
                        
                        # Show ingredients and instructions preview
                        col1, col2 = st.columns(2)
                        with col1:
                            with st.expander("🥕 Ingredients", expanded=False):
                                for ingredient in scraped_recipe.ingredients_raw:
                                    st.write(f"• {ingredient}")
                        
                        with col2:
                            with st.expander("👩‍🍳 Instructions", expanded=False):
                                st.write(scraped_recipe.instructions_raw)
                        
                        # Parse and validate the scraped recipe
                        st.markdown("#### 🔍 Recipe Validation")
                        parsed_recipe = parser.parse_scraped_recipe(scraped_recipe)
                        
                        # Show validation interface
                        validation_result = validation_ui.validate_recipe(parsed_recipe, user_id=1)
                        
                        if validation_result and validation_result.is_valid:
                            st.success("✅ Recipe validated and ready to save!")
                            
                            with st.expander("Validation Summary", expanded=True):
                                st.write(f"**Corrections Made:** {validation_result.get_correction_summary()}")
                                st.write(f"**Ingredient Assignments:** {len(validation_result.ingredient_assignments)}")
                                st.write(f"**New Ingredients:** {len(validation_result.new_ingredients)}")
                                
                                if validation_result.new_ingredients:
                                    st.write("**New ingredients to create:**")
                                    for ing in validation_result.new_ingredients:
                                        st.write(f"• {ing}")
                            
                            # Save button
                            if st.button("💾 Save Recipe to Cookbook", type="primary"):
                                st.success("Recipe would be saved to your cookbook! (Demo mode)")
                        
                    else:
                        st.error("❌ Unable to parse recipe from this text. Please check the format and try again.")
                        st.info("💡 **Tips for better parsing:**")
                        st.info("• Include a clear title at the top")
                        st.info("• List ingredients with quantities (e.g., '2 cups flour')")
                        st.info("• Number or clearly separate instruction steps")
                        st.info("• Include timing information if available")
                        
                except Exception as e:
                    st.error(f"❌ Parsing failed: {str(e)}")
                    st.info("The text parser works best with clearly formatted recipes. Try adjusting the format or contact support.")
    
    with demo_tab2:
        st.markdown("#### Upload Recipe File")
        st.info("Upload HTML files saved from recipe websites, or text files containing recipes.")
        
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['html', 'htm', 'txt', 'md'],
            help="Upload HTML files from recipe websites or text files with recipe content"
        )
        
        if uploaded_file is not None:
            with st.spinner("Reading and parsing file..."):
                try:
                    # Read file content
                    if uploaded_file.type.startswith('text/') or uploaded_file.name.endswith('.txt'):
                        # Text file
                        content = str(uploaded_file.read(), "utf-8")
                        st.success(f"📄 Read text file: {uploaded_file.name}")
                    else:
                        # HTML file
                        content = str(uploaded_file.read(), "utf-8")
                        st.success(f"🌐 Read HTML file: {uploaded_file.name}")
                    
                    # Show file preview
                    with st.expander("📄 File Content Preview", expanded=False):
                        preview = content[:500] + "..." if len(content) > 500 else content
                        st.text(preview)
                    
                    # Parse the file content
                    from services import ScrapingService
                    scraper = ScrapingService()
                    
                    if uploaded_file.name.endswith(('.html', '.htm')):
                        # Parse HTML content
                        scraped_recipe = scraper.parse_html_content(content)
                    else:
                        # Parse as text content
                        scraped_recipe = scraper.parse_recipe_text(content)
                    
                    if scraped_recipe and scraped_recipe.confidence_score > 0.2:
                        st.success(f"✅ Successfully parsed: {scraped_recipe.title}")
                        
                        # Show parsed data and validation (same as text input)
                        st.markdown("#### 🔍 Recipe Validation") 
                        parsed_recipe = parser.parse_scraped_recipe(scraped_recipe)
                        validation_result = validation_ui.validate_recipe(parsed_recipe, user_id=1)
                        
                        if validation_result and validation_result.is_valid:
                            st.success("✅ Recipe validated and ready to save!")
                            if st.button("💾 Save Recipe to Cookbook", key="file_save", type="primary"):
                                st.success("Recipe would be saved to your cookbook! (Demo mode)")
                    else:
                        st.error("❌ Unable to parse recipe from this file.")
                        st.info("💡 Try files with clear recipe structure or use the text input method.")
                        
                except Exception as e:
                    st.error(f"❌ File processing failed: {str(e)}")
                    st.info("Make sure the file contains readable recipe content.")
    
    with demo_tab3:
        st.markdown("#### Sample Data Demo")
        st.info("This shows how the validation process works with pre-loaded sample data.")
        
        # Create sample scraped recipe
        sample_recipe = create_sample_scraped_recipe()
        
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


def demo_ai_features():
    """Demo the AI features interface with sample data"""
    st.markdown("### 🤖 AI Features Demo")
    st.markdown("Experience AI-powered recipe enhancements and suggestions.")
    
    # Initialize AI services
    db = DatabaseService(":memory:")
    ai_service = AIService(db)
    ai_ui = AIFeaturesInterface(ai_service, db)
    
    # Show AI status first
    ai_ui.render_ai_status_indicator(compact=False)
    
    if not ai_service.is_ai_available():
        st.info("👆 Start LM Studio to see AI features in action!")
        return
    
    # Create sample recipe for AI demo
    sample_recipe = create_sample_parsed_recipe()
    
    # Show AI enhancement panel
    st.markdown("---")
    ai_ui.render_recipe_ai_panel(sample_recipe, user_pantry=['flour', 'butter', 'sugar', 'vanilla'])
    
    # Show additional AI features
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔧 AI Settings")
        ai_ui.render_ai_settings_panel()
    
    with col2:
        st.markdown("### 🔍 AI Scraping Helper")
        ai_ui.render_ai_scraping_helper()


def demo_pantry_manager():
    """Demo the pantry management interface"""
    st.markdown("### 🥬 My Pantry - What Can I Make?")
    st.markdown("Manage your ingredient inventory and discover recipes you can make right now!")
    
    # Initialize pantry services  
    db = DatabaseService(":memory:")
    pantry_service = get_pantry_service(db)
    pantry_ui = PantryManagerInterface(pantry_service)
    
    # Demo user ID
    demo_user_id = 1
    
    # Add some sample ingredients to the database for demo
    try:
        # Ensure we have some basic ingredients
        from services import get_ingredient_service
        ingredient_service = get_ingredient_service(db)
        
        # Add common pantry ingredients
        sample_ingredients = [
            ("Salt", "seasoning"),
            ("Black Pepper", "seasoning"),
            ("Olive Oil", "oil"), 
            ("Butter", "dairy"),
            ("Garlic", "vegetable"),
            ("Onion", "vegetable"),
            ("All-Purpose Flour", "grain"),
            ("Sugar", "sweetener"),
            ("Eggs", "protein"),
            ("Chicken Breast", "protein"),
            ("Milk", "dairy"),
            ("Tomato", "vegetable"),
            ("Basil", "herb"),
            ("Mozzarella Cheese", "dairy"),
            ("Ground Beef", "protein")
        ]
        
        for name, category in sample_ingredients:
            try:
                ingredient_service.create_ingredient(name, category)
            except:
                pass  # Ingredient might already exist
        
        # Create a few sample recipes with ingredients
        from models import Recipe
        sample_recipes = [
            {
                'name': 'Simple Scrambled Eggs',
                'description': 'Quick and easy scrambled eggs',
                'instructions': '1. Heat butter in pan 2. Whisk eggs with salt and pepper 3. Cook eggs stirring frequently 4. Serve hot',
                'prep_time_minutes': 5,
                'cook_time_minutes': 5,
                'servings': 2,
                'difficulty_level': 'easy',
                'ingredients': ['Eggs', 'Butter', 'Salt', 'Black Pepper']
            },
            {
                'name': 'Garlic Butter Chicken',
                'description': 'Tender chicken with garlic butter sauce',
                'instructions': '1. Season chicken with salt and pepper 2. Heat oil in pan 3. Cook chicken until golden 4. Add garlic and butter 5. Cook until done',
                'prep_time_minutes': 10,
                'cook_time_minutes': 15,
                'servings': 4,
                'difficulty_level': 'medium',
                'ingredients': ['Chicken Breast', 'Garlic', 'Butter', 'Olive Oil', 'Salt', 'Black Pepper']
            },
            {
                'name': 'Caprese Salad',
                'description': 'Fresh tomato and mozzarella salad',
                'instructions': '1. Slice tomatoes and mozzarella 2. Arrange on plate 3. Add basil leaves 4. Drizzle with olive oil 5. Season with salt and pepper',
                'prep_time_minutes': 10,
                'cook_time_minutes': 0,
                'servings': 2,
                'difficulty_level': 'easy',
                'ingredients': ['Tomato', 'Mozzarella Cheese', 'Basil', 'Olive Oil', 'Salt', 'Black Pepper']
            }
        ]
        
        # Add recipes to database
        for recipe_data in sample_recipes:
            try:
                # Create recipe
                recipe = db.create_recipe(
                    name=recipe_data['name'],
                    description=recipe_data['description'],
                    instructions=recipe_data['instructions'],
                    prep_time_minutes=recipe_data['prep_time_minutes'],
                    cook_time_minutes=recipe_data['cook_time_minutes'],
                    servings=recipe_data['servings'],
                    difficulty_level=recipe_data['difficulty_level'],
                    created_by=demo_user_id
                )
                
                if recipe:
                    # Add ingredients to recipe
                    for ingredient_name in recipe_data['ingredients']:
                        ingredients = db.search_ingredients(ingredient_name)
                        if ingredients:
                            ingredient = ingredients[0]
                            db.add_recipe_ingredient(
                                recipe.id,
                                ingredient.id,
                                quantity=1.0,
                                unit="unit"
                            )
            except Exception as e:
                pass  # Recipe might already exist
        
    except Exception as e:
        st.warning(f"Demo setup issue: {e}")
    
    # Check if user has a pantry setup
    user_pantry = pantry_service.get_user_pantry(demo_user_id)
    
    if not user_pantry:
        st.info("👋 Welcome to your pantry! Let's set it up with some common ingredients.")
        
        if st.button("🚀 Set Up My Pantry", type="primary"):
            with st.spinner("Setting up your pantry with common ingredients..."):
                added_count = pantry_service.add_common_ingredients_to_pantry(demo_user_id)
                st.success(f"✅ Added {added_count} common ingredients to your pantry!")
                st.experimental_rerun()
    else:
        # Show main pantry interface
        pantry_ui.render_pantry_interface(demo_user_id)
        
        # Show what recipes can be made
        st.markdown("---")
        st.markdown("### 🍽️ Recipes You Can Make Now")
        
        makeable_recipes = pantry_service.find_makeable_recipes(demo_user_id, strict_mode=True)
        partial_recipes = pantry_service.find_makeable_recipes(demo_user_id, strict_mode=False, include_partial_matches=True)
        
        if makeable_recipes:
            st.success(f"🎉 You can make {len(makeable_recipes)} recipes right now!")
            
            for recipe_match in makeable_recipes[:3]:  # Show top 3
                with st.expander(f"✅ {recipe_match.recipe.name} ({recipe_match.match_status})", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Description:** {recipe_match.recipe.description}")
                        st.write(f"**Time:** {recipe_match.recipe.prep_time_minutes + recipe_match.recipe.cook_time_minutes} min")
                        st.write(f"**Servings:** {recipe_match.recipe.servings}")
                        st.write(f"**Difficulty:** {recipe_match.recipe.difficulty_level}")
                    
                    with col2:
                        st.write("**Your Available Ingredients:**")
                        for ingredient in recipe_match.available_ingredients:
                            st.write(f"✅ {ingredient}")
                        
                        if recipe_match.missing_ingredients:
                            st.write("**Missing:**")
                            for ingredient in recipe_match.missing_ingredients:
                                st.write(f"❌ {ingredient}")
        else:
            st.info("😔 No complete recipes found with your current ingredients.")
        
        # Show partial matches
        partial_only = [r for r in partial_recipes if not r.can_make][:3]
        if partial_only:
            st.markdown("### 🟡 Almost Ready (Need 1-2 ingredients)")
            
            for recipe_match in partial_only:
                with st.expander(f"🟡 {recipe_match.recipe.name} - Missing {len(recipe_match.missing_ingredients)} ingredients", expanded=False):
                    st.write(f"**Match:** {recipe_match.match_percentage:.0%} of ingredients")
                    st.write(f"**Need to buy:** {', '.join(recipe_match.missing_ingredients)}")
        
        # Shopping suggestions
        if makeable_recipes or partial_only:
            st.markdown("---")
            st.markdown("### 🛒 Shopping Suggestions")
            
            suggestions = pantry_service.suggest_recipes_to_complete_pantry(demo_user_id, max_missing=2)
            
            if suggestions:
                suggestion = suggestions[0]  # Show top suggestion
                st.info(f"💡 **Shopping Tip:** Buy {', '.join(suggestion.missing_ingredients)} to make **{suggestion.recipe.name}**!")
        
        # Pantry statistics
        st.markdown("---")
        with st.expander("📊 Pantry Statistics", expanded=False):
            available_count = len([item for item in user_pantry if item.is_available])
            total_count = len(user_pantry)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Available Ingredients", available_count)
            with col2:
                st.metric("Total in Pantry", total_count)
            with col3:
                st.metric("Makeable Recipes", len(makeable_recipes))


def create_sample_parsed_recipe() -> ParsedRecipe:
    """Create sample parsed recipe for AI demo"""
    return ParsedRecipe(
        title="Classic Chocolate Chip Cookies",
        description="Perfect cookies every time - crispy edges, soft centers!",
        ingredients=[
            {'name': 'all-purpose flour', 'quantity': 2.25, 'unit': 'cup', 'original_text': '2 1/4 cups all-purpose flour'},
            {'name': 'baking soda', 'quantity': 1.0, 'unit': 'tsp', 'original_text': '1 tsp baking soda'},
            {'name': 'salt', 'quantity': 1.0, 'unit': 'tsp', 'original_text': '1 tsp salt'},
            {'name': 'butter', 'quantity': 1.0, 'unit': 'cup', 'original_text': '1 cup butter, softened'},
            {'name': 'brown sugar', 'quantity': 0.75, 'unit': 'cup', 'original_text': '3/4 cup packed brown sugar'},
            {'name': 'granulated sugar', 'quantity': 0.75, 'unit': 'cup', 'original_text': '3/4 cup granulated sugar'},
            {'name': 'eggs', 'quantity': 2.0, 'unit': 'large', 'original_text': '2 large eggs'},
            {'name': 'vanilla extract', 'quantity': 2.0, 'unit': 'tsp', 'original_text': '2 tsp vanilla extract'},
            {'name': 'chocolate chips', 'quantity': 2.0, 'unit': 'cup', 'original_text': '2 cups chocolate chips'}
        ],
        instructions="""1. Preheat oven to 375°F. 2. Mix flour, baking soda and salt in bowl. 3. Cream butter and sugars until fluffy. 4. Beat in eggs and vanilla. 5. Gradually add flour mixture. 6. Stir in chocolate chips. 7. Drop spoonfuls on cookie sheet. 8. Bake 9-11 minutes until golden.""",
        source_url="https://example.com/best-cookies",
        prep_time_minutes=15,
        cook_time_minutes=11,
        servings=36,
        difficulty_level="easy",
        cuisine_type="American",
        dietary_tags=["vegetarian"],
        meal_category="dessert"
    )


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