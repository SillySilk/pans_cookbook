#!/usr/bin/env python3
"""
Demo application for Pans Cookbook Recipe Browser.

Demonstrates the persistent pantry management and recipe browsing functionality.
Shows multi-page navigation with checkbox-based ingredient selection.
"""

import streamlit as st
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from ui.recipe_browser import create_recipe_browser
from services import get_database_service, get_ingredient_service
from models import Recipe

# Page configuration
st.set_page_config(
    page_title="Pans Cookbook",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize services
@st.cache_resource
def get_services():
    """Initialize and cache database services"""
    db_service = get_database_service()
    ingredient_service = get_ingredient_service()
    return db_service, ingredient_service

db_service, ingredient_service = get_services()

# Initialize recipe browser
@st.cache_resource
def get_recipe_browser():
    """Initialize and cache recipe browser"""
    return create_recipe_browser(db_service, ingredient_service)

browser = get_recipe_browser()

# Sidebar navigation
st.sidebar.title("🍳 Pans Cookbook")
st.sidebar.markdown("*Your Personal Recipe Manager*")

# Page selection
page = st.sidebar.selectbox(
    "Navigate to:",
    ["🏠 Home", "🥫 My Pantry", "📚 Recipe Browser", "📖 Recipe Details"]
)

# Database stats in sidebar
try:
    ingredients = ingredient_service.get_all_ingredients()
    recipes = browser._get_all_recipes()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Database Stats")
    st.sidebar.write(f"📦 {len(ingredients)} ingredients")
    st.sidebar.write(f"📚 {len(recipes)} recipes")
    
    # Pantry summary
    pantry_count = len(st.session_state.get(browser.PANTRY_KEY, set()))
    st.sidebar.write(f"🥫 {pantry_count} pantry items")
    
except Exception as e:
    st.sidebar.error(f"Error loading stats: {e}")

# Debug mode toggle
if st.sidebar.checkbox("🔧 Debug Mode"):
    st.sidebar.markdown("### Debug Info")
    st.sidebar.write("Session State Keys:")
    for key in st.session_state.keys():
        st.sidebar.write(f"• {key}")

# Clear cache button
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()

# Main content area
if page == "🏠 Home":
    st.title("🍳 Welcome to Pans Cookbook")
    st.markdown("*Your personal recipe management system*")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ## Getting Started
        
        1. **📦 Set up your pantry** - Go to "My Pantry" to check off ingredients you have
        2. **🔍 Browse recipes** - Use "Recipe Browser" to find recipes you can make
        3. **👁️ View details** - Click on recipes to see full instructions and ingredients
        
        ### Features
        - ✅ **Persistent pantry management** - Your ingredient selections are remembered
        - 🎯 **Smart filtering** - See which recipes you can make with available ingredients
        - 🔍 **Advanced search** - Filter by cuisine, meal type, difficulty, and cooking time
        - 📱 **Responsive design** - Works on desktop and mobile devices
        """)
        
        # Quick start section
        pantry_items = len(st.session_state.get(browser.PANTRY_KEY, set()))
        
        if pantry_items == 0:
            st.warning("⚠️ Your pantry is empty! Start by adding ingredients you have on hand.")
            if st.button("🚀 Set Up My Pantry"):
                st.switch_page("app_demo.py")  # This would work in a real Streamlit app
                st.session_state['page'] = "🥫 My Pantry"
                st.rerun()
        else:
            st.success(f"✅ You have {pantry_items} ingredients in your pantry!")
            if st.button("🍽️ Find Recipes I Can Make"):
                st.session_state['page'] = "📚 Recipe Browser"
                st.rerun()
    
    with col2:
        st.markdown("### 📈 Quick Stats")
        
        try:
            # Show some interesting stats
            stats = ingredient_service.get_ingredient_stats()
            
            st.metric("Total Ingredients", stats['total_ingredients'])
            st.metric("Ingredient Categories", len(stats['categories']))
            st.metric("Your Pantry Items", pantry_items)
            
            # Show top categories in pantry if user has items
            if pantry_items > 0:
                pantry_ingredients = [
                    ing for ing in ingredients 
                    if ing.id in st.session_state.get(browser.PANTRY_KEY, set())
                ]
                
                from collections import Counter
                category_counts = Counter(
                    ing.category or "Uncategorized" 
                    for ing in pantry_ingredients
                )
                
                st.markdown("**Top Pantry Categories:**")
                for category, count in category_counts.most_common(3):
                    st.write(f"• {category}: {count}")
        
        except Exception as e:
            st.error(f"Error loading statistics: {e}")

elif page == "🥫 My Pantry":
    browser.render_pantry_management()
    
    # Quick actions
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🍽️ Find Recipes I Can Make"):
            # Navigate to recipe browser with filter enabled
            st.session_state[f"{browser.FILTER_KEY}_makeable"] = True
            st.session_state['page'] = "📚 Recipe Browser"
            st.rerun()
    
    with col2:
        pantry_count = len(st.session_state.get(browser.PANTRY_KEY, set()))
        st.metric("Current Pantry Size", pantry_count)

elif page == "📚 Recipe Browser":
    browser.render_recipe_browser()

elif page == "📖 Recipe Details":
    # Show recipe details if a recipe is selected
    selected_recipe_id = st.session_state.get('selected_recipe_id')
    
    if selected_recipe_id:
        try:
            # Get the recipe from database
            recipe = db_service.get_recipe_by_id(selected_recipe_id, include_ingredients=True)
            
            if recipe:
                user_pantry = st.session_state.get(browser.PANTRY_KEY, set())
                browser.render_recipe_details(recipe, user_pantry)
                
                # Navigation buttons
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    if st.button("← Back to Recipe Browser"):
                        st.session_state.pop('selected_recipe_id', None)
                        st.session_state['page'] = "📚 Recipe Browser"
                        st.rerun()
                
                with col2:
                    if st.button("🥫 Manage Pantry"):
                        st.session_state['page'] = "🥫 My Pantry"
                        st.rerun()
            else:
                st.error("Recipe not found.")
                st.button("← Back to Recipe Browser", 
                         on_click=lambda: st.session_state.pop('selected_recipe_id', None))
        
        except Exception as e:
            st.error(f"Error loading recipe: {e}")
            st.button("← Back to Recipe Browser", 
                     on_click=lambda: st.session_state.pop('selected_recipe_id', None))
    
    else:
        st.info("No recipe selected. Go to Recipe Browser to select a recipe.")
        if st.button("📚 Go to Recipe Browser"):
            st.session_state['page'] = "📚 Recipe Browser"
            st.rerun()

# Footer
st.markdown("---")
st.markdown("*Built with ❤️ using Streamlit • Pans Cookbook v1.0*")