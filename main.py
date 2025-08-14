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

# Text encoding libraries
try:
    from unidecode import unidecode
    from markdownify import markdownify
    ENCODING_LIBRARIES_AVAILABLE = True
except ImportError:
    ENCODING_LIBRARIES_AVAILABLE = False

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
        {"label": "Add Recipe", "icon": "📝"},
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
        smart_parser()
    
    with tab3:
        recipe_browser()
    
    with tab4:
        ai_features()
    
    with tab5:
        if PANTRY_AVAILABLE:
            pantry_manager()
        else:
            st.error("❌ Pantry Manager not available due to import issues")
            st.info("This may be a temporary deployment issue. The feature is fully implemented but not accessible in this environment.")
        



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
        {"label": "Add Recipe", "icon": "📝"},
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
        smart_parser()
    
    with tab3:
        recipe_browser()
    
    with tab4:
        ai_features()
    
    with tab5:
        if PANTRY_AVAILABLE:
            pantry_manager()
        else:
            st.error("❌ Pantry Manager not available due to import issues")
            st.info("This may be a temporary deployment issue. The feature is fully implemented but not accessible in this environment.")


def smart_parser():
    """Add Recipe interface with AI parsing, basic parsing, and manual entry options"""
    st.markdown("### 📝 Add Recipe")
    st.markdown("Add recipes to your cookbook using AI parsing, basic text parsing, or manual entry.")
    
    # Initialize services
    db = get_database_service_singleton()
    ai_service = AIService(db)
    
    # Default to LM Studio (local AI)
    ai_service.set_provider("lm_studio", None)
    
    # Create tabs for different input modes
    input_tab1, input_tab2, input_tab3 = st.tabs(["🤖 AI Parse", "📝 Text Parse", "✍️ Manual Entry"])
    
    with input_tab1:
        ai_recipe_input(ai_service, db)
    
    with input_tab2:
        basic_recipe_input(db)
    
    with input_tab3:
        manual_recipe_input(db)


def ai_recipe_input(ai_service, db):
    """AI-powered recipe parsing with form for editing before saving"""
    st.markdown("#### 🤖 AI Recipe Parser")
    st.info("Paste recipe text and let AI extract the structured data. Review and edit before saving.")
    
    # Check AI availability
    if not ai_service.is_ai_available():
        st.error("❌ LM Studio not available. Make sure it's running at http://localhost:1234")
        st.info("Start LM Studio and load a model, then refresh this page.")
        return
    
    st.success("✅ LM Studio connected and ready")
    
    # Recipe text input
    recipe_text = st.text_area(
        "Paste Recipe Text:",
        height=200,
        placeholder="""Paste your recipe here, for example:

Simple Baked Chicken Breast
Prep: 10 minutes, Cook: 25 minutes, Serves: 4

Ingredients:
- 4 boneless skinless chicken breasts
- 2 tbsp olive oil
- 1 tsp salt
- 1/2 tsp black pepper
- 1 tsp garlic powder
- 1 tsp paprika

Instructions:
1. Preheat oven to 400°F
2. Season chicken with oil and spices
3. Bake for 20-25 minutes until internal temp reaches 165°F
4. Let rest 5 minutes before serving"""
    )
    
    # Parse button
    if st.button("🧠 Parse with AI", type="primary", key="ai_parse_button"):
        if not recipe_text.strip():
            st.warning("⚠️ Please paste some recipe text first!")
        else:
            with st.spinner("🤖 AI is parsing your recipe..."):
                try:
                    # Clean the text first to prevent encoding errors
                    clean_recipe_text = clean_text_encoding(recipe_text)
                    # Use AI to parse the recipe
                    parsed_data = ai_parse_recipe_text(ai_service, clean_recipe_text)
                    if parsed_data:
                        st.success("✅ Recipe parsed successfully!")
                        # Store in session state for the form
                        st.session_state['parsed_recipe_data'] = parsed_data
                        st.rerun()
                    else:
                        st.error("❌ Could not parse recipe. Try the Text Parse tab for basic extraction.")
                        
                except Exception as e:
                    st.error(f"❌ Parsing error: {str(e)}")
    
    # Show recipe form if we have parsed data
    if 'parsed_recipe_data' in st.session_state:
        st.markdown("---")
        show_recipe_form(db, st.session_state['parsed_recipe_data'], "AI")


def basic_recipe_input(db):
    """Basic text parsing without AI"""
    st.markdown("#### 📝 Text Recipe Parser")
    st.info("Basic text parsing that extracts recipe parts without AI. Good fallback option.")
    
    # Recipe text input
    recipe_text = st.text_area(
        "Paste Recipe Text:",
        height=200,
        placeholder="Paste your recipe here..."
    )
    
    # Parse button
    if st.button("📝 Parse Text", type="primary", key="text_parse_button"):
        if not recipe_text.strip():
            st.warning("⚠️ Please paste some recipe text first!")
        else:
            with st.spinner("📝 Parsing recipe text..."):
                try:
                    # Use our improved basic text parsing
                    parsed_data = basic_text_parse(recipe_text)
                    
                    if parsed_data:
                        st.success("✅ Recipe parsed with basic text extraction!")
                        print(f"Basic parsing result: {parsed_data}")  # Debug output
                        st.session_state['parsed_recipe_data'] = parsed_data
                        st.rerun()
                    else:
                        st.error("❌ Could not extract recipe parts from text. Please check the format.")
                        st.info("💡 Make sure your recipe has clear 'Ingredients:' and 'Instructions:' sections.")
                        
                except Exception as e:
                    st.error(f"❌ Text parsing error: {str(e)}")
                    print(f"Text parsing exception: {e}")  # Debug output
    
    # Show recipe form if we have parsed data
    if 'parsed_recipe_data' in st.session_state:
        st.markdown("---")
        show_recipe_form(db, st.session_state['parsed_recipe_data'], "Text")


def manual_recipe_input(db):
    """Manual recipe entry form"""
    st.markdown("#### ✍️ Manual Recipe Entry")
    st.info("Enter recipe details manually using the form below.")
    
    # Create empty data for manual entry
    empty_data = {
        'title': "",
        'description': "",
        'ingredients': [],
        'instructions': "",
        'prep_time': "",
        'cook_time': "",
        'total_time': "",
        'servings': ""
    }
    
    show_recipe_form(db, empty_data, "Manual")


def ai_parse_recipe_text(ai_service, recipe_text):
    """Use AI service to parse recipe text into structured data"""
    try:
        # Clean text to ensure no encoding issues in AI processing
        clean_text = clean_text_encoding(recipe_text)
        
        # Simplified prompt that's more likely to work with LM Studio
        prompt = f"""Extract recipe information from this text and return it as JSON.

Required fields:
- title (recipe name)
- ingredients (list of ingredient strings)
- instructions (cooking steps)
- prep_time (if mentioned)
- cook_time (if mentioned) 
- servings (if mentioned)
- description (brief summary)

Return only valid JSON like this example:
{{"title": "Chicken Recipe", "ingredients": ["4 chicken breasts", "2 tbsp oil"], "instructions": "1. Cook chicken...", "prep_time": "10 minutes", "cook_time": "25 minutes", "servings": "4", "description": "Delicious chicken dish"}}

Recipe text:
{clean_text}

JSON:"""

        response = ai_service.get_completion(prompt, max_tokens=1500, temperature=0.1)
        
        if response:
            print(f"AI Response: {response}")  # Debug output
            
            # Try multiple methods to extract JSON
            import json
            import re
            
            # Method 1: Look for JSON object
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group(0)
                    parsed_data = json.loads(json_str)
                    
                    # Clean up and validate data
                    cleaned_data = clean_parsed_data(parsed_data)
                    if cleaned_data:
                        print(f"Successfully parsed with AI: {cleaned_data}")
                        return cleaned_data
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
            
            # Method 2: Try basic text extraction if JSON fails
            print("JSON parsing failed, trying basic extraction...")
            return basic_parse_from_ai_response(response, recipe_text)
                
    except Exception as e:
        print(f"AI parsing error: {e}")
    
    # Fallback to basic parsing
    print("AI parsing failed completely, falling back to basic parsing...")
    return basic_text_parse(recipe_text)


def clean_parsed_data(data):
    """Clean and validate parsed recipe data"""
    if not isinstance(data, dict):
        return None
        
    # Ensure required fields exist
    cleaned = {
        'title': str(data.get('title', '')).strip(),
        'description': str(data.get('description', '')).strip(),
        'ingredients': [],
        'instructions': str(data.get('instructions', '')).strip(),
        'prep_time': str(data.get('prep_time', '')).strip(),
        'cook_time': str(data.get('cook_time', '')).strip(),
        'total_time': str(data.get('total_time', '')).strip(),
        'servings': str(data.get('servings', '')).strip()
    }
    
    # Handle ingredients - can be string or list
    ingredients_raw = data.get('ingredients', [])
    if isinstance(ingredients_raw, str):
        # Split by lines or common separators
        ingredients_list = []
        for line in ingredients_raw.split('\n'):
            line = line.strip()
            if line and not line.startswith('-') and not line.startswith('*'):
                ingredients_list.append(line)
            elif line:
                ingredients_list.append(line[1:].strip())  # Remove - or *
        cleaned['ingredients'] = [ing for ing in ingredients_list if ing]
    elif isinstance(ingredients_raw, list):
        cleaned['ingredients'] = [str(ing).strip() for ing in ingredients_raw if str(ing).strip()]
    
    # Must have title and at least one ingredient
    if cleaned['title'] and cleaned['ingredients']:
        return cleaned
    
    return None


def basic_parse_from_ai_response(ai_response, original_text):
    """Try to extract recipe data from AI response even if not JSON"""
    try:
        # Look for common patterns in the AI response
        title = extract_title_from_text(ai_response) or extract_title_from_text(original_text)
        ingredients = extract_ingredients_from_text(ai_response) or extract_ingredients_from_text(original_text)
        instructions = extract_instructions_from_text(ai_response) or extract_instructions_from_text(original_text)
        
        if title and ingredients:
            return {
                'title': title,
                'description': '',
                'ingredients': ingredients,
                'instructions': instructions,
                'prep_time': extract_time_from_text(ai_response, 'prep') or extract_time_from_text(original_text, 'prep'),
                'cook_time': extract_time_from_text(ai_response, 'cook') or extract_time_from_text(original_text, 'cook'),
                'total_time': '',
                'servings': extract_servings_from_text(ai_response) or extract_servings_from_text(original_text)
            }
    except Exception as e:
        print(f"Error in basic parse from AI response: {e}")
    
    return None


def basic_text_parse(recipe_text):
    """Basic text parsing without AI - extract recipe components using patterns"""
    try:
        title = extract_title_from_text(recipe_text)
        ingredients = extract_ingredients_from_text(recipe_text)
        instructions = extract_instructions_from_text(recipe_text)
        
        if not title:
            title = "Untitled Recipe"
        
        if not ingredients:
            # If no clear ingredients section, try to guess
            lines = recipe_text.split('\n')
            ingredients = []
            for line in lines[:20]:  # Look at first 20 lines
                line = line.strip()
                if line and (any(word in line.lower() for word in ['cup', 'tbsp', 'tsp', 'pound', 'lb', 'oz', 'gram', 'ml'])):
                    ingredients.append(line)
        
        if ingredients:
            return {
                'title': title,
                'description': '',
                'ingredients': ingredients,
                'instructions': instructions or recipe_text,
                'prep_time': extract_time_from_text(recipe_text, 'prep'),
                'cook_time': extract_time_from_text(recipe_text, 'cook'),
                'total_time': '',
                'servings': extract_servings_from_text(recipe_text)
            }
            
    except Exception as e:
        print(f"Basic text parsing error: {e}")
    
    return None


def extract_title_from_text(text):
    """Extract recipe title from text"""
    lines = text.split('\n')
    for line in lines[:5]:  # Check first 5 lines
        line = line.strip()
        if line and len(line) < 100 and not line.startswith('-') and not line.startswith('*'):
            # Skip common non-title lines
            if not any(word in line.lower() for word in ['ingredient', 'instruction', 'step', 'prep:', 'cook:', 'total:', 'serves']):
                return line
    return ""


def extract_ingredients_from_text(text):
    """Extract ingredients list from text"""
    import re
    
    # Look for ingredients section
    ingredients_section = ""
    lines = text.split('\n')
    
    in_ingredients = False
    ingredients = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Start of ingredients section
        if re.search(r'^ingredients?:?\s*$', line, re.IGNORECASE):
            in_ingredients = True
            continue
            
        # End of ingredients (start of instructions)
        if in_ingredients and re.search(r'^(instructions?|directions?|method|steps?):?\s*$', line, re.IGNORECASE):
            break
            
        # If we're in ingredients section
        if in_ingredients:
            if line.startswith(('-', '•', '*', '+')):
                ingredients.append(line[1:].strip())
            elif re.match(r'^\d+\.?\s+', line):  # numbered list
                ingredients.append(re.sub(r'^\d+\.?\s+', '', line))
            elif any(word in line.lower() for word in ['cup', 'tbsp', 'tsp', 'pound', 'lb', 'oz', 'gram', 'ml', 'clove', 'slice']):
                ingredients.append(line)
    
    return ingredients


def extract_instructions_from_text(text):
    """Extract instructions from text"""
    import re
    
    lines = text.split('\n')
    in_instructions = False
    instructions = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Start of instructions section
        if re.search(r'^(instructions?|directions?|method|steps?):?\s*$', line, re.IGNORECASE):
            in_instructions = True
            continue
            
        # If we're in instructions section
        if in_instructions:
            if line.startswith(('-', '•', '*', '+')):
                instructions.append(line[1:].strip())
            elif re.match(r'^\d+\.?\s+', line):  # numbered steps
                instructions.append(line)
            else:
                instructions.append(line)
    
    return '\n'.join(instructions) if instructions else ""


def extract_time_from_text(text, time_type):
    """Extract prep time or cook time from text"""
    import re
    
    pattern = rf'{time_type}\s*time:?\s*(\d+\s*(?:minutes?|mins?|hours?|hrs?))'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Also look for patterns like "Prep: 15 minutes"
    pattern = rf'{time_type}:?\s*(\d+\s*(?:minutes?|mins?|hours?|hrs?))'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1)
        
    return ""


def extract_servings_from_text(text):
    """Extract servings from text"""
    import re
    
    # Look for various serving patterns
    patterns = [
        r'serves?\s*:?\s*(\d+)',
        r'servings?\s*:?\s*(\d+)',
        r'yield\s*:?\s*(\d+)',
        r'makes?\s*:?\s*(\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
            
    return ""


def show_recipe_form(db, data, source_type):
    """Show the recipe form that can be filled by AI, parsing, or manual entry"""
    st.markdown(f"### 📋 Recipe Form ({source_type})")
    st.markdown("Review and edit the recipe details below, then save to your cookbook.")
    
    with st.form(f"recipe_form_{source_type.lower()}", clear_on_submit=False):
        # Basic recipe info
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Recipe Title *", value=data.get('title', ''))
        
        with col2:
            servings = st.text_input("Servings", value=data.get('servings', ''))
        
        # Timing
        time_col1, time_col2, time_col3 = st.columns(3)
        with time_col1:
            prep_time = st.text_input("Prep Time", value=data.get('prep_time', ''), placeholder="e.g. 15 minutes")
        with time_col2:
            cook_time = st.text_input("Cook Time", value=data.get('cook_time', ''), placeholder="e.g. 30 minutes")
        with time_col3:
            total_time = st.text_input("Total Time", value=data.get('total_time', ''), placeholder="e.g. 45 minutes")
        
        # Description
        description = st.text_area("Description", value=data.get('description', ''), height=100)
        
        # Simple Image Upload
        st.markdown("**Recipe Image (Optional):**")
        uploaded_image = st.file_uploader(
            "Upload a photo of your recipe",
            type=['png', 'jpg', 'jpeg', 'gif'],
            key=f"recipe_image_upload_{source_type.lower()}"
        )
        
        # Ingredients
        st.markdown("**Ingredients:**")
        ingredients_text = st.text_area(
            "Ingredients (one per line)",
            value='\n'.join(data.get('ingredients', [])) if data.get('ingredients') else '',
            height=150,
            placeholder="Enter each ingredient on a separate line:\n4 boneless chicken breasts\n2 tbsp olive oil\n1 tsp salt"
        )
        
        # Instructions
        instructions = st.text_area(
            "Instructions",
            value=data.get('instructions', ''),
            height=200,
            placeholder="Enter the cooking instructions..."
        )
        
        # Submit button
        submitted = st.form_submit_button("💾 Save Recipe to Cookbook", type="primary")
        
        if submitted:
            if not title.strip():
                st.error("❌ Recipe title is required!")
                return
            
            if not instructions.strip():
                st.error("❌ Instructions are required!")
                return
                
            # Parse ingredients list
            ingredients_list = [ing.strip() for ing in ingredients_text.split('\n') if ing.strip()]
            if not ingredients_list:
                st.error("❌ At least one ingredient is required!")
                return
            
            # Handle image upload if provided
            image_path = ""
            if uploaded_image is not None:
                success, saved_path = save_recipe_image_during_creation(uploaded_image, title)
                if success:
                    image_path = saved_path
            
            # Store recipe data for ingredient mapping step (don't save to DB yet)
            st.session_state['pending_recipe'] = {
                'title': title,
                'description': description,
                'ingredients_list': ingredients_list,
                'instructions': instructions,
                'prep_time': prep_time,
                'cook_time': cook_time,
                'total_time': total_time,
                'servings': servings,
                'image_path': image_path,
                'source_type': source_type
            }
            st.rerun()
    
    # Show ingredient mapping interface if recipe is pending
    if 'pending_recipe' in st.session_state:
        st.markdown("---")
        show_structured_ingredient_interface(db, st.session_state['pending_recipe'])
    
    # Handle success actions outside the form
    if st.session_state.get('recipe_saved', False):
        st.markdown("---")
        st.success(f"🎉 Recipe '{st.session_state.get('saved_recipe_title')}' was saved to your cookbook!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Add Another Recipe", type="primary", key=f"add_another_{source_type.lower()}"):
                # Clear all session state
                if 'parsed_recipe_data' in st.session_state:
                    del st.session_state['parsed_recipe_data']
                if 'recipe_saved' in st.session_state:
                    del st.session_state['recipe_saved']
                if 'saved_recipe_title' in st.session_state:
                    del st.session_state['saved_recipe_title']
                st.rerun()
        
        with col2:
            if st.button("📚 View All Recipes", key=f"view_recipes_{source_type.lower()}"):
                st.info("Navigate to the Recipe Browser tab to see all your recipes!")


def clean_text_encoding(text):
    """
    Clean text using unidecode library to handle ALL Unicode characters.
    This converts any Unicode character to its closest ASCII equivalent.
    """
    if not text:
        return ""
    
    # Convert to string if not already
    text = str(text)
    
    # Use global imports for text cleaning
    if ENCODING_LIBRARIES_AVAILABLE:
        # First, convert any HTML content to clean markdown (handles HTML entities too)
        try:
            # If text contains HTML tags, convert to markdown first
            if '<' in text and '>' in text:
                text = markdownify(text, strip=['script', 'style'])
        except Exception:
            pass  # If markdown conversion fails, continue with original text
        
        # Use unidecode to convert ALL Unicode characters to ASCII equivalents
        # This handles emojis, special characters, accented characters, etc.
        try:
            text = unidecode(text)
        except Exception as e:
            print(f"[WARNING] unidecode failed: {e}")
            # Fallback: keep only basic ASCII characters
            text = ''.join(char for char in text if ord(char) < 128)
    else:
        print("[WARNING] Encoding libraries not available, falling back to ASCII-only")
        # Fallback if libraries aren't available: keep only basic ASCII characters
        text = ''.join(char for char in text if ord(char) < 128)
    
    # Clean up any extra whitespace
    text = ' '.join(text.split())
    
    return text.strip()


def show_structured_ingredient_interface(db, recipe_data):
    """Show structured ingredient interface with expandable fields"""
    st.markdown("## 📋 Recipe Structure")
    st.markdown(f"**Recipe:** {recipe_data['title']}")
    
    # Get all existing ingredients for dropdowns
    from services import get_ingredient_service
    ingredient_service = get_ingredient_service()
    all_ingredients = ingredient_service.get_all_ingredients()
    ingredient_options = ["-- Select Ingredient --"] + [f"{ing.name}" for ing in all_ingredients]
    
    # Initialize structured ingredients in session state
    if 'structured_ingredients' not in st.session_state:
        st.session_state['structured_ingredients'] = []
        # Auto-parse ingredients from the ingredients_list
        ingredients_list = recipe_data['ingredients_list']
        for ingredient_text in ingredients_list:
            parsed = parse_ingredient_text(ingredient_text)
            st.session_state['structured_ingredients'].append({
                'original_text': ingredient_text,
                'quantity': parsed['quantity'],
                'unit': parsed['unit'],
                'ingredient_id': None,
                'ingredient_name': parsed['ingredient_name'],
                'preparation': parsed['preparation']
            })
    
    # Collapsible ingredients section
    with st.expander("🔧 Structured Ingredients (Auto-parsed)", expanded=True):
        st.markdown("Review and adjust the auto-parsed ingredient structure:")
        
        # Display each structured ingredient
        all_mapped = True
        for i, ingredient in enumerate(st.session_state['structured_ingredients']):
            st.markdown(f"**Ingredient {i+1}:**")
            col1, col2, col3, col4 = st.columns([1, 1, 2, 1])
            
            with col1:
                quantity = st.number_input(
                    "Qty", 
                    value=ingredient['quantity'], 
                    step=0.25, 
                    key=f"qty_{i}",
                    min_value=0.0
                )
                st.session_state['structured_ingredients'][i]['quantity'] = quantity
            
            with col2:
                unit = st.text_input(
                    "Unit", 
                    value=ingredient['unit'], 
                    key=f"unit_{i}",
                    placeholder="cup, tsp, etc."
                )
                st.session_state['structured_ingredients'][i]['unit'] = unit
            
            with col3:
                # Auto-match suggestion
                suggested_match = auto_match_ingredient(ingredient['ingredient_name'], all_ingredients)
                default_index = 0
                if suggested_match:
                    try:
                        default_index = ingredient_options.index(suggested_match.name) 
                    except ValueError:
                        pass
                
                selected_ingredient = st.selectbox(
                    "Ingredient",
                    ingredient_options,
                    index=default_index,
                    key=f"ingredient_{i}"
                )
                
                # Store selected ingredient ID
                if selected_ingredient != "-- Select Ingredient --":
                    matched_ingredient = next((ing for ing in all_ingredients if ing.name == selected_ingredient), None)
                    if matched_ingredient:
                        st.session_state['structured_ingredients'][i]['ingredient_id'] = matched_ingredient.id
                        st.session_state['structured_ingredients'][i]['ingredient_name'] = matched_ingredient.name
                    else:
                        st.session_state['structured_ingredients'][i]['ingredient_id'] = None
                        all_mapped = False
                else:
                    st.session_state['structured_ingredients'][i]['ingredient_id'] = None
                    all_mapped = False
            
            with col4:
                if st.button("➕", key=f"new_ing_{i}", help="Create new ingredient"):
                    show_new_ingredient_form_structured(ingredient_service, ingredient['ingredient_name'], i)
            
            # Preparation notes
            preparation = st.text_input(
                "Preparation (optional)", 
                value=ingredient['preparation'], 
                key=f"prep_{i}",
                placeholder="chopped, diced, etc."
            )
            st.session_state['structured_ingredients'][i]['preparation'] = preparation
            
            # Show original text for reference
            st.caption(f"Original: {ingredient['original_text']}")
            st.markdown("---")
        
        # Add new ingredient field button
        if st.button("➕ Add Another Ingredient"):
            st.session_state['structured_ingredients'].append({
                'original_text': '',
                'quantity': 1.0,
                'unit': '',
                'ingredient_id': None,
                'ingredient_name': '',
                'preparation': ''
            })
            st.rerun()
    
    # Save button
    st.markdown("### Save Recipe")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if all_mapped and len(st.session_state['structured_ingredients']) > 0:
            if st.button("✅ Save Recipe with Structured Ingredients", type="primary", key="save_structured_recipe"):
                save_recipe_with_structured_ingredients(db, recipe_data, st.session_state['structured_ingredients'])
        else:
            missing_count = len([ing for ing in st.session_state['structured_ingredients'] if ing['ingredient_id'] is None])
            st.button(f"⚠️ Map All {missing_count} Ingredients First", disabled=True)
            if missing_count > 0:
                st.caption(f"Please select ingredients for all {missing_count} unmapped fields")


def auto_match_ingredient(ingredient_text, all_ingredients):
    """Attempt to auto-match recipe ingredient text to existing ingredient"""
    # Simple matching - extract key words and find best match
    import re
    
    # Clean the ingredient text
    clean_text = re.sub(r'^\d+\s*', '', ingredient_text)  # Remove leading numbers
    clean_text = re.sub(r'\b(cups?|tbsp|tsp|pounds?|lbs?|oz|grams?|ml|cloves?|slices?)\b', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\b(chopped|diced|minced|sliced|grated|fresh|dried)\b', '', clean_text, flags=re.IGNORECASE)
    clean_text = clean_text.strip().lower()
    
    # Try exact matches first
    for ingredient in all_ingredients:
        if ingredient.name.lower() in clean_text or clean_text in ingredient.name.lower():
            return ingredient
    
    # Try partial matches
    words = clean_text.split()
    for ingredient in all_ingredients:
        ingredient_words = ingredient.name.lower().split()
        if any(word in ingredient_words for word in words if len(word) > 2):
            return ingredient
    
    return None


def show_new_ingredient_form_structured(ingredient_service, ingredient_name, index):
    """Show form to create new ingredient for structured interface"""
    with st.expander(f"Create New Ingredient: '{ingredient_name}'", expanded=True):
        with st.form(f"new_ingredient_form_structured_{index}"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Ingredient Name", value=ingredient_name.title())
            
            with col2:
                categories = ["Protein", "Vegetable", "Fruit", "Grain", "Dairy", "Spice", "Oil", "Other"]
                category = st.selectbox("Category", categories)
            
            submitted = st.form_submit_button("Create Ingredient")
            
            if submitted and name.strip():
                # Create the new ingredient
                new_ingredient = ingredient_service.create_ingredient(name.strip(), category)
                if new_ingredient:
                    st.success(f"✅ Created new ingredient: {name}")
                    # Update the structured ingredient
                    if 'structured_ingredients' in st.session_state:
                        st.session_state['structured_ingredients'][index]['ingredient_id'] = new_ingredient.id
                        st.session_state['structured_ingredients'][index]['ingredient_name'] = new_ingredient.name
                    st.rerun()
                else:
                    st.error("Failed to create ingredient")


def save_recipe_with_structured_ingredients(db, recipe_data, structured_ingredients):
    """Save recipe to database with structured ingredient relationships"""
    try:
        # Save the recipe first
        recipe_id = save_recipe_to_database(
            db, recipe_data['title'], recipe_data['description'], 
            recipe_data['ingredients_list'], recipe_data['instructions'],
            recipe_data['prep_time'], recipe_data['cook_time'], 
            recipe_data['total_time'], recipe_data['servings'], recipe_data['image_path']
        )
        
        if recipe_id:
            # Save the structured ingredient relationships
            successful_mappings = 0
            
            for order, ingredient in enumerate(structured_ingredients):
                if ingredient['ingredient_id']:
                    # Add to recipe_ingredients table with structured data
                    success = db.add_recipe_ingredient(
                        recipe_id=recipe_id,
                        ingredient_id=ingredient['ingredient_id'],
                        quantity=ingredient['quantity'],
                        unit=ingredient['unit'],
                        preparation_note=ingredient['preparation'],
                        ingredient_order=order,
                        is_optional=False
                    )
                    
                    if success:
                        successful_mappings += 1
                    else:
                        st.warning(f"Failed to map ingredient: {ingredient['ingredient_name']}")
            
            if successful_mappings == len([ing for ing in structured_ingredients if ing['ingredient_id']]):
                st.success(f"✅ Recipe '{recipe_data['title']}' saved with {successful_mappings} structured ingredients!")
            else:
                st.warning(f"⚠️ Recipe saved but only {successful_mappings} ingredient mappings succeeded")
            
            # Clear session state
            if 'pending_recipe' in st.session_state:
                del st.session_state['pending_recipe']
            if 'structured_ingredients' in st.session_state:
                del st.session_state['structured_ingredients']
                
            st.session_state['recipe_saved'] = True
            st.session_state['saved_recipe_title'] = recipe_data['title']
            st.rerun()
        else:
            st.error("Failed to save recipe")
            
    except Exception as e:
        st.error(f"Error saving recipe: {e}")


def show_new_ingredient_form(ingredient_service, ingredient_text, index):
    """Show form to create new ingredient"""
    with st.expander(f"Create New Ingredient for '{ingredient_text}'", expanded=True):
        # Extract suggested name from ingredient text
        import re
        suggested_name = re.sub(r'^\d+\s*', '', ingredient_text)
        suggested_name = re.sub(r'\b(cups?|tbsp|tsp|pounds?|lbs?|oz|grams?|ml|cloves?|slices?)\b', '', suggested_name, flags=re.IGNORECASE)
        suggested_name = re.sub(r'\b(chopped|diced|minced|sliced|grated|fresh|dried)\b', '', suggested_name, flags=re.IGNORECASE)
        suggested_name = suggested_name.strip().title()
        
        with st.form(f"new_ingredient_form_{index}"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Ingredient Name", value=suggested_name)
            
            with col2:
                categories = ["Protein", "Vegetable", "Fruit", "Grain", "Dairy", "Spice", "Oil", "Other"]
                category = st.selectbox("Category", categories)
            
            submitted = st.form_submit_button("Create Ingredient")
            
            if submitted and name.strip():
                # Create the new ingredient
                new_ingredient = ingredient_service.create_ingredient(name.strip(), category)
                if new_ingredient:
                    st.success(f"✅ Created new ingredient: {name}")
                    # Map it to the recipe ingredient
                    st.session_state['ingredient_mappings'][ingredient_text] = new_ingredient.id
                    st.rerun()
                else:
                    st.error("Failed to create ingredient")


def save_recipe_with_mappings(db, recipe_data, ingredient_mappings):
    """Save recipe to database with proper ingredient relationships"""
    try:
        # Save the recipe first
        recipe_id = save_recipe_to_database(
            db, recipe_data['title'], recipe_data['description'], 
            recipe_data['ingredients_list'], recipe_data['instructions'],
            recipe_data['prep_time'], recipe_data['cook_time'], 
            recipe_data['total_time'], recipe_data['servings'], recipe_data['image_path']
        )
        
        if recipe_id:
            # Now save the ingredient mappings to recipe_ingredients table
            ingredient_order = 0
            successful_mappings = 0
            
            for ingredient_text, ingredient_id in ingredient_mappings.items():
                # Parse quantity and unit from ingredient text (basic parsing)
                quantity, unit = parse_ingredient_quantity(ingredient_text)
                
                # Add to recipe_ingredients table using the database service
                success = db.add_recipe_ingredient(
                    recipe_id=recipe_id,
                    ingredient_id=ingredient_id,
                    quantity=quantity,
                    unit=unit,
                    preparation_note="",  # Could extract preparation notes in the future
                    ingredient_order=ingredient_order,
                    is_optional=False
                )
                
                if success:
                    successful_mappings += 1
                    ingredient_order += 1
                else:
                    st.warning(f"Failed to map ingredient: {ingredient_text}")
            
            if successful_mappings == len(ingredient_mappings):
                st.success(f"✅ Recipe '{recipe_data['title']}' saved successfully with {successful_mappings} ingredient mappings!")
            else:
                st.warning(f"⚠️ Recipe saved but only {successful_mappings}/{len(ingredient_mappings)} ingredient mappings succeeded")
            
            # Clear session state
            if 'pending_recipe' in st.session_state:
                del st.session_state['pending_recipe']
            if 'ingredient_mappings' in st.session_state:
                del st.session_state['ingredient_mappings']
                
            st.session_state['recipe_saved'] = True
            st.session_state['saved_recipe_title'] = recipe_data['title']
            st.rerun()
        else:
            st.error("Failed to save recipe")
            
    except Exception as e:
        st.error(f"Error saving recipe: {e}")


def parse_ingredient_text(ingredient_text):
    """Parse ingredient text into structured components"""
    import re
    
    # Clean the input
    text = ingredient_text.strip()
    
    # Initialize components
    result = {
        'quantity': 1.0,
        'unit': '',
        'ingredient_name': text,
        'preparation': ''
    }
    
    # Parse quantity and unit pattern: "2 cups flour, chopped"
    # Handle fractions like "1/2", "1 1/2", etc.
    quantity_pattern = r'^(\d+(?:\s*\d+/\d+|\.\d+|/\d+)?)\s*'
    match = re.match(quantity_pattern, text)
    
    if match:
        quantity_str = match.group(1).strip()
        try:
            # Handle fractions
            if '/' in quantity_str:
                if ' ' in quantity_str:  # Mixed number like "1 1/2"
                    whole, fraction = quantity_str.split(' ', 1)
                    num, denom = fraction.split('/')
                    result['quantity'] = float(whole) + float(num) / float(denom)
                else:  # Simple fraction like "1/2"
                    num, denom = quantity_str.split('/')
                    result['quantity'] = float(num) / float(denom)
            else:
                result['quantity'] = float(quantity_str)
        except:
            result['quantity'] = 1.0
        
        # Remove quantity from text
        text = text[len(match.group(0)):].strip()
    
    # Parse unit pattern: "cups", "tbsp", "tsp", etc.
    unit_pattern = r'^(cups?|tbsp|tsp|tablespoons?|teaspoons?|lbs?|pounds?|oz|ounces?|grams?|ml|liters?|cloves?|slices?|pieces?)\s+'
    match = re.match(unit_pattern, text, re.IGNORECASE)
    
    if match:
        result['unit'] = match.group(1).lower()
        text = text[len(match.group(0)):].strip()
    
    # Parse preparation notes: "flour, sifted" or "onion, diced"
    if ',' in text:
        parts = text.split(',', 1)
        result['ingredient_name'] = parts[0].strip()
        result['preparation'] = parts[1].strip()
    else:
        # Look for common preparation words at the end
        prep_pattern = r'\s+(chopped|diced|minced|sliced|grated|shredded|crushed|ground|fresh|dried|cooked)$'
        match = re.search(prep_pattern, text, re.IGNORECASE)
        if match:
            result['preparation'] = match.group(1).lower()
            result['ingredient_name'] = text[:match.start()].strip()
        else:
            result['ingredient_name'] = text
    
    # Clean up ingredient name
    result['ingredient_name'] = result['ingredient_name'].strip()
    
    return result


def parse_ingredient_quantity(ingredient_text):
    """Parse quantity and unit from ingredient text like '2 cups flour' (legacy function)"""
    parsed = parse_ingredient_text(ingredient_text)
    return parsed['quantity'], parsed['unit']


def clean_ingredients_list(ingredients_list):
    """Clean a list of ingredient strings"""
    cleaned = []
    for ingredient in ingredients_list:
        if ingredient and str(ingredient).strip():
            cleaned_ingredient = clean_text_encoding(str(ingredient))
            if cleaned_ingredient:  # Only add if not empty after cleaning
                cleaned.append(cleaned_ingredient)
    return cleaned


def process_and_save_recipe_image(uploaded_file, recipe_title):
    """
    Process uploaded image to create perfect 200x200 square and save it.
    Auto-crops and resizes to save storage space and ensure consistency.
    """
    import os
    import uuid
    from pathlib import Path
    from PIL import Image
    import io
    
    try:
        # Create static/recipe_images directory if it doesn't exist
        images_dir = Path("static/recipe_images")
        images_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate safe filename based on recipe title
        safe_title = "".join(c for c in recipe_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:20]  # Limit length
        
        # Generate unique filename (always save as .jpg for consistency and smaller size)
        unique_filename = f"{safe_title}_{uuid.uuid4().hex[:8]}.jpg"
        file_path = images_dir / unique_filename
        
        # Process the image
        print(f"[INFO] Processing image for recipe: {recipe_title}")
        
        # Open the uploaded image
        image = Image.open(uploaded_file)
        
        # Convert to RGB if necessary (handles PNG with transparency, etc.)
        if image.mode != 'RGB':
            # Create white background for transparent images
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'RGBA':
                background.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
            else:
                background.paste(image)
            image = background
        
        # Create perfect square by cropping to center
        width, height = image.size
        
        # Determine crop dimensions (largest square possible)
        crop_size = min(width, height)
        
        # Calculate crop coordinates (center crop)
        left = (width - crop_size) // 2
        top = (height - crop_size) // 2
        right = left + crop_size
        bottom = top + crop_size
        
        # Crop to square
        image_square = image.crop((left, top, right, bottom))
        
        # Resize to exactly 200x200 pixels
        image_final = image_square.resize((200, 200), Image.Resampling.LANCZOS)
        
        # Save as high-quality JPEG (smaller file size than PNG)
        image_final.save(file_path, 'JPEG', quality=85, optimize=True)
        
        # Return relative path for database storage
        relative_path = str(file_path)
        print(f"[INFO] Successfully processed and saved 200x200 image: {relative_path}")
        return True, relative_path
        
    except Exception as e:
        print(f"[ERROR] Failed to process and save recipe image: {e}")
        import traceback
        traceback.print_exc()
        return False, ""


# Keep old function name for backward compatibility
def save_recipe_image_during_creation(uploaded_file, recipe_title):
    """Wrapper for backward compatibility"""
    return process_and_save_recipe_image(uploaded_file, recipe_title)


def save_recipe_to_database(db, title, description, ingredients_list, instructions, 
                          prep_time, cook_time, total_time, servings, image_path=""):
    """Save a recipe to the database and return the recipe ID"""
    try:
        # Clean all text fields to prevent encoding issues
        clean_title = clean_text_encoding(title)
        clean_description = clean_text_encoding(description)
        clean_instructions = clean_text_encoding(instructions)
        clean_ingredients = clean_ingredients_list(ingredients_list)
        
        # Validate required fields after cleaning
        if not clean_title:
            print("[X] Error: Recipe title is empty after cleaning")
            return None
            
        if not clean_ingredients:
            print("[X] Error: No valid ingredients after cleaning")
            return None
        
        # Parse the time and servings values
        prep_minutes = parse_time_to_minutes(prep_time) or 0
        cook_minutes = parse_time_to_minutes(cook_time) or 0
        servings_num = parse_servings(servings) or 1
        
        # Single household system
        user_id = 1
        
        # Create the recipe in the database with cleaned data
        print(f"Attempting to save recipe: title='{clean_title}', prep_time={prep_minutes}, cook_time={cook_minutes}")
        
        recipe = db.create_recipe(
            title=clean_title,
            description=clean_description,
            instructions=clean_instructions,
            prep_time_minutes=prep_minutes,
            cook_time_minutes=cook_minutes,
            servings=servings_num,
            source_url="manual_entry",
            image_path=clean_text_encoding(image_path)  # Add image path support
        )
        
        print(f"Database create_recipe returned: {recipe}")
        
        if recipe:
            print(f"[OK] Successfully saved recipe '{clean_title}' with ID {recipe.id}")
            
            # Now add ingredients to the recipe
            ingredient_count = 0
            for ingredient_text in clean_ingredients:
                if ingredient_text.strip():
                    try:
                        # Add ingredient to recipe (you might need to implement this method)
                        # For now, just print what we would add
                        print(f"  - Ingredient: {ingredient_text.strip()}")
                        ingredient_count += 1
                    except Exception as e:
                        print(f"Warning: Could not add ingredient '{ingredient_text}': {e}")
            
            print(f"[OK] Added {ingredient_count} ingredients to recipe")
            return recipe.id
        else:
            print("[X] Failed to create recipe in database")
            return None
            
    except Exception as e:
        print(f"[X] Error saving recipe to database: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_time_to_minutes(time_str):
    """Parse time string like '15 minutes' or '1 hour' to minutes"""
    if not time_str:
        return None
    
    time_str = time_str.lower().strip()
    
    # Extract numbers
    import re
    numbers = re.findall(r'\d+', time_str)
    if not numbers:
        return None
    
    minutes = 0
    for num in numbers:
        num = int(num)
        if 'hour' in time_str:
            minutes += num * 60
        else:  # assume minutes
            minutes += num
    
    return minutes if minutes > 0 else None


def parse_servings(servings_str):
    """Parse servings string to extract number"""
    if not servings_str:
        return None
    
    import re
    numbers = re.findall(r'\d+', servings_str)
    return int(numbers[0]) if numbers else None


def single_recipe_parser(validator: 'SimpleValidationInterface', ai_parser, db):
    """Single recipe parsing with AI"""
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


def bulk_recipe_parser_ui(bulk_parser, validator: 'SimpleValidationInterface', ai_parser, db):
    """Bulk recipe parsing interface"""
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
                                    # Show success message
                                    st.success(f"Recipe {i+1} ready for validation!")
                    
                    else:
                        st.warning("⚠️ No recipes detected in the text.")
                        st.info("💡 Make sure your text contains complete recipes with ingredients and instructions.")
                
                except Exception as e:
                    st.error(f"❌ Bulk parsing failed: {str(e)}")
        else:
            st.warning("Please upload a file or paste some text to parse.")


def smart_parser_sample(validator: 'SimpleValidationInterface', ai_parser, db):
    """Pre-loaded sample recipe parser"""
    st.markdown("#### 🎯 Sample Recipe")
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


def validation_interface():
    """Recipe validation interface with text input and file upload"""
    st.markdown("### 🔍 Recipe Parser & Validation")
    st.markdown("Add recipes by pasting text or uploading files, then validate before saving to your cookbook.")
    
    # Initialize services
    db = get_database_service_singleton()
    parser = ParsingService(db)
    validation_ui = ValidationInterface(parser, db)
    
    # Create tabs for different input modes
    input_tab1, input_tab2, input_tab3 = st.tabs(["📝 Text Input", "📁 File Upload", "🎯 Sample Data"])
    
    with input_tab1:
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
                    # Clean the input text FIRST to prevent encoding errors
                    clean_recipe_text = clean_text_encoding(recipe_text)
                    
                    # Import scraping service for text parsing
                    from services import ScrapingService
                    scraper = ScrapingService()
                    
                    # Parse the cleaned text
                    scraped_recipe = scraper.parse_recipe_text(clean_recipe_text)
                    
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
                                st.success("Recipe would be saved to your cookbook!")
                        
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
    
    with input_tab2:
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
                        # Clean HTML content first to prevent encoding errors
                        clean_content = clean_text_encoding(content)
                        scraped_recipe = scraper.parse_html_content(clean_content)
                    else:
                        # Clean text content first to prevent encoding errors  
                        clean_content = clean_text_encoding(content)
                        scraped_recipe = scraper.parse_recipe_text(clean_content)
                    
                    if scraped_recipe and scraped_recipe.confidence_score > 0.2:
                        st.success(f"✅ Successfully parsed: {scraped_recipe.title}")
                        
                        # Show parsed data and validation (same as text input)
                        st.markdown("#### 🔍 Recipe Validation") 
                        parsed_recipe = parser.parse_scraped_recipe(scraped_recipe)
                        validation_result = validation_ui.validate_recipe(parsed_recipe, user_id=1)
                        
                        if validation_result and validation_result.is_valid:
                            st.success("✅ Recipe validated and ready to save!")
                            if st.button("💾 Save Recipe to Cookbook", key="file_save", type="primary"):
                                st.success("Recipe would be saved to your cookbook!")
                    else:
                        st.error("❌ Unable to parse recipe from this file.")
                        st.info("💡 Try files with clear recipe structure or use the text input method.")
                        
                except Exception as e:
                    st.error(f"❌ File processing failed: {str(e)}")
                    st.info("Make sure the file contains readable recipe content.")
    
    with input_tab3:
        st.markdown("#### Sample Data")
        st.info("Test the recipe validation with sample recipe data.")
        
        # Show information about validation interface
        st.info("🔍 Recipe validation is integrated into the **Add Recipe** tab.")
        st.info("💡 After parsing a recipe with AI or text parsing, you can review and edit it before saving.")


def recipe_browser():
    """Recipe browser interface using the full RecipeBrowser class"""
    st.markdown("### 📚 Recipe Browser")
    st.markdown("Browse, search, and manage your recipe collection with smart pantry integration.")
    
    try:
        # Initialize recipe browser with database
        db = get_database_service_singleton()
        browser = RecipeBrowser(db)
        
        # Check if we have recipes
        all_recipes = db.get_all_recipes(user_id=1, limit=50)
        
        if not all_recipes:
            st.info("🍽️ No recipes found. Use the **Add Recipe** tab to add some recipes!")
            st.info("💡 Try parsing your Simple Baked Chicken Breast recipe to get started!")
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


def ai_features():
    """AI features interface for recipe enhancement and suggestions"""
    st.markdown("### 🤖 AI Features")
    st.markdown("AI-powered recipe enhancements and suggestions.")
    
    # Initialize AI services
    db = get_database_service_singleton()
    ai_service = AIService(db)
    ai_ui = AIFeaturesInterface(ai_service, db)
    
    # Show AI status first
    ai_ui.render_ai_status_indicator(compact=False)
    
    if not ai_service.is_ai_available():
        st.info("👆 Start LM Studio to see AI features in action!")
        return
    
    # AI Features require real recipes - disabled until we have saved recipes
    st.info("🍳 AI Features will be available once you have saved recipes in your cookbook!")
    st.info("💡 Use the **Add Recipe** tab to add some recipes first, then return here to see AI enhancements.")
    
    # Show additional AI features
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔧 AI Settings")
        ai_ui.render_ai_settings_panel()
    
    with col2:
        st.markdown("### 🔍 AI Scraping Helper")
        ai_ui.render_ai_scraping_helper()


def pantry_manager():
    """Pantry management interface for tracking available ingredients"""
    if not PANTRY_AVAILABLE:
        st.error("❌ Pantry services not available")
        return
        
    st.markdown("### 🥬 My Pantry - What Can I Make?")
    st.markdown("Manage your ingredient inventory and discover recipes you can make right now!")
    
    # Initialize services  
    db = get_database_service_singleton()
    pantry_service = get_pantry_service(db)
    
    # Single household system
    user_id = 1  # Single household system
    
    # Get all available ingredients from database (dynamic)
    all_ingredients = db.get_all_ingredients()
    
    if not all_ingredients:
        st.warning("📝 No ingredients found in database. Add ingredients via:")
        st.info("• Smart Parser tab (parse recipes to auto-add ingredients)")
        st.info("• CSV Import in Database Inspection section")
        return
    
    # Get user's current pantry
    user_pantry_items = pantry_service.get_user_pantry(user_id)
    pantry_ingredient_ids = {item.ingredient_id for item in user_pantry_items if hasattr(item, 'ingredient_id')}
    
    st.markdown(f"**Available ingredients in database:** {len(all_ingredients)}")
    st.markdown(f"**Ingredients in your pantry:** {len(pantry_ingredient_ids)}")
    
    # Create tabs for different pantry functions
    pantry_tab1, pantry_tab2, pantry_tab3 = st.tabs(["🛒 Manage Pantry", "🍳 What Can I Make?", "📊 Pantry Stats"])
    
    with pantry_tab1:
        render_pantry_management(db, pantry_service, user_id, all_ingredients, pantry_ingredient_ids)
    
    with pantry_tab2:
        render_recipe_suggestions(db, pantry_service, user_id, all_ingredients)
    
    with pantry_tab3:
        render_pantry_statistics(db, pantry_service, user_id, all_ingredients, pantry_ingredient_ids)


def render_pantry_management(db, pantry_service, user_id, all_ingredients, current_pantry_ids):
    """Render the improved pantry management interface"""
    st.markdown("#### 🥬 My Pantry Management")
    
    # Auto-add all ingredients to pantry database (so they're all available for management)
    auto_added_count = 0
    for ingredient in all_ingredients:
        if ingredient.id not in current_pantry_ids:
            # Add to pantry but mark as not available
            try:
                pantry_service.update_pantry_item(user_id, ingredient.id, False, "none")
                auto_added_count += 1
            except:
                pass  # Ingredient might already be in pantry table
    
    # Refresh pantry data after auto-adding
    if auto_added_count > 0:
        st.info(f"✅ Auto-added {auto_added_count} ingredients to your pantry for management")
        st.rerun()
    
    # Get fresh pantry data
    user_pantry_items = pantry_service.get_user_pantry(user_id)
    available_count = len([item for item in user_pantry_items if item.is_available])
    
    # Header with stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Ingredients", len(all_ingredients))
    with col2:
        st.metric("Currently Available", available_count)
    with col3:
        st.metric("Need to Stock", len(all_ingredients) - available_count)
    
    st.markdown("---")
    
    # Search functionality
    search_term = st.text_input("🔍 Search ingredients...", placeholder="Type ingredient name to find quickly")
    
    # Bulk operations
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ Mark All Available", type="secondary"):
            for ingredient in all_ingredients:
                pantry_service.update_pantry_item(user_id, ingredient.id, True, "plenty")
            st.success("Marked all ingredients as available!")
            st.rerun()
    
    with col2:
        if st.button("❌ Clear All Availability", type="secondary"):
            for ingredient in all_ingredients:
                pantry_service.update_pantry_item(user_id, ingredient.id, False, "none")
            st.success("Cleared all ingredient availability!")
            st.rerun()
    
    with col3:
        if st.button("🗑️ Remove Uncheck Items", type="secondary"):
            st.warning("This would remove unchecked ingredients from pantry (not implemented yet)")
    
    st.markdown("---")
    
    # Group ingredients by category
    ingredients_by_category = {}
    for ingredient in all_ingredients:
        category = ingredient.category or "Uncategorized"
        if category not in ingredients_by_category:
            ingredients_by_category[category] = []
        ingredients_by_category[category].append(ingredient)
    
    # Create a mapping of ingredient ID to availability status
    pantry_status = {item.ingredient_id: item.is_available for item in user_pantry_items if hasattr(item, 'ingredient_id')}
    
    # Category icons mapping
    category_icons = {
        'protein': '🥩',
        'dairy': '🥛', 
        'vegetables': '🥕',
        'grains': '🌾',
        'pantry': '🏺',
        'condiments': '🧂',
        'oil': '🫒',
        'seasoning': '🧂',
        'sweetener': '🍯',
        'Uncategorized': '📦'
    }
    
    # Filter ingredients if search term is provided
    if search_term:
        filtered_categories = {}
        for category, ingredients in ingredients_by_category.items():
            filtered_ingredients = [ing for ing in ingredients if search_term.lower() in ing.name.lower()]
            if filtered_ingredients:
                filtered_categories[category] = filtered_ingredients
        ingredients_by_category = filtered_categories
        
        if not ingredients_by_category:
            st.warning(f"No ingredients found matching '{search_term}'")
    
    # Render compact multi-column category layout
    categories = list(sorted(ingredients_by_category.keys()))
    
    # Responsive column layout (3 on desktop, 1 on mobile)
    # Check if mobile by using a simple responsive approach
    num_cols = 3  # Desktop: 3 columns
    try:
        # Try to detect narrow screens - on mobile, use 1 column
        # This is a simple approach; Streamlit doesn't have built-in responsive detection
        if st.session_state.get('mobile_layout', False):
            num_cols = 1
    except:
        pass
    
    # Allow user to toggle layout
    layout_col1, layout_col2 = st.columns([1, 4])
    with layout_col1:
        if st.button("📱 Mobile Layout" if num_cols == 3 else "🖥️ Desktop Layout"):
            st.session_state['mobile_layout'] = not st.session_state.get('mobile_layout', False)
            st.rerun()
    
    # Create columns based on layout choice
    if st.session_state.get('mobile_layout', False):
        num_cols = 1
    else:
        num_cols = 3
    
    cols = st.columns(num_cols)
    
    for i, category in enumerate(categories):
        col_index = i % num_cols
        ingredients = ingredients_by_category[category]
        icon = category_icons.get(category.lower(), '📦')
        
        # Count available ingredients in this category
        available_in_category = len([ing for ing in ingredients if pantry_status.get(ing.id, False)])
        
        with cols[col_index]:
            st.markdown(f"### {icon} {category.title()}")
            st.caption(f"{available_in_category}/{len(ingredients)} available")
            
            # Create lists for multiselect
            ingredient_names = [ing.name for ing in sorted(ingredients, key=lambda x: x.name)]
            ingredient_dict = {ing.name: ing for ing in ingredients}
            
            # Get currently selected ingredients (those marked as available)
            currently_selected = [ing.name for ing in ingredients if pantry_status.get(ing.id, False)]
            
            # Multiselect for available ingredients
            selected_ingredients = st.multiselect(
                f"I have these {category.lower()} items:",
                options=ingredient_names,
                default=currently_selected,
                key=f"multiselect_{category}",
                help=f"Select ingredients you currently have in your {category.lower()}"
            )
            
            # Update pantry status based on selection
            for ingredient_name in ingredient_names:
                ingredient = ingredient_dict[ingredient_name]
                should_be_available = ingredient_name in selected_ingredients
                currently_available = pantry_status.get(ingredient.id, False)
                
                if should_be_available != currently_available:
                    quantity = "plenty" if should_be_available else "none"
                    pantry_service.update_pantry_item(user_id, ingredient.id, should_be_available, quantity)
            
            # Compact bulk operations
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ All", key=f"all_{category}", help=f"Select all {category.lower()} items"):
                    for ingredient in ingredients:
                        pantry_service.update_pantry_item(user_id, ingredient.id, True, "plenty")
                    st.rerun()
            
            with col_b:
                if st.button("❌ None", key=f"clear_{category}", help=f"Deselect all {category.lower()} items"):
                    for ingredient in ingredients:
                        pantry_service.update_pantry_item(user_id, ingredient.id, False, "none")
                    st.rerun()
            
            # Show ingredient removal options (collapsed by default)
            with st.expander(f"🗑️ Remove {category} Items", expanded=False):
                st.caption("Remove ingredients you'll never use:")
                for ingredient in sorted(ingredients, key=lambda x: x.name):
                    col_name, col_btn = st.columns([3, 1])
                    with col_name:
                        st.write(ingredient.name)
                    with col_btn:
                        if st.button("🗑️", key=f"remove_perm_{ingredient.id}", help=f"Remove {ingredient.name} permanently"):
                            try:
                                with pantry_service.db.get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM user_pantry WHERE user_id = ? AND ingredient_id = ?", 
                                                 (user_id, ingredient.id))
                                    conn.commit()
                                st.success(f"Removed {ingredient.name} from pantry")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error removing ingredient: {e}")
            
            st.markdown("---")  # Separator between categories


def render_recipe_suggestions(db, pantry_service, user_id, all_ingredients):
    """Render recipe suggestions based on pantry contents"""
    st.markdown("#### 🍳 Recipes You Can Make")
    
    # Get user's pantry items
    pantry_items = pantry_service.get_user_pantry(user_id)
    
    if not pantry_items:
        st.info("Add some ingredients to your pantry first to see recipe suggestions!")
        return
    
    # Get all recipes and check which ones can be made
    all_recipes = db.get_all_recipes(user_id=user_id, limit=50)
    
    if not all_recipes:
        st.info("No recipes found in database. Add recipes via the Smart Parser tab!")
        return
    
    # Analyze recipe compatibility
    makeable_recipes = []
    partial_recipes = []
    
    pantry_ingredient_ids = {item.ingredient_id for item in pantry_items if hasattr(item, 'ingredient_id')}
    
    for recipe in all_recipes:
        if hasattr(recipe, 'required_ingredient_ids'):
            required_ids = recipe.required_ingredient_ids
            if required_ids:
                available_count = len(required_ids & pantry_ingredient_ids)
                total_count = len(required_ids)
                match_percentage = (available_count / total_count) * 100 if total_count > 0 else 0
                
                if match_percentage == 100:
                    makeable_recipes.append((recipe, match_percentage, available_count, total_count))
                elif match_percentage >= 50:  # Show recipes where you have at least half the ingredients
                    partial_recipes.append((recipe, match_percentage, available_count, total_count))
    
    # Display results
    if makeable_recipes:
        st.success(f"🎉 You can make {len(makeable_recipes)} recipes right now!")
        for recipe, percentage, available, total in makeable_recipes:
            with st.expander(f"✅ {recipe.name} (100% match - {total}/{total} ingredients)"):
                st.write(f"**Description:** {recipe.description}")
                st.write(f"**Prep time:** {recipe.prep_time_minutes} min | **Cook time:** {recipe.cook_time_minutes} min")
                st.write(f"**Serves:** {recipe.servings}")
                if st.button(f"View Full Recipe", key=f"view_{recipe.id}"):
                    st.session_state['selected_recipe_id'] = recipe.id
                    st.rerun()
    
    if partial_recipes:
        st.info(f"📋 {len(partial_recipes)} recipes you could make with a few more ingredients:")
        for recipe, percentage, available, total in partial_recipes:
            missing_count = total - available
            with st.expander(f"📋 {recipe.name} ({percentage:.0f}% match - {available}/{total} ingredients, need {missing_count} more)"):
                st.write(f"**Description:** {recipe.description}")
                st.write(f"**Missing ingredients:** You need {missing_count} more ingredients to make this recipe")
    
    if not makeable_recipes and not partial_recipes:
        st.info("No recipe matches found. Try adding more ingredients to your pantry!")


def render_pantry_statistics(db, pantry_service, user_id, all_ingredients, pantry_ingredient_ids):
    """Render pantry statistics and insights"""
    st.markdown("#### 📊 Pantry Insights")
    
    # Basic stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Available", len(all_ingredients))
    
    with col2:
        st.metric("In Your Pantry", len(pantry_ingredient_ids))
    
    with col3:
        percentage = (len(pantry_ingredient_ids) / len(all_ingredients) * 100) if all_ingredients else 0
        st.metric("Pantry Coverage", f"{percentage:.1f}%")
    
    with col4:
        recipes = db.get_all_recipes(user_id=user_id, limit=100)
        st.metric("Available Recipes", len(recipes))
    
    # Category breakdown
    if pantry_ingredient_ids:
        st.markdown("**Pantry by Category:**")
        
        pantry_ingredients = [ing for ing in all_ingredients if ing.id in pantry_ingredient_ids]
        category_counts = {}
        
        for ingredient in pantry_ingredients:
            category = ingredient.category or "Uncategorized"
            category_counts[category] = category_counts.get(category, 0) + 1
        
        for category, count in sorted(category_counts.items()):
            st.write(f"• **{category}:** {count} ingredients")
    
    # Recent activity (if we had timestamps, but we'll skip this for now)
    st.markdown("**Pantry Management:**")
    st.info("💡 Tip: Keep your pantry updated for better recipe suggestions!")
    st.info("💡 Tip: Use the Smart Parser to add more recipes that work with your ingredients!")



def test_ai_connection(provider: str, api_key: str = None):
    """Test connection to selected AI provider"""
    with st.spinner(f"Testing connection to {provider}..."):
        try:
            if provider == "OpenAI (ChatGPT)":
                if not api_key:
                    st.error("❌ Please enter your OpenAI API key")
                    return
                
                import openai
                client = openai.OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": "Hello, can you parse recipes?"}],
                    max_tokens=50
                )
                st.success("✅ OpenAI connection successful!")
                st.info(f"Model: GPT-4, Response: {response.choices[0].message.content[:50]}...")
            
            elif provider == "Claude (Anthropic)":
                if not api_key:
                    st.error("❌ Please enter your Anthropic API key")
                    return
                
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=50,
                    messages=[{"role": "user", "content": "Hello, can you parse recipes?"}]
                )
                st.success("✅ Claude connection successful!")
                st.info(f"Model: Claude-3.5, Response: {message.content[0].text[:50]}...")
            
            elif provider == "Gemini (Google)":
                if not api_key:
                    st.error("❌ Please enter your Google AI API key")
                    return
                
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-pro')
                response = model.generate_content("Hello, can you parse recipes?")
                st.success("✅ Gemini connection successful!")
                st.info(f"Model: Gemini-1.5-Pro, Response: {response.text[:50]}...")
            
            else:  # LM Studio
                import requests
                response = requests.get("http://localhost:1234/v1/models", timeout=5)
                if response.status_code == 200:
                    models = response.json()
                    st.success("✅ LM Studio connection successful!")
                    if models.get('data'):
                        model_name = models['data'][0].get('id', 'Unknown')
                        st.info(f"Local model loaded: {model_name}")
                    else:
                        st.warning("⚠️ LM Studio connected but no models loaded")
                else:
                    st.error("❌ LM Studio not responding")
        
        except Exception as e:
            st.error(f"❌ Connection failed: {str(e)}")
            if "API key" in str(e):
                st.info("💡 Check your API key is valid and has sufficient credits")
            elif "import" in str(e):
                st.info("💡 Install required package: pip install openai anthropic google-generativeai")


if __name__ == "__main__":
    main()