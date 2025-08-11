"""
Recipe details and editing interface for Pans Cookbook application.

Provides comprehensive recipe viewing with editing capabilities,
nutrition information display, dietary tag filtering, and cooking time filters.
Leverages Herbalism app styling patterns with recipe-specific layouts.
"""

import streamlit as st
from typing import List, Dict, Set, Optional, Any, Tuple
from datetime import datetime
import json

from models import Recipe, Ingredient, RecipeIngredient, NutritionData
from services import DatabaseService, IngredientService, get_database_service, get_ingredient_service
from utils import get_logger

logger = get_logger(__name__)


class RecipeDetailsInterface:
    """
    Comprehensive recipe details and editing interface.
    
    Provides detailed recipe viewing, in-place editing capabilities,
    nutrition information display, and advanced filtering options.
    """
    
    def __init__(self, database_service: Optional[DatabaseService] = None,
                 ingredient_service: Optional[IngredientService] = None):
        self.db = database_service or get_database_service()
        self.ingredient_service = ingredient_service or get_ingredient_service()
        
        # Initialize custom CSS styling
        self._inject_custom_css()
        
        # Available dietary tags
        self.DIETARY_TAGS = [
            "vegetarian", "vegan", "gluten-free", "dairy-free", "nut-free",
            "low-carb", "keto", "paleo", "mediterranean", "high-protein", 
            "low-sodium", "sugar-free", "whole30", "raw", "kosher", "halal"
        ]
        
        # Difficulty levels
        self.DIFFICULTY_LEVELS = ["easy", "medium", "hard"]
        
        # Cuisine types
        self.CUISINE_TYPES = [
            "American", "Italian", "Mexican", "Chinese", "Indian", "French",
            "Thai", "Japanese", "Mediterranean", "Greek", "Spanish", "Korean",
            "Vietnamese", "Middle Eastern", "Caribbean", "African", "Other"
        ]
        
        # Meal categories
        self.MEAL_CATEGORIES = [
            "breakfast", "brunch", "lunch", "dinner", "snack", "dessert",
            "appetizer", "side dish", "beverage", "sauce", "marinade"
        ]
    
    def render_recipe_details(self, recipe: Recipe, user_pantry: Set[int], 
                             edit_mode: bool = False) -> Optional[Recipe]:
        """
        Render comprehensive recipe details with optional editing.
        
        Args:
            recipe: Recipe to display/edit
            user_pantry: Set of ingredient IDs user has available
            edit_mode: Whether to show in edit mode
            
        Returns:
            Updated recipe if saved, None otherwise
        """
        if edit_mode:
            return self._render_edit_mode(recipe, user_pantry)
        else:
            return self._render_view_mode(recipe, user_pantry)
    
    def _render_view_mode(self, recipe: Recipe, user_pantry: Set[int]) -> Optional[Recipe]:
        """Render recipe in view mode with detailed information"""
        # Header with action buttons
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.header(f"📖 {recipe.name}")
            if recipe.source_url:
                st.markdown(f"[🔗 Original Source]({recipe.source_url})")
        
        with col2:
            if st.button("✏️ Edit Recipe", key="edit_recipe_btn"):
                st.session_state['edit_mode'] = True
                st.rerun()
        
        with col3:
            if st.button("⭐ Add to Favorites", key="favorite_recipe_btn"):
                self._add_to_favorites(recipe.id)
                st.success("Added to favorites!")
        
        # Recipe metadata metrics
        self._render_recipe_metrics(recipe)
        
        # Recipe information tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📋 Overview", "🥕 Ingredients", "👨‍🍳 Instructions", 
            "📊 Nutrition", "🏷️ Tags & Info"
        ])
        
        with tab1:
            self._render_overview_tab(recipe, user_pantry)
        
        with tab2:
            self._render_ingredients_tab(recipe, user_pantry)
        
        with tab3:
            self._render_instructions_tab(recipe)
        
        with tab4:
            self._render_nutrition_tab(recipe)
        
        with tab5:
            self._render_tags_info_tab(recipe)
        
        return None
    
    def _render_edit_mode(self, recipe: Recipe, user_pantry: Set[int]) -> Optional[Recipe]:
        """Render recipe in edit mode with forms"""
        st.header(f"✏️ Editing: {recipe.name}")
        
        with st.form("recipe_edit_form", clear_on_submit=False):
            # Basic information
            st.subheader("📝 Basic Information")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                name = st.text_input("Recipe Name", value=recipe.name, key="edit_name")
                description = st.text_area(
                    "Description", 
                    value=recipe.description or "",
                    height=100,
                    key="edit_description"
                )
            
            with col2:
                source_url = st.text_input(
                    "Source URL", 
                    value=recipe.source_url or "",
                    key="edit_source"
                )
            
            # Time and serving information
            st.subheader("⏱️ Time & Servings")
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            
            with col1:
                prep_time = st.number_input(
                    "Prep Time (minutes)",
                    min_value=0,
                    max_value=600,
                    value=recipe.prep_time_minutes,
                    key="edit_prep_time"
                )
            
            with col2:
                cook_time = st.number_input(
                    "Cook Time (minutes)",
                    min_value=0,
                    max_value=1440,
                    value=recipe.cook_time_minutes,
                    key="edit_cook_time"
                )
            
            with col3:
                servings = st.number_input(
                    "Servings",
                    min_value=1,
                    max_value=50,
                    value=recipe.servings,
                    key="edit_servings"
                )
            
            with col4:
                difficulty = st.selectbox(
                    "Difficulty",
                    options=self.DIFFICULTY_LEVELS,
                    index=self.DIFFICULTY_LEVELS.index(recipe.difficulty_level),
                    key="edit_difficulty"
                )
            
            # Category information
            st.subheader("🏷️ Categories")
            col1, col2 = st.columns([1, 1])
            
            with col1:
                cuisine_index = 0
                if recipe.cuisine_type in self.CUISINE_TYPES:
                    cuisine_index = self.CUISINE_TYPES.index(recipe.cuisine_type)
                
                cuisine = st.selectbox(
                    "Cuisine Type",
                    options=[""] + self.CUISINE_TYPES,
                    index=cuisine_index,
                    key="edit_cuisine"
                )
            
            with col2:
                category_index = 0
                if recipe.meal_category in self.MEAL_CATEGORIES:
                    category_index = self.MEAL_CATEGORIES.index(recipe.meal_category) + 1
                
                meal_category = st.selectbox(
                    "Meal Category",
                    options=[""] + self.MEAL_CATEGORIES,
                    index=category_index,
                    key="edit_meal_category"
                )
            
            # Dietary tags
            st.subheader("🌱 Dietary Tags")
            dietary_tags = st.multiselect(
                "Select applicable dietary tags",
                options=self.DIETARY_TAGS,
                default=recipe.dietary_tags,
                key="edit_dietary_tags"
            )
            
            # Instructions
            st.subheader("👨‍🍳 Cooking Instructions")
            instructions = st.text_area(
                "Step-by-step instructions",
                value=recipe.instructions,
                height=200,
                help="Enter each step on a new line or number them (1., 2., etc.)",
                key="edit_instructions"
            )
            
            # Ingredients editing (simplified - full ingredient management would be complex)
            st.subheader("🥕 Ingredients")
            st.info("💡 For detailed ingredient editing, use the Recipe Builder or import from scraping.")
            
            current_ingredients = self._get_recipe_ingredients(recipe.id)
            if current_ingredients:
                st.markdown("**Current ingredients:**")
                for ri in current_ingredients:
                    ingredient = self.ingredient_service.get_ingredient(ri.ingredient_id)
                    if ingredient:
                        display_text = f"{ri.quantity} {ri.unit} {ingredient.name}"
                        if ri.preparation_note:
                            display_text += f" ({ri.preparation_note})"
                        st.write(f"• {display_text}")
            
            # Nutrition information (optional)
            with st.expander("📊 Nutrition Information (Optional)"):
                self._render_nutrition_edit_form(recipe)
            
            # Form submission
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.form_submit_button("💾 Save Changes", type="primary"):
                    # Create updated recipe
                    updated_recipe = self._create_updated_recipe(
                        recipe, name, description, source_url, prep_time, cook_time,
                        servings, difficulty, cuisine, meal_category, dietary_tags, instructions
                    )
                    
                    # Save to database
                    if self._save_recipe_changes(updated_recipe):
                        st.success("✅ Recipe saved successfully!")
                        st.session_state.pop('edit_mode', None)
                        st.rerun()
                    else:
                        st.error("❌ Failed to save recipe changes.")
            
            with col2:
                if st.form_submit_button("🚫 Cancel"):
                    st.session_state.pop('edit_mode', None)
                    st.rerun()
            
            with col3:
                if st.form_submit_button("🗑️ Delete Recipe", type="secondary"):
                    if self._confirm_delete_recipe(recipe.id):
                        st.success("Recipe deleted successfully!")
                        # Navigate away from deleted recipe
                        st.session_state.pop('selected_recipe_id', None)
                        st.session_state.pop('edit_mode', None)
                        st.rerun()
        
        return None
    
    def _render_recipe_metrics(self, recipe: Recipe):
        """Render recipe metrics display"""
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
        
        with col1:
            st.metric("Prep Time", f"{recipe.prep_time_minutes} min")
        with col2:
            st.metric("Cook Time", f"{recipe.cook_time_minutes} min")
        with col3:
            st.metric("Total Time", f"{recipe.get_total_time_minutes()} min")
        with col4:
            st.metric("Servings", recipe.servings)
        with col5:
            difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
            st.metric("Difficulty", f"{difficulty_emoji.get(recipe.difficulty_level, '⚪')} {recipe.difficulty_level.title()}")
    
    def _render_overview_tab(self, recipe: Recipe, user_pantry: Set[int]):
        """Render recipe overview tab"""
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if recipe.description:
                st.markdown("### Description")
                st.write(recipe.description)
            
            # Recipe availability summary
            recipe_ingredients = self._get_recipe_ingredients(recipe.id)
            if recipe_ingredients:
                required_ids = {ri.ingredient_id for ri in recipe_ingredients}
                available_count = len(required_ids & user_pantry)
                missing_count = len(required_ids - user_pantry)
                
                st.markdown("### 🥫 Pantry Status")
                
                if missing_count == 0:
                    st.success(f"✅ Perfect! You have all {len(required_ids)} ingredients needed.")
                elif available_count > 0:
                    st.warning(f"⚠️ You have {available_count}/{len(required_ids)} ingredients. Missing {missing_count} items.")
                    
                    # Show missing ingredients
                    missing_ingredients = []
                    for ri in recipe_ingredients:
                        if ri.ingredient_id not in user_pantry:
                            ingredient = self.ingredient_service.get_ingredient(ri.ingredient_id)
                            if ingredient:
                                missing_ingredients.append(ingredient.name)
                    
                    if missing_ingredients:
                        st.markdown("**Missing ingredients:**")
                        for ing_name in missing_ingredients[:5]:  # Show first 5
                            st.write(f"• {ing_name}")
                        if len(missing_ingredients) > 5:
                            st.write(f"• ... and {len(missing_ingredients) - 5} more")
                else:
                    st.error(f"❌ You need to get {len(required_ids)} ingredients to make this recipe.")
        
        with col2:
            # Recipe info card
            st.markdown("### 📋 Recipe Info")
            
            if recipe.cuisine_type:
                st.write(f"**Cuisine:** {recipe.cuisine_type}")
            
            if recipe.meal_category:
                st.write(f"**Category:** {recipe.meal_category.title()}")
            
            if recipe.dietary_tags:
                st.write(f"**Dietary:** {', '.join(recipe.dietary_tags)}")
            
            if recipe.rating and recipe.rating > 0:
                stars = "⭐" * int(recipe.rating)
                st.write(f"**Rating:** {stars} ({recipe.rating:.1f}/5)")
                if recipe.rating_count > 0:
                    st.write(f"Based on {recipe.rating_count} reviews")
            
            # Quick actions
            st.markdown("### 🔗 Quick Actions")
            
            if st.button("🛒 Add Ingredients to Shopping List"):
                st.info("Shopping list feature coming soon!")
            
            if st.button("📱 Share Recipe"):
                self._show_share_options(recipe)
            
            if st.button("📊 Nutritional Analysis"):
                st.info("Detailed nutrition analysis coming soon!")
    
    def _render_ingredients_tab(self, recipe: Recipe, user_pantry: Set[int]):
        """Render ingredients tab with detailed breakdown"""
        recipe_ingredients = self._get_recipe_ingredients(recipe.id)
        
        if not recipe_ingredients:
            st.warning("No ingredients found for this recipe.")
            return
        
        st.markdown("### 🥕 Ingredient List")
        
        # Group ingredients by category for better organization
        ingredients_by_category = {}
        uncategorized_ingredients = []
        
        for ri in recipe_ingredients:
            ingredient = self.ingredient_service.get_ingredient(ri.ingredient_id)
            if ingredient:
                category = ingredient.category or "Other"
                if category not in ingredients_by_category:
                    ingredients_by_category[category] = []
                ingredients_by_category[category].append((ri, ingredient))
        
        # Display ingredients by category
        for category in sorted(ingredients_by_category.keys()):
            if len(ingredients_by_category) > 1:  # Only show category headers if multiple categories
                st.markdown(f"#### {category.title()}")
            
            for ri, ingredient in ingredients_by_category[category]:
                # Format display text
                display_text = f"{ri.quantity:g} {ri.unit} {ingredient.name}"
                if ri.preparation_note:
                    display_text += f", {ri.preparation_note}"
                
                # Show availability status
                if ingredient.id in user_pantry:
                    st.markdown(f'<div class="ingredient-available">✅ {display_text}</div>', 
                              unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="ingredient-missing">❌ {display_text}</div>', 
                              unsafe_allow_html=True)
        
        # Ingredient substitutions
        st.markdown("### 🔄 Possible Substitutions")
        
        substitution_found = False
        for ri, ingredient in [(ri, self.ingredient_service.get_ingredient(ri.ingredient_id)) 
                              for ri in recipe_ingredients]:
            if ingredient and ingredient.common_substitutes:
                substitution_found = True
                st.markdown(f"**{ingredient.name}:**")
                for substitute in ingredient.common_substitutes[:3]:  # Show top 3 substitutes
                    st.write(f"• {substitute}")
        
        if not substitution_found:
            st.info("No common substitutions available for ingredients in this recipe.")
    
    def _render_instructions_tab(self, recipe: Recipe):
        """Render cooking instructions tab"""
        if not recipe.instructions:
            st.warning("No cooking instructions available for this recipe.")
            return
        
        st.markdown("### 👨‍🍳 Cooking Instructions")
        
        # Parse and format instructions
        instructions = recipe.instructions.strip()
        
        # Check if instructions are already numbered
        lines = instructions.split('\n')
        formatted_instructions = []
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # If line doesn't start with a number, add one
            if not line[0].isdigit():
                formatted_instructions.append(f"{i}. {line}")
            else:
                formatted_instructions.append(line)
        
        # Display instructions in expandable steps
        for i, instruction in enumerate(formatted_instructions):
            with st.expander(f"Step {i+1}", expanded=i==0):  # First step expanded
                st.write(instruction)
                
                # Add timer for time-sensitive steps
                if any(word in instruction.lower() for word in ['minutes', 'hour', 'cook', 'bake', 'simmer']):
                    if st.button(f"⏱️ Start Timer", key=f"timer_{i}"):
                        st.info("Timer feature coming soon!")
        
        # Cooking tips
        st.markdown("### 💡 Cooking Tips")
        st.info("""
        **Pro Tips:**
        - Read through all instructions before starting
        - Prep all ingredients first (mise en place)
        - Adjust cooking times based on your equipment
        - Taste and adjust seasonings as you go
        """)
    
    def _render_nutrition_tab(self, recipe: Recipe):
        """Render nutrition information tab"""
        st.markdown("### 📊 Nutrition Information")
        
        if recipe.nutritional_info:
            # Display nutrition data
            nutrition = recipe.nutritional_info
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if nutrition.calories:
                    st.metric("Calories", f"{nutrition.calories} kcal")
                if nutrition.protein_grams:
                    st.metric("Protein", f"{nutrition.protein_grams:.1f}g")
            
            with col2:
                if nutrition.carbs_grams:
                    st.metric("Carbs", f"{nutrition.carbs_grams:.1f}g")
                if nutrition.fat_grams:
                    st.metric("Fat", f"{nutrition.fat_grams:.1f}g")
            
            with col3:
                if nutrition.fiber_grams:
                    st.metric("Fiber", f"{nutrition.fiber_grams:.1f}g")
                if nutrition.sodium_milligrams:
                    st.metric("Sodium", f"{nutrition.sodium_milligrams:.0f}mg")
        
        else:
            st.info("Nutrition information not available for this recipe.")
            st.markdown("**Estimated nutritional content will be calculated based on ingredients.**")
        
        # Dietary analysis
        if recipe.dietary_tags:
            st.markdown("### 🌱 Dietary Information")
            
            dietary_info = {
                "vegetarian": "🥬 Contains no meat or fish",
                "vegan": "🌱 Contains no animal products",
                "gluten-free": "🌾 Safe for gluten sensitivity",
                "dairy-free": "🥛 Contains no dairy products",
                "low-carb": "⚡ Low in carbohydrates",
                "keto": "🥑 Ketogenic diet friendly",
                "high-protein": "💪 High in protein content"
            }
            
            for tag in recipe.dietary_tags:
                if tag in dietary_info:
                    st.success(dietary_info[tag])
                else:
                    st.info(f"✓ {tag.replace('-', ' ').title()}")
    
    def _render_tags_info_tab(self, recipe: Recipe):
        """Render tags and additional information tab"""
        st.markdown("### 🏷️ Tags & Categories")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if recipe.cuisine_type:
                st.markdown(f"**🌍 Cuisine:** {recipe.cuisine_type}")
            
            if recipe.meal_category:
                st.markdown(f"**🍽️ Meal Type:** {recipe.meal_category.title()}")
            
            st.markdown(f"**⏱️ Total Time:** {recipe.get_total_time_minutes()} minutes")
            st.markdown(f"**👥 Serves:** {recipe.servings} people")
            st.markdown(f"**📊 Difficulty:** {recipe.difficulty_level.title()}")
        
        with col2:
            if recipe.dietary_tags:
                st.markdown("**🌱 Dietary Tags:**")
                for tag in recipe.dietary_tags:
                    st.write(f"• {tag.replace('-', ' ').title()}")
        
        # Recipe metadata
        st.markdown("### 📝 Recipe Information")
        
        if recipe.source_url:
            st.markdown(f"**🔗 Original Source:** [View Original Recipe]({recipe.source_url})")
        
        if recipe.created_at:
            st.markdown(f"**📅 Added:** {recipe.created_at.strftime('%B %d, %Y')}")
        
        if recipe.updated_at and recipe.updated_at != recipe.created_at:
            st.markdown(f"**✏️ Last Updated:** {recipe.updated_at.strftime('%B %d, %Y')}")
    
    def _render_nutrition_edit_form(self, recipe: Recipe):
        """Render nutrition information editing form"""
        # Get current nutrition data
        current_nutrition = recipe.nutritional_info or NutritionData()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            calories = st.number_input(
                "Calories (per serving)",
                min_value=0,
                max_value=2000,
                value=current_nutrition.calories or 0,
                key="edit_calories"
            )
            
            protein = st.number_input(
                "Protein (grams)",
                min_value=0.0,
                max_value=100.0,
                value=float(current_nutrition.protein_grams or 0),
                step=0.1,
                key="edit_protein"
            )
            
            carbs = st.number_input(
                "Carbohydrates (grams)",
                min_value=0.0,
                max_value=200.0,
                value=float(current_nutrition.carbs_grams or 0),
                step=0.1,
                key="edit_carbs"
            )
        
        with col2:
            fat = st.number_input(
                "Fat (grams)",
                min_value=0.0,
                max_value=100.0,
                value=float(current_nutrition.fat_grams or 0),
                step=0.1,
                key="edit_fat"
            )
            
            fiber = st.number_input(
                "Fiber (grams)",
                min_value=0.0,
                max_value=50.0,
                value=float(current_nutrition.fiber_grams or 0),
                step=0.1,
                key="edit_fiber"
            )
            
            sodium = st.number_input(
                "Sodium (milligrams)",
                min_value=0.0,
                max_value=5000.0,
                value=float(current_nutrition.sodium_milligrams or 0),
                step=1.0,
                key="edit_sodium"
            )
    
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
    
    def _create_updated_recipe(self, original_recipe: Recipe, name: str, description: str,
                             source_url: str, prep_time: int, cook_time: int, servings: int,
                             difficulty: str, cuisine: str, meal_category: str,
                             dietary_tags: List[str], instructions: str) -> Recipe:
        """Create updated recipe object with form data"""
        updated_recipe = Recipe(
            id=original_recipe.id,
            name=name.strip(),
            description=description.strip(),
            instructions=instructions.strip(),
            prep_time_minutes=prep_time,
            cook_time_minutes=cook_time,
            servings=servings,
            difficulty_level=difficulty,
            cuisine_type=cuisine.strip() if cuisine else "",
            meal_category=meal_category.strip() if meal_category else "",
            dietary_tags=dietary_tags,
            source_url=source_url.strip() if source_url else None,
            created_by=original_recipe.created_by,
            created_at=original_recipe.created_at,
            updated_at=datetime.now(),
            is_public=original_recipe.is_public,
            rating=original_recipe.rating,
            rating_count=original_recipe.rating_count
        )
        
        # Handle nutrition data from form
        nutrition_data = NutritionData(
            calories=st.session_state.get('edit_calories', None) or None,
            protein_grams=st.session_state.get('edit_protein', None) or None,
            carbs_grams=st.session_state.get('edit_carbs', None) or None,
            fat_grams=st.session_state.get('edit_fat', None) or None,
            fiber_grams=st.session_state.get('edit_fiber', None) or None,
            sodium_milligrams=st.session_state.get('edit_sodium', None) or None
        )
        
        updated_recipe.nutritional_info = nutrition_data
        
        return updated_recipe
    
    def _save_recipe_changes(self, recipe: Recipe) -> bool:
        """Save recipe changes to database"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Prepare nutrition data
                nutrition_json = "{}"
                if recipe.nutritional_info:
                    nutrition_dict = {}
                    if recipe.nutritional_info.calories:
                        nutrition_dict['calories'] = recipe.nutritional_info.calories
                    if recipe.nutritional_info.protein_grams:
                        nutrition_dict['protein_grams'] = recipe.nutritional_info.protein_grams
                    if recipe.nutritional_info.carbs_grams:
                        nutrition_dict['carbs_grams'] = recipe.nutritional_info.carbs_grams
                    if recipe.nutritional_info.fat_grams:
                        nutrition_dict['fat_grams'] = recipe.nutritional_info.fat_grams
                    if recipe.nutritional_info.fiber_grams:
                        nutrition_dict['fiber_grams'] = recipe.nutritional_info.fiber_grams
                    if recipe.nutritional_info.sodium_milligrams:
                        nutrition_dict['sodium_milligrams'] = recipe.nutritional_info.sodium_milligrams
                    
                    if nutrition_dict:
                        nutrition_json = json.dumps(nutrition_dict)
                
                # Update recipe
                cursor.execute("""
                    UPDATE recipes SET
                        name = ?, description = ?, instructions = ?,
                        prep_time_minutes = ?, cook_time_minutes = ?, servings = ?,
                        difficulty_level = ?, cuisine_type = ?, meal_category = ?,
                        dietary_tags = ?, source_url = ?, nutritional_info = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    recipe.name, recipe.description, recipe.instructions,
                    recipe.prep_time_minutes, recipe.cook_time_minutes, recipe.servings,
                    recipe.difficulty_level, recipe.cuisine_type, recipe.meal_category,
                    ','.join(recipe.dietary_tags), recipe.source_url, nutrition_json,
                    recipe.id
                ))
                
                conn.commit()
                logger.info(f"Updated recipe {recipe.id}: {recipe.name}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving recipe changes: {e}")
            return False
    
    def _add_to_favorites(self, recipe_id: int):
        """Add recipe to user's favorites (placeholder implementation)"""
        # This would integrate with user collections system (Task 12)
        st.session_state[f'favorite_{recipe_id}'] = True
        logger.info(f"Added recipe {recipe_id} to favorites")
    
    def _show_share_options(self, recipe: Recipe):
        """Show recipe sharing options"""
        st.info("🔗 Share this recipe:")
        st.code(f"Recipe: {recipe.name}\nFrom: Pans Cookbook\nTotal time: {recipe.get_total_time_minutes()} minutes")
    
    def _confirm_delete_recipe(self, recipe_id: int) -> bool:
        """Confirm and delete recipe (placeholder implementation)"""
        if st.checkbox("I understand this action cannot be undone"):
            try:
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
                    conn.commit()
                    logger.info(f"Deleted recipe {recipe_id}")
                    return True
            except Exception as e:
                logger.error(f"Error deleting recipe: {e}")
                st.error(f"Failed to delete recipe: {e}")
        return False
    
    def _inject_custom_css(self):
        """Inject custom CSS styling for recipe details"""
        st.markdown("""
        <style>
            .ingredient-available {
                color: #2E7D32;
                font-weight: bold;
                background-color: #E8F5E9;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #A5D6A7;
                margin: 4px 0;
                display: block;
            }
            .ingredient-missing {
                color: #C62828;
                background-color: #FFEBEE;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #EF9A9A;
                margin: 4px 0;
                display: block;
            }
            .recipe-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 2rem;
                border-radius: 12px;
                margin-bottom: 2rem;
            }
            .metric-card {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 1rem;
                text-align: center;
            }
            .nutrition-card {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 8px;
                padding: 1rem;
                margin: 0.5rem 0;
            }
            .instruction-step {
                background-color: #f1f3f4;
                border-left: 4px solid #1976D2;
                padding: 1rem;
                margin: 1rem 0;
                border-radius: 0 8px 8px 0;
            }
        </style>
        """, unsafe_allow_html=True)


def create_recipe_details_interface(database_service: Optional[DatabaseService] = None,
                                  ingredient_service: Optional[IngredientService] = None) -> RecipeDetailsInterface:
    """Factory function to create recipe details interface"""
    return RecipeDetailsInterface(database_service, ingredient_service)