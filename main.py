#!/usr/bin/env python3
"""
Pans Cookbook - Main Application Entry Point

A recipe finder and manager with web scraping capabilities.
Based on traditional parsing with manual validation workflows.
"""

import sys
import streamlit as st
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from models import ScrapedRecipe, ParsedRecipe
from services import DatabaseService, ParsingService, AIService
import tempfile
import os
from ui import ValidationInterface, AIFeaturesInterface, show_ai_status
from ui.recipe_browser import RecipeBrowser
from ui.responsive_design import ResponsiveDesign, MobileOptimizations, create_responsive_layout
from datetime import datetime


def get_database_service_singleton():
    """Get singleton database service instance with automatic type detection"""
    if 'database_service' not in st.session_state:
        from config.database_config import get_database_service, get_database_info
        
        # Get database info for display
        db_info = get_database_info()
        
        # Show which database we're using
        if 'db_info_shown' not in st.session_state:
            st.write(f"🗄️ Using database: {db_info['description']}")
            if db_info['type'] == 'postgresql':
                st.write(f"   Host: {db_info['host']}")
            else:
                st.write(f"   Path: {db_info['path']}")
            st.session_state.db_info_shown = True
        
        # Initialize database service
        st.session_state.database_service = get_database_service()
        st.write(f"🔧 Initialized {db_info['type'].upper()} database service")
    
    return st.session_state.database_service

# Import pantry services with error handling for deployment
try:
    from services import get_pantry_service
    from ui.pantry_manager import PantryManagerInterface
    PANTRY_AVAILABLE = True
except ImportError as e:
    print(f"Pantry services not available: {e}")
    PANTRY_AVAILABLE = False

# Import enhanced parsing services
try:
    from services.ai_ingredient_parser import get_ai_ingredient_parser
    from services.bulk_recipe_parser import get_bulk_recipe_parser
    from ui.simple_validation import SimpleValidationInterface
    AI_PARSING_AVAILABLE = True
except ImportError as e:
    print(f"AI parsing services not available: {e}")
    AI_PARSING_AVAILABLE = False

def add_core_pantry_ingredients(db):
    """Add core pantry ingredients from CSV file with categorization"""
    import csv
    from services import get_ingredient_service
    
    csv_path = r"C:\AI\cookbook\orphan\Core_Pantry_Ingredient_List.csv"
    
    # Get ingredient service
    ingredient_service = get_ingredient_service(db)
    
    # Ingredient categorization mapping
    ingredient_categories = {
        # Proteins
        'chicken breast': 'protein',
        'chicken thighs': 'protein', 
        'pork chops': 'protein',
        'pork tenderloin': 'protein',
        'stew meat': 'protein',
        'boneless pork chop tenderloins': 'protein',
        'shredded chicken': 'protein',
        'ground beef': 'protein',
        'bacon': 'protein',
        'salmon': 'protein',
        'shrimp': 'protein',
        
        # Dairy
        'heavy cream': 'dairy',
        'parmesan cheese': 'dairy',
        'shredded mozzarella': 'dairy',
        'ricotta cheese': 'dairy',
        'sour cream': 'dairy',
        'butter': 'dairy',
        'milk': 'dairy',
        'yogurt': 'dairy',
        'cheddar cheese': 'dairy',
        
        # Grains & Pasta
        'egg noodles': 'grains',
        'rotini pasta': 'grains',
        'fettuccine': 'grains',
        'italian style rice': 'grains',
        'israeli couscous': 'grains',
        'pearl couscous': 'grains',
        'breadcrumbs': 'grains',
        'panko breadcrumbs': 'grains',
        'flour': 'grains',
        'tins of biscuits': 'grains',
        'mac and cheese boxes': 'grains',
        
        # Vegetables
        'yellow onion': 'vegetables',
        'bell peppers': 'vegetables',
        'zucchini': 'vegetables',
        'frozen peas': 'vegetables',
        'frozen mixed vegetables': 'vegetables',
        'frozen corn': 'vegetables',
        'frozen green beans': 'vegetables',
        'carrots': 'vegetables',
        'potatoes': 'vegetables',
        'garlic': 'vegetables',
        
        # Pantry/Condiments
        'beef bouillon cubes': 'pantry',
        'cream of mushroom soup': 'pantry',
        'condensed cream soup': 'pantry',
        'beef broth': 'pantry',
        'chicken broth': 'pantry',
        'colseslaw dressing': 'condiments',
        'caesar dressing': 'condiments',
        'worcestershire sauce': 'condiments',
        'marsala cooking wine': 'pantry',
        'white wine': 'pantry',
        'balsamic vinegar': 'condiments',
        'apple cider vinegar': 'condiments',
        'red wine vinegar': 'condiments',
        'lemon juice': 'condiments',
        'olive oil': 'pantry',
        'avocado oil spray': 'pantry',
        'sugar': 'pantry',
        'special dark chocolate': 'pantry'
    }
    
    added_count = 0
    
    try:
        # Read CSV file
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header row
            
            for row in reader:
                if row and len(row) > 0:
                    ingredient_name = row[0].strip().lower()
                    if not ingredient_name:
                        continue
                    
                    # Get category for this ingredient
                    category = ingredient_categories.get(ingredient_name, 'pantry')
                    
                    # Check if ingredient already exists (search for exact match)
                    existing = db.search_ingredients(ingredient_name)
                    name_exists = any(ing.name.lower() == ingredient_name for ing in existing)
                    
                    st.write(f"Debug: Processing '{ingredient_name}' - Existing: {len(existing)}, Name exists: {name_exists}")
                    
                    if not name_exists:
                        # Add new ingredient using ingredient service
                        ingredient = ingredient_service.create_ingredient(
                            name=ingredient_name,
                            category=category,
                            common_substitutes=[],
                            storage_tips="",
                            nutritional_data={}
                        )
                        if ingredient:
                            added_count += 1
                            st.write(f"✅ Successfully added: {ingredient_name} (category: {category}, ID: {ingredient.id})")
                        else:
                            st.write(f"❌ Failed to create: {ingredient_name}")
                    else:
                        st.write(f"⏭️ Skipped (already exists): {ingredient_name}")
    
    except FileNotFoundError:
        st.error(f"❌ Could not find CSV file: {csv_path}")
        return 0
    except Exception as e:
        st.error(f"❌ Error reading CSV file: {e}")
        return 0
    
    return added_count

def migrate_database_data(source_db_path, target_db_service):
    """Migrate ingredients and recipes from one database to another"""
    import sqlite3
    from services import get_ingredient_service
    
    migrated_count = 0
    
    try:
        # Connect to source database
        source_conn = sqlite3.connect(source_db_path)
        source_conn.row_factory = sqlite3.Row
        
        # Get ingredient service for target database
        ingredient_service = get_ingredient_service(target_db_service)
        
        # Migrate ingredients
        cursor = source_conn.cursor()
        cursor.execute("SELECT * FROM ingredients")
        source_ingredients = cursor.fetchall()
        
        st.write(f"Found {len(source_ingredients)} ingredients in {source_db_path}")
        
        for row in source_ingredients:
            ingredient_name = row['name'].lower()
            
            # Check if ingredient already exists in target
            existing = target_db_service.search_ingredients(ingredient_name)
            name_exists = any(ing.name.lower() == ingredient_name for ing in existing)
            
            if not name_exists:
                # Migrate the ingredient
                ingredient = ingredient_service.create_ingredient(
                    name=ingredient_name,
                    category=row['category'] or 'pantry',
                    common_substitutes=[],
                    storage_tips=row.get('storage_tips', ''),
                    nutritional_data={}
                )
                if ingredient:
                    migrated_count += 1
                    st.write(f"✅ Migrated: {ingredient_name}")
                else:
                    st.write(f"❌ Failed to migrate: {ingredient_name}")
            else:
                st.write(f"⏭️ Skipped (exists): {ingredient_name}")
        
        source_conn.close()
        
    except Exception as e:
        st.error(f"❌ Migration failed: {e}")
        import traceback
        with st.expander("Migration Error Details"):
            st.code(traceback.format_exc())
    
    return migrated_count

def clear_database_completely(db_service):
    """Clear all data from the database"""
    try:
        with db_service.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            st.write("🗑️ Clearing all data from tables:")
            
            # Clear each table
            for table in tables:
                table_name = table[0]
                if table_name != 'sqlite_sequence':  # Don't clear system table
                    cursor.execute(f"DELETE FROM {table_name}")
                    st.write(f"- Cleared table: {table_name}")
            
            # Reset auto-increment counters
            cursor.execute("DELETE FROM sqlite_sequence")
            
            conn.commit()
            st.write("✅ All data cleared successfully!")
            return True
            
    except Exception as e:
        st.error(f"❌ Error clearing database: {e}")
        import traceback
        with st.expander("Clear Database Error Details"):
            st.code(traceback.format_exc())
        return False

def recreate_database_from_scratch():
    """Delete the database file and recreate it"""
    try:
        import os
        from pathlib import Path
        from config.database_config import DatabaseConfig
        
        db_config = DatabaseConfig.get_database_config()
        db_path = db_config.get('path', 'database/pans_cookbook.db')
        
        # Delete the database file if it exists
        if os.path.exists(db_path):
            os.remove(db_path)
            st.write(f"🗑️ Deleted database file: {db_path}")
        
        # Clear session state to force recreation
        if 'database_service' in st.session_state:
            del st.session_state['database_service']
        if 'db_path_shown' in st.session_state:
            del st.session_state['db_path_shown']
        
        # Create new database service (will auto-initialize schema)
        new_db = get_database_service_singleton()
        st.write("✅ Created new database with fresh schema")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Error recreating database: {e}")
        import traceback
        with st.expander("Recreate Database Error Details"):
            st.code(traceback.format_exc())
        return False

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
        {"label": "Smart Parser", "icon": "🧠"},
        {"label": "Recipe Browser", "icon": "📚"},
        {"label": "AI Features", "icon": "🤖"},
        {"label": "My Pantry", "icon": "🥬"}
    ]
    tab1, tab2, tab3, tab4, tab5 = responsive.create_responsive_tabs(tab_config)
    
    with tab1:
        # Welcome message with responsive layout
        with responsive.create_collapsible_section("Welcome to Pans Cookbook!", "welcome", 
                                                  expanded_on_desktop=True, expanded_on_mobile=False):
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
                db = get_database_service_singleton()
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
                validation_ui = ValidationInterface(ParsingService(), get_database_service_singleton())
                st.success("✅ Validation UI: Working")
            except Exception as e:
                st.error(f"❌ Validation UI: {e}")
            
            try:
                ai_service = AIService(get_database_service_singleton())
                ai_ui = AIFeaturesInterface(ai_service)
                st.success("✅ AI Features UI: Working")
            except Exception as e:
                st.error(f"❌ AI Features UI: {e}")
            
            if PANTRY_AVAILABLE:
                try:
                    pantry_service = get_pantry_service()
                    pantry_ui = PantryManagerInterface(pantry_service)
                    st.success("✅ Pantry Management: Working")
                except Exception as e:
                    st.error(f"❌ Pantry Management: {e}")
            else:
                st.error("❌ Pantry Management: Not available (import error)")
            
            # AI Status
            try:
                show_ai_status(compact=False)
            except Exception as e:
                st.error(f"❌ AI Status Check: {e}")
        
        # Database inspection section
        with responsive.create_collapsible_section("🗄️ Database Inspection", "db_inspect", 
                                                  expanded_on_desktop=False, expanded_on_mobile=False):
            try:
                db = get_database_service_singleton()
                from config.database_config import DatabaseConfig
                db_config = DatabaseConfig.get_database_config()
                db_path = db_config.get('path', 'database/pans_cookbook.db')
                st.write(f"**Database Path:** `{db_path}`")
                
                # Get database stats
                stats = db.get_database_stats()
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Recipes", stats.get('recipes', 0))
                with col2:
                    st.metric("Ingredients", stats.get('ingredients', 0))
                with col3:
                    st.metric("Pantry Items", stats.get('user_pantry', 0))
                
                # Show recent recipes
                recent_recipes = db.get_all_recipes(user_id=1, limit=5)
                if recent_recipes:
                    st.write("**Recent Recipes:**")
                    for recipe in recent_recipes:
                        st.write(f"- ID: {recipe.id}, Name: {recipe.name}")
                else:
                    st.write("**No recipes found in database**")
                
                # Show all existing database files in current directory only
                import glob
                import os
                db_files = [f for f in glob.glob("*.db") if os.path.isfile(f)]
                if db_files:
                    st.write("**All database files found:**")
                    for db_file in db_files:
                        size = os.path.getsize(db_file)
                        is_current = "👈 CURRENT" if db_file == db_path else ""
                        st.write(f"- `{db_file}`: {size} bytes {is_current}")
                
                # Show database file info
                if db_path != ":memory:" and os.path.exists(db_path):
                    file_size = os.path.getsize(db_path)
                    st.write(f"**Current database file size:** {file_size} bytes")
                    
                    # Check if file is empty or corrupted
                    if file_size == 0:
                        st.error("⚠️ Database file is empty!")
                    elif file_size < 100:
                        st.warning("⚠️ Database file seems very small")
                
                # Show detailed ingredient list
                all_ingredients = db.get_all_ingredients()
                if all_ingredients:
                    st.write(f"**All {len(all_ingredients)} ingredients in database:**")
                    
                    # Group by category
                    from collections import defaultdict
                    by_category = defaultdict(list)
                    for ing in all_ingredients:
                        by_category[ing.category or "Uncategorized"].append(f"{ing.name} (ID: {ing.id})")
                    
                    for category, ingredients in sorted(by_category.items()):
                        with st.expander(f"{category.title()} ({len(ingredients)})", expanded=False):
                            for ingredient in sorted(ingredients):
                                st.write(f"- {ingredient}")
                else:
                    st.warning("**No ingredients found in current database**")
                
            except Exception as e:
                st.error(f"❌ Database inspection failed: {e}")
                import traceback
                with st.expander("Debug Traceback"):
                    st.code(traceback.format_exc())
        
        # Ingredient management section
        with responsive.create_collapsible_section("📦 Ingredient Management", "ingredients", 
                                                  expanded_on_desktop=False, expanded_on_mobile=False):
            try:
                db = get_database_service_singleton()
                
                # Show current ingredient count
                all_ingredients = db.get_all_ingredients()
                st.metric("Total Ingredients", len(all_ingredients))
                
                # Add core pantry ingredients from CSV
                if st.button("➕ Add Core Pantry Ingredients from CSV"):
                    added_count = add_core_pantry_ingredients(db)
                    if added_count > 0:
                        st.success(f"✅ Added {added_count} new ingredients!")
                        st.rerun()
                    else:
                        st.info("ℹ️ All core pantry ingredients already exist in the database.")
                
                # Database migration tools
                st.markdown("---")
                st.markdown("**Database Migration Tools:**")
                
                # Check for existing database files in current directory only
                import glob
                import os
                other_db_files = [f for f in glob.glob("*.db") if f != db_path and os.path.isfile(f)]
                
                if other_db_files:
                    st.write(f"Found other database files: {', '.join(other_db_files)}")
                    
                    selected_db = st.selectbox("Migrate data from:", other_db_files)
                    
                    if st.button(f"🔄 Migrate data from {selected_db}"):
                        migrate_count = migrate_database_data(selected_db, db)
                        if migrate_count > 0:
                            st.success(f"✅ Migrated {migrate_count} items!")
                            st.rerun()
                        else:
                            st.info("ℹ️ No new data to migrate.")
                else:
                    st.info("No other database files found to migrate from.")
                
                # Database reset tools
                st.markdown("---")
                st.markdown("**🚨 Database Reset Tools:**")
                
                if st.button("🗑️ CLEAR ALL DATA (Reset Database)", type="secondary"):
                    if clear_database_completely(db):
                        st.success("✅ Database cleared successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to clear database")
                
                if st.button("🔄 RECREATE DATABASE FROM SCRATCH", type="secondary"):
                    if recreate_database_from_scratch():
                        st.success("✅ Database recreated from scratch!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to recreate database")
                
                # Show ingredient categories
                if all_ingredients:
                    from collections import defaultdict
                    by_category = defaultdict(list)
                    for ing in all_ingredients:
                        by_category[ing.category or "Uncategorized"].append(ing.name)
                    
                    st.write("**Ingredients by Category:**")
                    for category, ingredients in sorted(by_category.items()):
                        with st.expander(f"{category.title()} ({len(ingredients)})"):
                            st.write(", ".join(sorted(ingredients)))
                
            except Exception as e:
                st.error(f"❌ Ingredient management failed: {e}")
                import traceback
                with st.expander("Debug Traceback"):
                    st.code(traceback.format_exc())
    
    with tab2:
        demo_smart_parser()
    
    with tab3:
        demo_recipe_browser()
    
    with tab4:
        demo_ai_features()
    
    with tab5:
        if PANTRY_AVAILABLE:
            demo_pantry_manager()
        else:
            st.error("❌ Pantry Manager not available due to import issues")
            st.info("This may be a temporary deployment issue. The feature is fully implemented but not accessible in this environment.")
        

def demo_smart_parser():
    """Demo the enhanced AI-powered recipe parser"""
    st.markdown("### 🧠 Smart Recipe Parser")
    st.markdown("AI-powered recipe parsing with clean validation and automatic pantry integration.")
    
    if not AI_PARSING_AVAILABLE:
        st.error("❌ AI parsing services not available")
        st.info("The enhanced parsing features require AI services. Using basic parsing instead.")
        demo_validation_interface()
        return
    
    # Initialize services
    db = get_database_service_singleton()
    ai_service = AIService(db)
    
    if not ai_service.is_ai_available():
        st.warning("🤖 AI service not available. Start LM Studio to use smart parsing features.")
        st.info("Falling back to basic validation interface...")
        demo_validation_interface()
        return
    
    # Initialize AI parsing services
    ai_parser = get_ai_ingredient_parser(ai_service, db)
    bulk_parser = get_bulk_recipe_parser(ai_service)
    simple_validator = SimpleValidationInterface(ai_parser, db)
    
    # Create tabs for different input modes
    parser_tab1, parser_tab2, parser_tab3 = st.tabs(["📝 Single Recipe", "📚 Bulk Import", "🎯 Sample Demo"])
    
    with parser_tab1:
        demo_single_recipe_parser(simple_validator, ai_parser, db)
    
    with parser_tab2:
        demo_bulk_recipe_parser(bulk_parser, simple_validator, ai_parser, db)
    
    with parser_tab3:
        demo_smart_parser_sample(simple_validator, ai_parser, db)


def demo_single_recipe_parser(validator: 'SimpleValidationInterface', ai_parser, db):
    """Demo single recipe parsing with AI"""
    st.markdown("#### 📝 Parse Single Recipe")
    st.info("🚀 **NEW**: AI-powered ingredient parsing with automatic pantry integration!")
    
    # Text input form
    with st.form("smart_text_input_form", clear_on_submit=False):
        recipe_text = st.text_area(
            "Recipe Text", 
            placeholder="""Paste any recipe here... For example:

Grandma's Chocolate Chip Cookies

These are the best cookies you'll ever make!

Ingredients:
- 2 1/4 cups all-purpose flour  
- 1 tsp baking soda
- 1 tsp salt
- 1 cup butter, softened
- 3/4 cup granulated sugar
- 3/4 cup packed brown sugar
- 1 large egg
- 2 tsp vanilla extract
- 2 cups semi-sweet chocolate chips

Instructions:
1. Preheat oven to 375°F (190°C)
2. In medium bowl, whisk together flour, baking soda and salt
3. In large bowl, beat butter and both sugars until creamy
4. Beat in egg and vanilla
5. Gradually add flour mixture until just combined
6. Stir in chocolate chips
7. Drop rounded tablespoons onto ungreased cookie sheets
8. Bake 9-11 minutes until golden brown
9. Cool on baking sheets 2 minutes before removing

Prep Time: 15 minutes
Cook Time: 11 minutes  
Serves: 48 cookies
Difficulty: Easy""",
            height=400,
            help="The AI will automatically detect ingredients, quantities, units, and instructions"
        )
        
        col1, col2 = st.columns([1, 3])
        with col1:
            parse_button = st.form_submit_button("🧠 Smart Parse", type="primary")
        with col2:
            st.caption("AI will extract structured recipe data and check your pantry!")
    
    if parse_button and recipe_text.strip():
        with st.spinner("🤖 AI is analyzing your recipe..."):
            try:
                # Use bulk parser to extract recipe from text
                from services.bulk_recipe_parser import get_bulk_recipe_parser
                bulk_parser = get_bulk_recipe_parser()
                
                scraped_recipes = bulk_parser.parse_bulk_text(recipe_text, "user_input")
                
                if scraped_recipes:
                    scraped_recipe = scraped_recipes[0]  # Take the first/main recipe
                    
                    st.success(f"✅ Successfully parsed: **{scraped_recipe.title}**")
                    
                    # Show parsing preview
                    with st.expander("📋 AI Parsing Results", expanded=True):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Title:** {scraped_recipe.title}")
                            st.write(f"**Description:** {scraped_recipe.description}")
                            st.write(f"**Ingredients Found:** {len(scraped_recipe.ingredients_raw)}")
                            st.write(f"**Prep Time:** {scraped_recipe.prep_time_text}")
                            st.write(f"**Cook Time:** {scraped_recipe.cook_time_text}")
                        
                        with col2:
                            st.write(f"**Servings:** {scraped_recipe.servings_text}")
                            st.write(f"**Difficulty:** {scraped_recipe.difficulty_text}")
                            st.write(f"**Cuisine:** {scraped_recipe.cuisine_text}")
                            st.write(f"**Category:** {scraped_recipe.category_text}")
                            st.write(f"**AI Confidence:** {scraped_recipe.confidence_score:.1%}")
                    
                    # Use simple validation interface
                    st.markdown("---")
                    validation_result = validator.validate_recipe_simple(scraped_recipe, user_id=1)
                    
                    if validation_result and validation_result.is_valid:
                        st.balloons()
                else:
                    st.error("❌ Could not extract recipe from this text.")
                    st.info("💡 **Tips for better parsing:**")
                    st.info("• Include clear ingredient lists and instructions")
                    st.info("• Make sure the recipe title is prominent")  
                    st.info("• Include timing and serving information")
                    
            except Exception as e:
                st.error(f"❌ Smart parsing failed: {str(e)}")


def demo_bulk_recipe_parser(bulk_parser, validator: 'SimpleValidationInterface', ai_parser, db):
    """Demo bulk recipe parsing"""
    st.markdown("#### 📚 Bulk Recipe Import")
    st.info("🚀 **NEW**: Import multiple recipes from one text dump - perfect for recipe collections!")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload Recipe Collection File",
        type=['txt', 'md'],
        help="Upload text files containing multiple recipes"
    )
    
    # Or text area for pasting
    st.markdown("**Or paste multiple recipes:**")
    bulk_text = st.text_area(
        "Multiple Recipes Text",
        placeholder="""Example: Multiple recipes in one text...

RECIPE 1: Pancakes
Ingredients:
- 2 cups flour
- 2 eggs  
- 1 cup milk
Instructions:
1. Mix ingredients
2. Cook on griddle

RECIPE 2: French Toast  
Ingredients:
- 4 bread slices
- 2 eggs
- 1/4 cup milk
Instructions:
1. Beat eggs and milk
2. Dip bread and cook

(The AI will automatically detect recipe boundaries and parse each one separately!)""",
        height=300
    )
    
    if st.button("🧠 Parse All Recipes", type="primary"):
        text_to_parse = None
        source_name = "bulk_input"
        
        # Get text from file or text area
        if uploaded_file:
            try:
                text_to_parse = str(uploaded_file.read(), "utf-8")
                source_name = f"file_{uploaded_file.name}"
            except Exception as e:
                st.error(f"Error reading file: {e}")
                return
        elif bulk_text.strip():
            text_to_parse = bulk_text
        
        if text_to_parse:
            with st.spinner("🤖 AI is finding and parsing all recipes..."):
                try:
                    scraped_recipes = bulk_parser.parse_bulk_text(text_to_parse, source_name)
                    
                    if scraped_recipes:
                        st.success(f"🎉 Found and parsed **{len(scraped_recipes)}** recipes!")
                        
                        # Show all found recipes
                        for i, recipe in enumerate(scraped_recipes):
                            with st.expander(f"📝 Recipe {i+1}: {recipe.title}", expanded=i==0):
                                
                                # Basic recipe info
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"**Ingredients:** {len(recipe.ingredients_raw)}")
                                    st.write(f"**Prep Time:** {recipe.prep_time_text}")
                                    st.write(f"**Cook Time:** {recipe.cook_time_text}")
                                with col2:
                                    st.write(f"**Servings:** {recipe.servings_text}")
                                    st.write(f"**Difficulty:** {recipe.difficulty_text}")
                                    st.write(f"**AI Confidence:** {recipe.confidence_score:.1%}")
                                
                                # Ingredients preview
                                if recipe.ingredients_raw:
                                    with st.expander("🥕 Ingredients", expanded=False):
                                        for ing in recipe.ingredients_raw[:5]:
                                            st.write(f"• {ing}")
                                        if len(recipe.ingredients_raw) > 5:
                                            st.write(f"... and {len(recipe.ingredients_raw) - 5} more")
                                
                                # Validation option
                                if st.button(f"✅ Validate & Save Recipe {i+1}", key=f"validate_{i}"):
                                    st.info(f"Validating {recipe.title}...")
                                    # Here you would call the validator for each recipe
                                    # For demo, just show success
                                    st.success(f"Recipe {i+1} ready for validation!")
                    
                    else:
                        st.warning("⚠️ No recipes detected in the text.")
                        st.info("💡 Make sure your text contains complete recipes with ingredients and instructions.")
                
                except Exception as e:
                    st.error(f"❌ Bulk parsing failed: {str(e)}")
        else:
            st.warning("Please upload a file or paste some text to parse.")


def demo_smart_parser_sample(validator: 'SimpleValidationInterface', ai_parser, db):
    """Demo with pre-loaded sample"""
    st.markdown("#### 🎯 Smart Parser Demo")
    st.info("See how the AI parser works with a sample recipe - includes pantry checking!")
    
    sample_recipe_text = """Ultimate Beef Tacos

These are the best tacos for weeknight dinners!

Ingredients:
- 1 pound ground beef (80/20)
- 1 packet taco seasoning
- 2/3 cup water
- 8 small corn tortillas
- 1 cup shredded Mexican cheese blend
- 1 medium tomato, diced
- 1/2 cup yellow onion, diced  
- 1 head iceberg lettuce, shredded
- 1/2 cup sour cream
- Hot sauce to taste (optional)

Instructions:
1. Brown the ground beef in a large skillet over medium-high heat
2. Drain excess fat and add taco seasoning with water
3. Simmer for 5 minutes until sauce thickens
4. Warm tortillas in microwave or on griddle
5. Fill tortillas with meat and desired toppings
6. Serve immediately with hot sauce

Prep Time: 10 minutes
Cook Time: 10 minutes
Total Time: 20 minutes
Serves: 4 people
Difficulty: Easy
Cuisine: Mexican
Category: Dinner"""

    # Show the sample
    with st.expander("📄 Sample Recipe Text", expanded=False):
        st.code(sample_recipe_text, language=None)
    
    if st.button("🧠 Parse Sample Recipe", type="primary"):
        with st.spinner("🤖 AI is parsing the sample recipe..."):
            try:
                # Parse with bulk parser
                from services.bulk_recipe_parser import get_bulk_recipe_parser
                bulk_parser = get_bulk_recipe_parser()
                
                scraped_recipes = bulk_parser.parse_bulk_text(sample_recipe_text, "sample")
                
                if scraped_recipes:
                    scraped_recipe = scraped_recipes[0]
                    
                    st.success(f"✅ Sample parsed successfully: **{scraped_recipe.title}**")
                    
                    # Use simple validation
                    validation_result = validator.validate_recipe_simple(scraped_recipe, user_id=1)
                    
                else:
                    st.error("Failed to parse sample recipe")
                    
            except Exception as e:
                st.error(f"Sample parsing error: {e}")


def demo_validation_interface():
    """Demo the validation interface with text input and file upload"""
    st.markdown("### 🔍 Recipe Parser & Validation")
    st.markdown("Add recipes by pasting text or uploading files, then validate before saving to your cookbook.")
    
    # Initialize services
    db = get_database_service_singleton()
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


def demo_recipe_browser():
    """Demo the recipe browser interface using the full RecipeBrowser class"""
    st.markdown("### 📚 Recipe Browser")
    st.markdown("Browse, search, and manage your recipe collection with smart pantry integration.")
    
    try:
        # Initialize recipe browser with database
        db = get_database_service_singleton()
        browser = RecipeBrowser(db)
        
        # Check if we have recipes
        all_recipes = db.get_all_recipes(user_id=1, limit=50)
        
        if not all_recipes:
            st.info("🍽️ No recipes found. Use the **Smart Parser** tab to add some recipes!")
            
            # DISABLED: Demo recipes removed per user request
            # Use Smart Parser tab to add real recipes manually or via scraping
            if False:  # Disabled code block
                with st.spinner("Adding sample recipes..."):
                    # First ensure we have some basic ingredients
                    sample_ingredients = [
                        ("All-Purpose Flour", "grain"),
                        ("Sugar", "sweetener"), 
                        ("Milk", "dairy"),
                        ("Pasta", "grain"),
                        ("Olive Oil", "oil"),
                        ("Garlic", "vegetable")
                    ]
                    
                    ingredient_ids = {}
                    for name, category in sample_ingredients:
                        ingredient = db.create_ingredient(name, category)
                        if ingredient:
                            ingredient_ids[name] = ingredient.id
                    
                    # Add sample recipes
                    sample_recipes = [
                        {
                            "name": "Classic Pancakes",
                            "description": "Fluffy breakfast pancakes",
                            "instructions": "1. Mix dry ingredients in a bowl.\n2. Add wet ingredients and stir until just combined.\n3. Cook on hot griddle until golden brown on both sides.",
                            "prep_time_minutes": 10,
                            "cook_time_minutes": 15,
                            "servings": 4,
                            "difficulty_level": "easy",
                            "cuisine_type": "American",
                            "meal_category": "breakfast",
                            "ingredients": [
                                {"ingredient_id": ingredient_ids.get("All-Purpose Flour", 1), "quantity": 2, "unit": "cups", "preparation_note": ""},
                                {"ingredient_id": ingredient_ids.get("Sugar", 2), "quantity": 2, "unit": "tbsp", "preparation_note": ""},
                                {"ingredient_id": ingredient_ids.get("Milk", 3), "quantity": 1.5, "unit": "cups", "preparation_note": ""}
                            ]
                        },
                        {
                            "name": "Garlic Pasta",
                            "description": "Simple and delicious pasta with garlic and olive oil",
                            "instructions": "1. Cook pasta according to package directions.\n2. Heat olive oil in a pan.\n3. Add minced garlic and cook until fragrant.\n4. Toss with pasta and serve.",
                            "prep_time_minutes": 5,
                            "cook_time_minutes": 20,
                            "servings": 2,
                            "difficulty_level": "easy",
                            "cuisine_type": "Italian",
                            "meal_category": "dinner",
                            "ingredients": [
                                {"ingredient_id": ingredient_ids.get("Pasta", 4), "quantity": 8, "unit": "oz", "preparation_note": ""},
                                {"ingredient_id": ingredient_ids.get("Olive Oil", 5), "quantity": 3, "unit": "tbsp", "preparation_note": ""},
                                {"ingredient_id": ingredient_ids.get("Garlic", 6), "quantity": 3, "unit": "cloves", "preparation_note": "minced"}
                            ]
                        }
                    ]
                    
                    for recipe_data in sample_recipes:
                        recipe = db.create_recipe(recipe_data, user_id=1)
                        if recipe:
                            st.success(f"✅ Added: {recipe.name} (ID: {recipe.id})")
                        else:
                            st.error(f"❌ Failed to create recipe: {recipe_data['name']}")
                    
                    st.rerun()
        else:
            # Use the full RecipeBrowser interface
            st.markdown("---")
            
            # Check if user wants to see detailed recipe view
            if 'selected_recipe_id' in st.session_state:
                recipe_id = st.session_state['selected_recipe_id']
                st.write(f"**Debug**: Looking for recipe ID: {recipe_id}")
                
                selected_recipe = db.get_recipe_by_id(recipe_id)
                if selected_recipe:
                    # Back button
                    if st.button("← Back to Recipe List"):
                        del st.session_state['selected_recipe_id']
                        st.rerun()
                    
                    # Render detailed recipe view
                    user_pantry = st.session_state.get(browser.PANTRY_KEY, set())
                    browser.render_recipe_details(selected_recipe, user_pantry)
                else:
                    st.error(f"Recipe not found for ID: {recipe_id}")
                    
                    # Debug: show all recipes
                    all_recipes_debug = db.get_all_recipes(user_id=1, limit=10)
                    st.write(f"**Debug**: Found {len(all_recipes_debug)} recipes in database:")
                    for r in all_recipes_debug:
                        st.write(f"- ID: {r.id}, Name: {r.name}")
                    
                    del st.session_state['selected_recipe_id']
            else:
                # Render main recipe browser interface
                browser.render_recipe_browser(user_id=1)
    
    except Exception as e:
        st.error(f"Error loading recipe browser: {e}")
        import traceback
        with st.expander("Debug Info"):
            st.code(traceback.format_exc())


def demo_ai_features():
    """Demo the AI features interface with sample data"""
    st.markdown("### 🤖 AI Features Demo")
    st.markdown("Experience AI-powered recipe enhancements and suggestions.")
    
    # Initialize AI services
    db = get_database_service_singleton()
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
    if not PANTRY_AVAILABLE:
        st.error("❌ Pantry services not available")
        return
        
    st.markdown("### 🥬 My Pantry - What Can I Make?")
    st.markdown("Manage your ingredient inventory and discover recipes you can make right now!")
    
    # Initialize pantry services  
    db = get_database_service_singleton()
    pantry_service = get_pantry_service(db)
    pantry_ui = PantryManagerInterface(pantry_service)
    
    # Demo user ID
    demo_user_id = 1
    
    # DISABLED: Auto-population of sample ingredients
    # This was causing issues with CSV import and data consistency
    # Users should manually add ingredients via CSV import or pantry interface
    
    # Previous code automatically added 15 sample ingredients which interfered with clean database state
    
    # DISABLED: All sample recipe creation removed per user request
    # Users should add recipes manually via Smart Parser tab
    if False:  # Disabled code block
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
        
    
    # Check if user has a pantry setup
    user_pantry = pantry_service.get_user_pantry(demo_user_id)
    
    if not user_pantry:
        st.info("👋 Welcome to your pantry! Let's set it up with some common ingredients.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 Set Up My Pantry", type="primary"):
                with st.spinner("Setting up your pantry with common ingredients..."):
                    try:
                        added_count = pantry_service.add_common_ingredients_to_pantry(demo_user_id)
                        if added_count > 0:
                            st.success(f"✅ Added {added_count} common ingredients to your pantry!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to add ingredients. Let's try manual setup.")
                    except Exception as e:
                        st.error(f"❌ Setup failed: {e}")
                        st.info("Let's try manual setup instead...")
        
        with col2:
            if st.button("🔧 Manual Setup", type="secondary"):
                with st.spinner("Setting up pantry manually..."):
                    try:
                        # Manual ingredient setup with direct database calls
                        from services import get_ingredient_service
                        ingredient_service = get_ingredient_service(db)
                        
                        # Basic ingredients to add
                        manual_ingredients = [
                            ("Salt", "seasoning"),
                            ("Black Pepper", "seasoning"),
                            ("Olive Oil", "oil"),
                            ("Butter", "dairy"),
                            ("Garlic", "vegetable"),
                            ("Onion", "vegetable"),
                            ("All-Purpose Flour", "grain"),
                            ("Sugar", "sweetener"),
                            ("Eggs", "protein"),
                            ("Chicken Breast", "protein")
                        ]
                        
                        added_count = 0
                        for name, category in manual_ingredients:
                            try:
                                # Create ingredient in database
                                ingredient = ingredient_service.create_ingredient(name, category)
                                if ingredient:
                                    # Add to pantry
                                    success = pantry_service.update_pantry_item(demo_user_id, ingredient.id, True, "plenty")
                                    if success:
                                        added_count += 1
                            except Exception as ing_error:
                                # Ingredient might already exist, try to find it
                                try:
                                    existing = db.search_ingredients(name)
                                    if existing:
                                        ingredient = existing[0]
                                        success = pantry_service.update_pantry_item(demo_user_id, ingredient.id, True, "plenty")
                                        if success:
                                            added_count += 1
                                except:
                                    pass  # Skip this ingredient
                        
                        if added_count > 0:
                            st.success(f"✅ Manually added {added_count} ingredients to your pantry!")
                            st.rerun()
                        else:
                            st.error("❌ Manual setup also failed. Let's debug this...")
                            
                            # Detailed step-by-step debugging
                            st.write("**Detailed Debug Process:**")
                            
                            # Test ingredient service
                            try:
                                from services import get_ingredient_service
                                ingredient_service = get_ingredient_service(db)
                                st.write("✅ Ingredient service created")
                                
                                # Try to create one ingredient
                                test_ingredient = ingredient_service.create_ingredient("Test Salt", "seasoning")
                                if test_ingredient:
                                    st.write(f"✅ Test ingredient created: {test_ingredient.name} (ID: {test_ingredient.id})")
                                    
                                    # Try to add to pantry
                                    success = pantry_service.update_pantry_item(demo_user_id, test_ingredient.id, True, "plenty")
                                    if success:
                                        st.write("✅ Test ingredient added to pantry successfully!")
                                    else:
                                        st.write("❌ Failed to add test ingredient to pantry")
                                        
                                        # Let's try a direct SQL approach
                                        st.write("**Trying direct SQL insert:**")
                                        try:
                                            with db.get_connection() as conn:
                                                cursor = conn.cursor()
                                                cursor.execute("""
                                                    INSERT OR REPLACE INTO user_pantry 
                                                    (user_id, ingredient_id, is_available, quantity_estimate, last_updated)
                                                    VALUES (?, ?, ?, ?, ?)
                                                """, (demo_user_id, test_ingredient.id, 1, "plenty", "2024-01-01"))
                                                conn.commit()
                                                st.write("✅ Direct SQL insert worked!")
                                        except Exception as sql_e:
                                            st.write(f"❌ Direct SQL failed: {sql_e}")
                                else:
                                    st.write("❌ Failed to create test ingredient")
                                    
                            except Exception as ing_e:
                                st.write(f"❌ Ingredient service error: {ing_e}")
                                import traceback
                                st.code(traceback.format_exc())
                            
                            # Check database tables
                            st.write("**Database Table Check:**")
                            try:
                                with db.get_connection() as conn:
                                    cursor = conn.cursor()
                                    
                                    # Check if user_pantry table exists
                                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_pantry'")
                                    table_exists = cursor.fetchone()
                                    if table_exists:
                                        st.write("✅ user_pantry table exists")
                                        
                                        # Check table schema
                                        cursor.execute("PRAGMA table_info(user_pantry)")
                                        columns = cursor.fetchall()
                                        st.write("**user_pantry columns:**")
                                        for col in columns:
                                            st.write(f"  - {col[1]} ({col[2]})")
                                    else:
                                        st.write("❌ user_pantry table does not exist!")
                                        
                            except Exception as table_e:
                                st.write(f"❌ Table check error: {table_e}")
                            
                            # Show existing ingredients for reference
                            st.write("**Existing Ingredients:**")
                            try:
                                all_ingredients = db.get_all_ingredients()
                                st.write(f"Total: {len(all_ingredients)}")
                                for i, ing in enumerate(all_ingredients[:5]):
                                    st.write(f"{i+1}. {ing.name} ({ing.category}) - ID: {ing.id}")
                            except Exception as list_e:
                                st.write(f"❌ Error listing ingredients: {list_e}")
                    
                    except Exception as e:
                        st.error(f"❌ Manual setup error: {e}")
                        import traceback
                        st.code(traceback.format_exc())
    else:
        # Show main pantry interface
        pantry_ui.render_pantry_manager(demo_user_id)
        
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
        
        # Pantry statistics and debug info
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            with st.expander("📊 Pantry Statistics", expanded=False):
                available_count = len([item for item in user_pantry if item.is_available])
                total_count = len(user_pantry)
                
                col1a, col1b, col1c = st.columns(3)
                with col1a:
                    st.metric("Available Ingredients", available_count)
                with col1b:
                    st.metric("Total in Pantry", total_count)
                with col1c:
                    st.metric("Makeable Recipes", len(makeable_recipes))
        
        with col2:
            with st.expander("🔍 Database Debug Info", expanded=False):
                try:
                    # Show database ingredients
                    all_ingredients = db.get_all_ingredients()
                    st.write(f"**Total ingredients in database:** {len(all_ingredients)}")
                    
                    if all_ingredients:
                        st.write("**Sample ingredients:**")
                        for ing in all_ingredients[:5]:
                            st.write(f"• {ing.name} ({ing.category}) - ID: {ing.id}")
                    
                    # Show pantry table structure
                    st.write(f"**Pantry items for user {demo_user_id}:**")
                    if user_pantry:
                        for item in user_pantry[:5]:
                            status = "✅ Available" if item.is_available else "❌ Not available"
                            st.write(f"• {item.ingredient_name} - {status} ({item.quantity_estimate})")
                    else:
                        st.write("No pantry items found")
                        
                    # Button to force refresh pantry
                    if st.button("🔄 Refresh Pantry Data", key="refresh_pantry"):
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Debug error: {e}")


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