"""
Core recipe browsing UI for Pans Cookbook application.

Provides recipe filtering interface with persistent pantry management,
"Can Make" vs "Missing Ingredients" styling, and real-time search.
Leverages Herbalism app layout patterns with recipe-specific adaptations.
"""

import streamlit as st
from typing import List, Dict, Set, Optional, Any, Tuple
from collections import defaultdict
import pandas as pd

from models import Recipe, Ingredient, RecipeIngredient
from services import DatabaseService, IngredientService, get_database_service, get_ingredient_service
from services.pantry_service import PantryService, get_pantry_service
from utils import get_logger

logger = get_logger(__name__)


class RecipeBrowser:
    """
    Recipe browsing interface with persistent pantry management.
    
    Features persistent ingredient selection, recipe filtering,
    and visual indicators for recipe availability based on user's pantry.
    """
    
    def __init__(self, database_service: Optional[DatabaseService] = None, 
                 ingredient_service: Optional[IngredientService] = None,
                 pantry_service: Optional[PantryService] = None):
        self.db = database_service or get_database_service()
        self.ingredient_service = ingredient_service or get_ingredient_service()
        self.pantry_service = pantry_service or get_pantry_service(self.db)
        
        # Initialize custom CSS styling
        self._inject_custom_css()
        
        # Session state keys
        self.PANTRY_KEY = "user_pantry_ingredients"
        self.SEARCH_KEY = "recipe_search_query"
        self.FILTER_KEY = "recipe_filters"
    
    def _load_pantry_from_database(self, user_id: int = 1) -> Set[int]:
        """Load user's pantry from database and sync with session state"""
        try:
            pantry_items = self.pantry_service.get_user_pantry(user_id)
            available_ingredient_ids = {
                item.ingredient_id for item in pantry_items if item.is_available
            }
            # Update session state to match database
            st.session_state[self.PANTRY_KEY] = available_ingredient_ids
            return available_ingredient_ids
        except Exception as e:
            logger.error(f"Error loading pantry from database: {e}")
            # Fallback to session state
            return st.session_state.get(self.PANTRY_KEY, set())
    
    def _sync_pantry_to_database(self, user_id: int = 1):
        """Sync session state pantry selections to database"""
        try:
            pantry_ingredient_ids = st.session_state.get(self.PANTRY_KEY, set())
            for ingredient_id in pantry_ingredient_ids:
                self.pantry_service.update_pantry_item(user_id, ingredient_id, True, "plenty")
        except Exception as e:
            logger.error(f"Error syncing pantry to database: {e}")
    
    def render_pantry_management(self, user_id: int = 1):
        """Render the persistent pantry management interface"""
        st.header("🥫 My Pantry")
        st.markdown("Check off the ingredients you have available. Your selections will be remembered.")
        
        # Load pantry from database (this will update session state)
        current_pantry = self._load_pantry_from_database(user_id)
        
        # Get all ingredients grouped by category
        all_ingredients = self.ingredient_service.get_all_ingredients()
        ingredients_by_category = defaultdict(list)
        
        for ingredient in all_ingredients:
            category = ingredient.category or "Uncategorized"
            ingredients_by_category[category].append(ingredient)
        
        # Sort categories for consistent display
        sorted_categories = sorted(ingredients_by_category.keys())
        
        # Category filter tabs or expandable sections
        st.markdown("### Organize by Category")
        
        # Search within pantry
        search_query = st.text_input(
            "🔍 Search ingredients",
            placeholder="Search for ingredients to add to pantry...",
            key="pantry_search"
        )
        
        # Filter ingredients by search
        if search_query:
            filtered_ingredients = [
                ing for ing in all_ingredients 
                if search_query.lower() in ing.name.lower()
            ]
            
            if filtered_ingredients:
                st.markdown(f"**Search Results ({len(filtered_ingredients)} found):**")
                self._render_ingredient_checkboxes(filtered_ingredients, "search_results", user_id)
            else:
                st.info("No ingredients found matching your search.")
        
        # Show ingredients by category in expandable sections
        col1, col2 = st.columns([3, 1])
        
        with col1:
            for category in sorted_categories:
                with st.expander(f"📦 {category.title()} ({len(ingredients_by_category[category])})", expanded=False):
                    self._render_ingredient_checkboxes(
                        ingredients_by_category[category], 
                        f"category_{category}",
                        user_id
                    )
        
        with col2:
            # Pantry summary
            pantry_count = len(st.session_state[self.PANTRY_KEY])
            st.metric("Items in Pantry", pantry_count)
            
            if pantry_count > 0:
                if st.button("🗑️ Clear All", help="Remove all ingredients from pantry"):
                    st.session_state[self.PANTRY_KEY] = set()
                    st.rerun()
                
                # Show quick pantry overview
                st.markdown("**Quick Overview:**")
                pantry_ingredients = [
                    ing for ing in all_ingredients 
                    if ing.id in st.session_state[self.PANTRY_KEY]
                ]
                
                # Group by category for overview
                pantry_by_category = defaultdict(int)
                for ing in pantry_ingredients:
                    category = ing.category or "Uncategorized"
                    pantry_by_category[category] += 1
                
                for category, count in sorted(pantry_by_category.items()):
                    st.write(f"• {category}: {count}")
    
    def render_recipe_browser(self, user_id: int = 1):
        """Render the main recipe browsing interface"""
        st.header("📚 Recipe Browser")
        
        # Load pantry from database and get user's pantry
        user_pantry = self._load_pantry_from_database(user_id)
        pantry_count = len(user_pantry)
        
        if pantry_count == 0:
            st.warning("⚠️ Your pantry is empty! Add ingredients to see which recipes you can make.")
            st.info("💡 Use the 'My Pantry' page to select ingredients you have available.")
        
        # Search and filter controls
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_query = st.text_input(
                "🔍 Search recipes",
                placeholder="Search by name, cuisine, or description...",
                key=self.SEARCH_KEY
            )
        
        with col2:
            # Cuisine filter
            all_recipes = self._get_all_recipes()
            cuisines = sorted(set(r.cuisine_type for r in all_recipes if r.cuisine_type))
            selected_cuisine = st.selectbox(
                "🌍 Cuisine",
                options=["All"] + cuisines,
                key=f"{self.FILTER_KEY}_cuisine"
            )
        
        with col3:
            # Meal category filter
            categories = sorted(set(r.meal_category for r in all_recipes if r.meal_category))
            selected_category = st.selectbox(
                "🍽️ Meal Type",
                options=["All"] + categories,
                key=f"{self.FILTER_KEY}_category"
            )
        
        # Advanced filters in expander
        with st.expander("🔧 Advanced Filters"):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                difficulty_filter = st.selectbox(
                    "Difficulty Level",
                    options=["All", "easy", "medium", "hard"],
                    key=f"{self.FILTER_KEY}_difficulty"
                )
                
                # Cooking time range filter
                st.markdown("**⏱️ Cooking Time Range:**")
                time_range = st.select_slider(
                    "Total Time",
                    options=["Any", "Quick (≤30 min)", "Medium (30-60 min)", 
                             "Long (60-120 min)", "Extended (≥2 hours)"],
                    value="Any",
                    key=f"{self.FILTER_KEY}_time_range"
                )
                
                # Servings filter
                servings_range = st.slider(
                    "Number of Servings",
                    min_value=1,
                    max_value=12,
                    value=(1, 12),
                    key=f"{self.FILTER_KEY}_servings"
                )
            
            with col2:
                # Dietary restrictions filter
                st.markdown("**🌱 Dietary Restrictions:**")
                dietary_filters = st.multiselect(
                    "Must include these dietary tags",
                    options=[
                        "vegetarian", "vegan", "gluten-free", "dairy-free", "nut-free",
                        "low-carb", "keto", "paleo", "high-protein", "low-sodium"
                    ],
                    key=f"{self.FILTER_KEY}_dietary"
                )
                
                # Recipe availability filter
                show_only_makeable = st.checkbox(
                    "Show only recipes I can make",
                    key=f"{self.FILTER_KEY}_makeable"
                )
                
                # Recipe completeness filter
                require_complete = st.checkbox(
                    "Only show recipes with complete instructions",
                    key=f"{self.FILTER_KEY}_complete"
                )
        
        # Filter and display recipes
        filtered_recipes = self._filter_recipes(
            search_query, selected_cuisine, selected_category, 
            difficulty_filter, time_range, servings_range, dietary_filters,
            show_only_makeable, require_complete, user_pantry
        )
        
        # Recipe display
        if filtered_recipes:
            st.markdown(f"**Found {len(filtered_recipes)} recipes:**")
            
            # Sort recipes by "makeability"
            sorted_recipes = self._sort_recipes_by_availability(filtered_recipes, user_pantry)
            
            # Display recipes in cards
            for recipe in sorted_recipes:
                self._render_recipe_card(recipe, user_pantry)
        
        else:
            st.info("No recipes found matching your criteria.")
    
    def render_recipe_details(self, recipe: Recipe, user_pantry: Set[int]):
        """Render detailed view of a specific recipe"""
        st.header(f"📖 {recipe.name}")
        
        # Recipe metadata
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        
        with col1:
            st.metric("Prep Time", f"{recipe.prep_time_minutes} min")
        with col2:
            st.metric("Cook Time", f"{recipe.cook_time_minutes} min")
        with col3:
            st.metric("Total Time", f"{recipe.get_total_time_minutes()} min")
        with col4:
            st.metric("Servings", recipe.servings)
        
        # Recipe info
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if recipe.description:
                st.markdown("**Description:**")
                st.write(recipe.description)
        
        with col2:
            st.markdown("**Details:**")
            st.write(f"**Difficulty:** {recipe.difficulty_level.title()}")
            if recipe.cuisine_type:
                st.write(f"**Cuisine:** {recipe.cuisine_type}")
            if recipe.meal_category:
                st.write(f"**Category:** {recipe.meal_category.title()}")
            if recipe.dietary_tags:
                st.write(f"**Tags:** {', '.join(recipe.dietary_tags)}")
        
        # Ingredient analysis
        recipe_ingredients = self._get_recipe_ingredients(recipe.id)
        if recipe_ingredients:
            st.markdown("### 🥕 Ingredients")
            
            # Calculate availability
            required_ingredient_ids = {ri.ingredient_id for ri in recipe_ingredients}
            available_ids = required_ingredient_ids & user_pantry
            missing_ids = required_ingredient_ids - user_pantry
            
            # Availability status
            if len(missing_ids) == 0:
                st.success("✅ You have all ingredients needed!")
            elif len(available_ids) > 0:
                st.warning(f"⚠️ You have {len(available_ids)}/{len(required_ingredient_ids)} ingredients. Missing {len(missing_ids)} ingredients.")
            else:
                st.error("❌ You don't have any of the required ingredients.")
            
            # Display ingredients with status
            for recipe_ingredient in recipe_ingredients:
                ingredient = self.ingredient_service.get_ingredient(recipe_ingredient.ingredient_id)
                if ingredient:
                    # Format ingredient display
                    display_text = recipe_ingredient.get_display_text()
                    if recipe_ingredient.preparation_note:
                        display_text += f" {ingredient.name}, {recipe_ingredient.preparation_note}"
                    else:
                        display_text += f" {ingredient.name}"
                    
                    # Show availability status
                    if ingredient.id in user_pantry:
                        st.markdown(f'<div class="owned-ingredient">✅ {display_text}</div>', 
                                  unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="missing-ingredient">❌ {display_text}</div>', 
                                  unsafe_allow_html=True)
        
        # Instructions
        if recipe.instructions:
            st.markdown("### 📋 Instructions")
            st.markdown(recipe.instructions)
        
        # Source info
        if recipe.source_url:
            st.markdown("### 🔗 Source")
            st.markdown(f"[Original Recipe]({recipe.source_url})")
    
    def _render_ingredient_checkboxes(self, ingredients: List[Ingredient], container_key: str, user_id: int = 1):
        """Render ingredient checkboxes for pantry management"""
        # Sort ingredients alphabetically
        sorted_ingredients = sorted(ingredients, key=lambda x: x.name)
        
        # Create columns for better layout
        num_cols = min(3, max(1, len(sorted_ingredients) // 10))
        cols = st.columns(num_cols)
        
        for i, ingredient in enumerate(sorted_ingredients):
            col = cols[i % num_cols]
            
            with col:
                # Check if ingredient is in pantry
                is_checked = ingredient.id in st.session_state[self.PANTRY_KEY]
                
                # Create checkbox
                checked = st.checkbox(
                    ingredient.name,
                    value=is_checked,
                    key=f"pantry_check_{container_key}_{ingredient.id}"
                )
                
                # Update pantry state and sync to database
                if checked and not is_checked:
                    st.session_state[self.PANTRY_KEY].add(ingredient.id)
                    # Add to database
                    self.pantry_service.update_pantry_item(user_id, ingredient.id, True, "plenty")
                elif not checked and is_checked:
                    st.session_state[self.PANTRY_KEY].discard(ingredient.id)
                    # Remove from database
                    self.pantry_service.update_pantry_item(user_id, ingredient.id, False, None)
    
    def _render_recipe_card(self, recipe: Recipe, user_pantry: Set[int]):
        """Render a recipe card with availability status"""
        # Get recipe ingredients for analysis
        recipe_ingredients = self._get_recipe_ingredients(recipe.id)
        required_ingredient_ids = {ri.ingredient_id for ri in recipe_ingredients}
        
        # Calculate availability
        available_count = len(required_ingredient_ids & user_pantry)
        missing_count = len(required_ingredient_ids - user_pantry)
        total_ingredients = len(required_ingredient_ids)
        
        # Determine status
        if missing_count == 0:
            status_class = "craft-status-can-make"
            status_text = "✅ Can Make!"
            status_color = "#1B5E20"
        elif available_count > 0:
            status_class = "craft-status-missing"
            status_text = f"⚠️ Missing {missing_count} ingredients"
            status_color = "#E65100"
        else:
            status_class = "craft-status-missing"
            status_text = "❌ Need ingredients"
            status_color = "#B71C1C"
        
        # Create recipe card
        with st.container():
            st.markdown(f"""
            <div style="border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin: 1rem 0; background-color: white;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h3 style="margin: 0; color: #1976D2;">{recipe.name}</h3>
                        <p style="margin: 0.5rem 0; color: #666;">
                            {recipe.cuisine_type} • {recipe.meal_category} • {recipe.get_total_time_minutes()} min • {recipe.servings} servings
                        </p>
                        <div class="{status_class}" style="color: {status_color}; font-weight: bold;">
                            {status_text}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 1.2em; color: #1976D2;">
                            {available_count}/{total_ingredients} ingredients
                        </div>
                        <div style="color: #666;">
                            {recipe.difficulty_level.title()} difficulty
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Recipe details button
            if st.button(f"View Recipe Details", key=f"view_recipe_{recipe.id}"):
                st.session_state['selected_recipe_id'] = recipe.id
                st.rerun()
    
    def _get_all_recipes(self) -> List[Recipe]:
        """Get all recipes from database"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM recipes ORDER BY name")
                rows = cursor.fetchall()
                
                recipes = []
                for row in rows:
                    recipe = self.db._row_to_recipe(row)
                    # Load ingredient relationships
                    recipe.required_ingredient_ids = self.db._get_recipe_ingredient_ids(recipe.id, conn)
                    recipes.append(recipe)
                
                return recipes
        except Exception as e:
            logger.error(f"Error loading recipes: {e}")
            return []
    
    def _get_recipe_ingredients(self, recipe_id: int) -> List[RecipeIngredient]:
        """Get recipe ingredients for a specific recipe"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM recipe_ingredients 
                    WHERE recipe_id = ? 
                    ORDER BY ingredient_order, ingredient_id
                """, (recipe_id,))
                
                rows = cursor.fetchall()
                return [self.db._row_to_recipe_ingredient(row) for row in rows]
        except Exception as e:
            logger.error(f"Error loading recipe ingredients: {e}")
            return []
    
    def _filter_recipes(self, search_query: str, cuisine: str, category: str, 
                       difficulty: str, time_range: str, servings_range: Tuple[int, int],
                       dietary_filters: List[str], show_only_makeable: bool, 
                       require_complete: bool, user_pantry: Set[int]) -> List[Recipe]:
        """Filter recipes based on comprehensive criteria"""
        recipes = self._get_all_recipes()
        
        # Apply filters
        filtered = []
        for recipe in recipes:
            # Search filter
            if search_query:
                search_lower = search_query.lower()
                if not (search_lower in recipe.name.lower() or 
                       search_lower in (recipe.description or "").lower() or
                       search_lower in (recipe.cuisine_type or "").lower()):
                    continue
            
            # Cuisine filter
            if cuisine != "All" and recipe.cuisine_type != cuisine:
                continue
            
            # Category filter
            if category != "All" and recipe.meal_category != category:
                continue
            
            # Difficulty filter
            if difficulty != "All" and recipe.difficulty_level != difficulty:
                continue
            
            # Time range filter
            total_time = recipe.get_total_time_minutes()
            if time_range != "Any":
                if time_range == "Quick (≤30 min)" and total_time > 30:
                    continue
                elif time_range == "Medium (30-60 min)" and (total_time <= 30 or total_time > 60):
                    continue
                elif time_range == "Long (60-120 min)" and (total_time <= 60 or total_time > 120):
                    continue
                elif time_range == "Extended (≥2 hours)" and total_time < 120:
                    continue
            
            # Servings range filter
            if not (servings_range[0] <= recipe.servings <= servings_range[1]):
                continue
            
            # Dietary restrictions filter
            if dietary_filters:
                recipe_tags = [tag.lower() for tag in recipe.dietary_tags]
                if not all(diet_filter.lower() in recipe_tags for diet_filter in dietary_filters):
                    continue
            
            # Recipe completeness filter
            if require_complete:
                if not recipe.instructions or len(recipe.instructions.strip()) < 50:
                    continue
            
            # Makeability filter
            if show_only_makeable:
                missing_ingredients = recipe.required_ingredient_ids - user_pantry
                if len(missing_ingredients) > 0:
                    continue
            
            filtered.append(recipe)
        
        return filtered
    
    def _sort_recipes_by_availability(self, recipes: List[Recipe], user_pantry: Set[int]) -> List[Recipe]:
        """Sort recipes by ingredient availability (can make first)"""
        def availability_score(recipe: Recipe) -> Tuple[int, int, str]:
            missing_count = len(recipe.required_ingredient_ids - user_pantry)
            available_count = len(recipe.required_ingredient_ids & user_pantry)
            
            # Sort by: 1) Can make (missing=0), 2) Available ingredient count (desc), 3) Recipe name
            return (missing_count, -available_count, recipe.name)
        
        return sorted(recipes, key=availability_score)
    
    def _inject_custom_css(self):
        """Inject custom CSS styling adapted from Herbalism app"""
        st.markdown("""
        <style>
            .owned-ingredient {
                color: #2E7D32;
                font-weight: bold;
                background-color: #E8F5E9;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #A5D6A7;
                margin: 2px 0;
                display: inline-block;
            }
            .missing-ingredient {
                color: #C62828;
                background-color: #FFEBEE;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #EF9A9A;
                margin: 2px 0;
                display: inline-block;
            }
            .craft-status-can-make {
                color: #1B5E20;
                font-weight: bold;
            }
            .craft-status-missing {
                color: #E65100;
                font-weight: bold;
            }
            .recipe-card {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 1rem;
                margin: 1rem 0;
                background-color: #fafafa;
                transition: box-shadow 0.3s ease;
            }
            .recipe-card:hover {
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .pantry-section {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 1rem;
                margin: 1rem 0;
            }
        </style>
        """, unsafe_allow_html=True)


def create_recipe_browser(database_service: Optional[DatabaseService] = None,
                         ingredient_service: Optional[IngredientService] = None,
                         pantry_service: Optional[PantryService] = None) -> RecipeBrowser:
    """Factory function to create recipe browser"""
    return RecipeBrowser(database_service, ingredient_service, pantry_service)