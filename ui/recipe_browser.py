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
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_query = st.text_input(
                "🔍 Search recipes",
                placeholder="Search by name or description...",
                key=self.SEARCH_KEY
            )
        
        with col2:
            # Placeholder for future filters if needed
            st.write("")  # Empty space for layout consistency
        
        # Advanced filters in expander
        with st.expander("🔧 Advanced Filters"):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                difficulty_filter = st.selectbox(
                    "Difficulty Level",
                    options=["All"],
                    key=f"{self.FILTER_KEY}_difficulty",
                    disabled=True,
                    help="Difficulty levels removed in simplified schema"
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
                # Dietary restrictions filter - disabled for simplified schema
                st.markdown("**🌱 Dietary Restrictions:**")
                dietary_filters = st.multiselect(
                    "Must include these dietary tags",
                    options=[],
                    key=f"{self.FILTER_KEY}_dietary",
                    disabled=True,
                    help="Dietary tags removed in simplified schema"
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
            search_query, difficulty_filter, time_range, servings_range, dietary_filters,
            show_only_makeable, require_complete, user_pantry
        )
        
        # Recipe display
        if filtered_recipes:
            st.markdown(f"**Found {len(filtered_recipes)} recipes:**")
            
            # Sort recipes by "makeability"
            sorted_recipes = self._sort_recipes_by_availability(filtered_recipes, user_pantry)
            
            # Display recipes in grid layout
            self._render_recipe_grid(sorted_recipes, user_pantry)
        
        else:
            st.info("No recipes found matching your criteria.")
    
    def render_recipe_details(self, recipe: Recipe, user_pantry: Set[int]):
        """Render detailed view of a specific recipe in standard cookbook format"""
        
        # 1. RECIPE TITLE (full width across top)
        st.title(recipe.name)
        
        # Delete confirmation dialog (if active)
        if st.session_state.get(f'confirm_delete_detail_{recipe.id}', False):
            st.error(f"⚠️ Are you sure you want to delete '{recipe.name}'? This action cannot be undone.")
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Yes, Delete", key=f"confirm_delete_detail_yes_{recipe.id}", type="primary"):
                    if self.db.delete_recipe(recipe.id):
                        st.success(f"Recipe '{recipe.name}' deleted!")
                        if 'selected_recipe_id' in st.session_state:
                            del st.session_state['selected_recipe_id']
                        del st.session_state[f'confirm_delete_detail_{recipe.id}']
                        st.rerun()
                    else:
                        st.error("Failed to delete recipe.")
            with col2:
                if st.button("Cancel", key=f"cancel_delete_detail_{recipe.id}"):
                    del st.session_state[f'confirm_delete_detail_{recipe.id}']
                    st.rerun()
            st.markdown("---")
        
        # 2. IMAGE + INGREDIENTS (side by side - standard cookbook layout)
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Recipe detail image - processed images are perfect 200x200 squares
            if recipe.image_path and self._image_exists(recipe.image_path):
                # Display processed 200x200 image (fits nicely in detail view)
                st.image(recipe.image_path, width=200)
            else:
                # Placeholder image with same size  
                st.markdown("""
                <div class="recipe-placeholder-image">
                    <div class="placeholder-content">
                        📷<br>
                        <span class="placeholder-text">No image uploaded<br><small>Upload a photo to make this recipe more appealing!</small></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Compact image upload - thin bar style
            st.markdown("**Add Photo:**")
            uploaded_file = st.file_uploader(
                "Browse files", 
                type=['png', 'jpg', 'jpeg', 'gif'],
                key=f"image_upload_{recipe.id}",
                label_visibility="collapsed"
            )
            
            if uploaded_file is not None:
                if st.button(f"Save Image", key=f"save_image_{recipe.id}", use_container_width=True):
                    success, image_path = self._save_recipe_image(recipe.id, uploaded_file)
                    if success:
                        st.success("Image uploaded!")
                        if self.db.update_recipe_image(recipe.id, image_path):
                            st.rerun()
                        else:
                            st.error("Failed to save image")
                    else:
                        st.error("Upload failed")
        
        with col2:
            # 3. INGREDIENTS SECTION (traditional cookbook format - moved to right column)
            recipe_ingredients = self._get_recipe_ingredients(recipe.id)
            if recipe_ingredients:
                st.markdown("## Ingredients")
                
                # Calculate availability for quick reference
                required_ingredient_ids = {ri.ingredient_id for ri in recipe_ingredients}
                available_ids = required_ingredient_ids & user_pantry
                missing_ids = required_ingredient_ids - user_pantry
                
                # Quick availability indicator (compact)
                if len(missing_ids) == 0:
                    st.success("✅ You have all ingredients")
                elif len(available_ids) > 0:
                    st.warning(f"⚠️ Missing {len(missing_ids)} ingredients")
                else:
                    st.info("ℹ️ Check pantry for ingredients")
                
                # Traditional ingredients list (plain text format for reading)
                for recipe_ingredient in recipe_ingredients:
                    ingredient = self.ingredient_service.get_ingredient(recipe_ingredient.ingredient_id)
                    if ingredient:
                        # Create readable ingredient text (can include descriptive terms)
                        # e.g., "2 tbsp butter, melted" instead of just "2 tbsp butter"
                        display_text = recipe_ingredient.get_display_text()
                        if recipe_ingredient.preparation_note:
                            # Format as "quantity unit ingredient, preparation"
                            display_text += f" {ingredient.name}, {recipe_ingredient.preparation_note}"
                        else:
                            display_text += f" {ingredient.name}"
                        
                        # Show with simple availability indicator
                        if ingredient.id in user_pantry:
                            st.markdown(f"✅ {display_text}")
                        else:
                            st.markdown(f"◯ {display_text}")
                
                # Expandable structured ingredient details (for system/editing purposes)
                with st.expander("🔧 Structured Ingredient Data", expanded=False):
                    st.markdown("**System ingredient mappings for recipe analysis:**")
                    
                    # Table format for structured data
                    structured_data = []
                    for recipe_ingredient in recipe_ingredients:
                        ingredient = self.ingredient_service.get_ingredient(recipe_ingredient.ingredient_id)
                        if ingredient:
                            structured_data.append({
                                "Order": recipe_ingredient.ingredient_order or 0,
                                "Quantity": recipe_ingredient.quantity,
                                "Unit": recipe_ingredient.unit,
                                "Ingredient": ingredient.name,
                                "Category": ingredient.category,
                                "Preparation": recipe_ingredient.preparation_note or "-",
                                "Optional": "Yes" if recipe_ingredient.is_optional else "No"
                            })
                    
                    if structured_data:
                        import pandas as pd
                        df = pd.DataFrame(structured_data)
                        df = df.sort_values("Order")
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        
                        st.markdown("*This structured data enables the 'What Can I Make' feature and ingredient tracking.*")
        
        # 4. DESCRIPTION SECTION (moved below image/ingredients)
        if recipe.description:
            st.markdown("## Description")
            st.write(recipe.description)
        
        # 5. INSTRUCTIONS SECTION (standard cookbook format)
        if recipe.instructions:
            st.markdown("## Instructions")
            st.markdown(recipe.instructions)
        
        # 6. ADDITIONAL INFO (compact format)
        if recipe.source_url:
            st.markdown("**Source:** " + f"[Original Recipe]({recipe.source_url})")
        
        st.markdown("---")
        
        # 7. TIMING INFO (bottom, small text as requested)
        if recipe.prep_time_minutes > 0 or recipe.cook_time_minutes > 0:
            timing_info = []
            if recipe.prep_time_minutes > 0:
                timing_info.append(f"Prep: {recipe.prep_time_minutes} min")
            if recipe.cook_time_minutes > 0:
                timing_info.append(f"Cook: {recipe.cook_time_minutes} min")
            if len(timing_info) > 0:
                total_time = recipe.get_total_time_minutes()
                timing_info.append(f"Total: {total_time} min")
                
                st.markdown(f"<small>⏱️ {' | '.join(timing_info)} | Serves {recipe.servings}</small>", 
                           unsafe_allow_html=True)
        
        # 8. ACTION BUTTONS (bottom as requested)
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("🏠 Back to Recipes", key=f"back_from_detail_{recipe.id}"):
                if 'selected_recipe_id' in st.session_state:
                    del st.session_state['selected_recipe_id']
                st.rerun()
        
        with col2:
            if st.button("✏️ Edit", key=f"edit_detail_{recipe.id}"):
                st.info("Edit functionality coming soon")
        
        with col3:
            if st.button("🗑️ Delete Recipe", key=f"delete_detail_{recipe.id}", type="secondary"):
                st.session_state[f'confirm_delete_detail_{recipe.id}'] = True
                st.rerun()
    
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
        """Render a recipe card with uniform sizing and placeholder images"""
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
        
        # Create uniform recipe card with fixed sizing
        with st.container():
            st.markdown('<div class="recipe-card-container">', unsafe_allow_html=True)
            
            # Recipe image as clickable button - no extra elements
            has_image = recipe.image_path and self._image_exists(recipe.image_path)
            
            # Simple approach: One button, one image, make it work
            if has_image:
                # Display image first
                st.markdown(f"""
                <div class="recipe-image-container">
                    <img src="data:image/jpeg;base64,{self._get_image_base64(recipe.image_path)}" alt="{recipe.name}">
                    <div class="recipe-title-overlay">
                        <span class="recipe-title-text">{recipe.name}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Display placeholder
                st.markdown(f"""
                <div class="recipe-placeholder-container">
                    <div class="placeholder-content">
                        🍽️<br>
                        <span class="placeholder-text">No Image</span>
                    </div>
                    <div class="recipe-title-overlay">
                        <span class="recipe-title-text">{recipe.name}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Simple generic button - recipe name is shown in overlay
            if st.button("Recipe", key=f"recipe_click_{recipe.id}"):
                st.session_state['selected_recipe_id'] = recipe.id
                st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    def _render_recipe_grid(self, recipes: List[Recipe], user_pantry: Set[int]):
        """Render recipes in a simple responsive grid layout"""
        # Create 4 columns for very compact cards
        recipes_per_row = 4
        
        # Group recipes into rows
        for i in range(0, len(recipes), recipes_per_row):
            row_recipes = recipes[i:i + recipes_per_row]
            cols = st.columns(recipes_per_row)
            
            for j, recipe in enumerate(row_recipes):
                with cols[j]:
                    self._render_recipe_card(recipe, user_pantry)
                    st.markdown("---")  # Add separator between cards
    
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
    
    def _filter_recipes(self, search_query: str, difficulty: str, time_range: str, 
                       servings_range: Tuple[int, int], dietary_filters: List[str], 
                       show_only_makeable: bool, require_complete: bool, user_pantry: Set[int]) -> List[Recipe]:
        """Filter recipes based on comprehensive criteria"""
        recipes = self._get_all_recipes()
        
        # Apply filters
        filtered = []
        for recipe in recipes:
            # Search filter
            if search_query:
                search_lower = search_query.lower()
                if not (search_lower in recipe.name.lower() or 
                       search_lower in (recipe.description or "").lower()):
                    continue
            
            # Category filter - disabled for simplified schema
            # (meal_category removed)
            
            # Difficulty filter - disabled for simplified schema
            # (difficulty_level removed)
            
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
            
            # Dietary restrictions filter - disabled for simplified schema
            # (dietary_tags removed)
            
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
            .recipe-grid {
                display: flex;
                flex-wrap: wrap;
                gap: 1rem;
                justify-content: flex-start;
            }
            .recipe-card-compact {
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            .recipe-card-compact:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }
            
            /* Recipe card container */
            .recipe-card-container {
                display: flex;
                flex-direction: column;
                height: 100%;
                align-items: stretch;
            }
            
            /* Recipe card containers - all elements exactly 200px wide */
            .recipe-card-container {
                display: flex;
                flex-direction: column;
                width: 200px; /* Fixed width container */
                align-items: center;
            }
            
            /* Simple recipe image container */
            .recipe-image-container {
                width: 200px;
                height: 200px;
                position: relative;
                border-radius: 8px;
                overflow: hidden;
                margin-bottom: 0.5rem;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            
            .recipe-image-container:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }
            
            .recipe-image-container img {
                width: 200px;
                height: 200px;
                object-fit: cover;
                display: block;
            }
            
            /* Simple recipe placeholder container */
            .recipe-placeholder-container {
                width: 200px;
                height: 200px;
                position: relative;
                border-radius: 8px;
                overflow: hidden;
                margin-bottom: 0.5rem;
                background: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%);
                border: 2px dashed #ccc;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            
            .recipe-placeholder-container:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }
            
            /* Style the recipe buttons to match the image width */
            .recipe-card-container .stButton {
                width: 200px !important;
            }
            
            .recipe-card-container .stButton > button {
                width: 200px !important;
                max-width: 200px !important;
                background: #1f77b4 !important;
                color: white !important;
                border-radius: 6px !important;
                font-size: 0.8rem !important;
                padding: 0.5rem !important;
                margin-top: 0.25rem !important;
            }
            
            /* Text overlay at bottom of image */
            .recipe-title-overlay {
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                background: linear-gradient(transparent, rgba(0,0,0,0.7));
                padding: 20px 8px 8px;
                color: white;
                text-align: center;
            }
            
            .recipe-title-text {
                font-size: 0.9rem;
                font-weight: 600;
                line-height: 1.2;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }
            
            .placeholder-content {
                text-align: center;
                color: #888;
                font-size: 2rem;
            }
            
            .placeholder-text {
                font-size: 0.8rem;
                display: block;
                margin-top: 0.25rem;
                color: #666;
            }
            
            /* Recipe detail placeholder image */
            .recipe-placeholder-image {
                width: 200px;
                height: 200px;
                background: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%);
                border: 2px dashed #ccc;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 1rem;
            }
            
            .recipe-placeholder-image .placeholder-content {
                text-align: center;
                color: #888;
                font-size: 2rem;
            }
            
            .recipe-placeholder-image .placeholder-text {
                font-size: 0.8rem;
                display: block;
                margin-top: 0.25rem;
                color: #666;
            }
            
            /* Responsive adjustments - keep everything aligned */
            @media (max-width: 768px) {
                .recipe-card-container {
                    width: 150px;
                }
                
                .recipe-placeholder-image {
                    width: 150px;
                    height: 150px;
                }
                
                .recipe-card-container button,
                .recipe-card-container .stButton > button {
                    width: 150px !important;
                    max-width: 150px !important;
                    height: 3rem !important;
                    min-height: 3rem !important;
                    font-size: 0.8rem !important;
                }
                
                .placeholder-content {
                    font-size: 1.2rem;
                }
                
                .placeholder-text {
                    font-size: 0.6rem;
                }
            }
            
            @media (max-width: 480px) {
                .recipe-card-container {
                    width: 120px;
                }
                
                .recipe-placeholder-image {
                    width: 120px;
                    height: 120px;
                }
                
                .recipe-card-container button,
                .recipe-card-container .stButton > button {
                    width: 120px !important;
                    max-width: 120px !important;
                    height: 3rem !important;
                    min-height: 3rem !important;
                    font-size: 0.7rem !important;
                }
                
                .placeholder-content {
                    font-size: 1rem;
                }
                
                .placeholder-text {
                    font-size: 0.5rem;
                }
            }
        </style>
        """, unsafe_allow_html=True)
    
    def _image_exists(self, image_path: str) -> bool:
        """Check if image file exists"""
        import os
        if not image_path:
            return False
        
        # Check if path is absolute or relative
        if not os.path.isabs(image_path):
            # If relative, check both from current directory and static directory
            current_dir_path = os.path.join(os.getcwd(), image_path)
            static_path = os.path.join(os.getcwd(), "static", "recipe_images", os.path.basename(image_path))
            return os.path.exists(current_dir_path) or os.path.exists(static_path)
        else:
            return os.path.exists(image_path)
    
    def _get_image_base64(self, image_path: str) -> str:
        """Convert image to base64 for inline HTML display"""
        import base64
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode()
        except Exception as e:
            logger.error(f"Failed to encode image to base64: {e}")
            return ""
    
    def _save_recipe_image(self, recipe_id: int, uploaded_file) -> Tuple[bool, str]:
        """Process and save uploaded image as perfect 200x200 square"""
        import os
        import uuid
        from pathlib import Path
        
        try:
            # Import Pillow for image processing (compatible with Streamlit)
            from PIL import Image
            
            # Create static/recipe_images directory if it doesn't exist
            images_dir = Path("static/recipe_images")
            images_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename (always save as .jpg for consistency)
            unique_filename = f"recipe_{recipe_id}_{uuid.uuid4().hex[:8]}.jpg"
            file_path = images_dir / unique_filename
            
            # Process the uploaded image using Pillow (Streamlit compatible)
            logger.info(f"Processing image for recipe {recipe_id}")
            
            # Open the uploaded file with Pillow
            image = Image.open(uploaded_file)
            
            # Convert to RGB if necessary (handles PNG transparency, etc.)
            if image.mode != 'RGB':
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image)
                image = background
            
            # Create perfect square by center cropping
            width, height = image.size
            crop_size = min(width, height)
            
            # Calculate center crop coordinates
            left = (width - crop_size) // 2
            top = (height - crop_size) // 2
            right = left + crop_size
            bottom = top + crop_size
            
            # Crop to square and resize to exactly 200x200
            image_square = image.crop((left, top, right, bottom))
            image_final = image_square.resize((200, 200), Image.Resampling.LANCZOS)
            
            # Save as optimized JPEG (smaller file size)
            image_final.save(file_path, 'JPEG', quality=85, optimize=True)
            
            # Return relative path for database storage
            relative_path = str(file_path)
            logger.info(f"Successfully processed and saved 200x200 image: {relative_path}")
            return True, relative_path
            
        except Exception as e:
            logger.error(f"Failed to process and save recipe image: {e}")
            import traceback
            traceback.print_exc()
            return False, ""


def create_recipe_browser(database_service: Optional[DatabaseService] = None,
                         ingredient_service: Optional[IngredientService] = None,
                         pantry_service: Optional[PantryService] = None) -> RecipeBrowser:
    """Factory function to create recipe browser"""
    return RecipeBrowser(database_service, ingredient_service, pantry_service)