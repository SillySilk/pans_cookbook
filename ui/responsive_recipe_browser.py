"""
Responsive recipe browser component for Pans Cookbook application.

Provides mobile-optimized recipe browsing with grid layouts, card views,
and touch-friendly interactions for all device sizes.
"""

import streamlit as st
from typing import List, Optional, Dict, Any
from datetime import datetime

from models import Recipe, Ingredient
from services import DatabaseService, SearchService
from utils import get_logger
from .responsive_design import ResponsiveDesign, MobileOptimizations

logger = get_logger(__name__)


class ResponsiveRecipeBrowser:
    """
    Responsive recipe browser with mobile-first design.
    
    Adapts layout and interaction patterns based on device capabilities
    and provides optimal viewing experience across all screen sizes.
    """
    
    def __init__(self, database_service: Optional[DatabaseService] = None,
                 search_service: Optional[SearchService] = None):
        self.db = database_service
        self.search_service = search_service
        self.responsive = ResponsiveDesign()
        
        # View modes
        self.VIEW_MODES = {
            'grid': '🔲 Grid View',
            'list': '📋 List View', 
            'card': '🃏 Card View'
        }
    
    def render_recipe_browser(self, recipes: List[Recipe], user_id: Optional[int] = None,
                             mobile_mode: bool = False):
        """Render responsive recipe browser"""
        if not recipes:
            self._render_empty_state()
            return
        
        # Browser controls
        self._render_browser_controls(len(recipes), mobile_mode)
        
        # Recipe display
        if mobile_mode:
            self._render_mobile_recipe_list(recipes, user_id)
        else:
            view_mode = st.session_state.get('recipe_view_mode', 'grid')
            
            if view_mode == 'grid':
                self._render_grid_view(recipes, user_id)
            elif view_mode == 'list':
                self._render_list_view(recipes, user_id)
            else:  # card view
                self._render_card_view(recipes, user_id)
    
    def _render_browser_controls(self, recipe_count: int, mobile_mode: bool):
        """Render browser controls (view mode, sort, pagination)"""
        if mobile_mode:
            # Mobile controls - simplified
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"**{recipe_count} recipes found**")
            with col2:
                sort_by = st.selectbox(
                    "Sort",
                    ["Relevance", "Newest", "Rating", "Time"],
                    key="mobile_sort"
                )
        else:
            # Desktop controls - full featured
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                metrics = [
                    {"label": "Recipes", "value": str(recipe_count)}
                ]
                self.responsive.render_responsive_metrics(metrics, mobile_stack=False)
            
            with col2:
                view_mode = st.selectbox(
                    "View Mode",
                    list(self.VIEW_MODES.keys()),
                    format_func=lambda x: self.VIEW_MODES[x],
                    key="recipe_view_mode"
                )
            
            with col3:
                sort_by = st.selectbox(
                    "Sort By",
                    ["Relevance", "Title A-Z", "Newest First", "Rating", "Cook Time"],
                    key="desktop_sort"
                )
            
            with col4:
                per_page = st.selectbox(
                    "Per Page",
                    [12, 24, 48, 96],
                    index=1,
                    key="recipes_per_page"
                )
    
    def _render_mobile_recipe_list(self, recipes: List[Recipe], user_id: Optional[int] = None):
        """Render mobile-optimized recipe list"""
        st.markdown('<div class="mobile-recipe-list">', unsafe_allow_html=True)
        
        for i, recipe in enumerate(recipes):
            action = MobileOptimizations.render_mobile_recipe_card(recipe)
            
            if action == "view":
                self._handle_recipe_view(recipe, user_id)
            elif action == "save":
                self._handle_recipe_save(recipe, user_id)
            elif action == "share":
                self._handle_recipe_share(recipe)
            
            # Add separator except for last item
            if i < len(recipes) - 1:
                st.markdown("---")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def _render_grid_view(self, recipes: List[Recipe], user_id: Optional[int] = None):
        """Render responsive grid view"""
        st.markdown('<div class="recipe-grid">', unsafe_allow_html=True)
        
        # Create responsive columns
        cols_per_row = self._get_columns_per_row()
        
        for i in range(0, len(recipes), cols_per_row):
            cols = st.columns(cols_per_row)
            
            for j, col in enumerate(cols):
                recipe_index = i + j
                if recipe_index < len(recipes):
                    with col:
                        self._render_recipe_grid_card(recipes[recipe_index], user_id)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def _render_list_view(self, recipes: List[Recipe], user_id: Optional[int] = None):
        """Render responsive list view"""
        for recipe in recipes:
            with st.container():
                self._render_recipe_list_item(recipe, user_id)
                st.markdown("---")
    
    def _render_card_view(self, recipes: List[Recipe], user_id: Optional[int] = None):
        """Render responsive card view"""
        for recipe in recipes:
            with st.container():
                self._render_recipe_detailed_card(recipe, user_id)
                st.markdown("---")
    
    def _render_recipe_grid_card(self, recipe: Recipe, user_id: Optional[int] = None):
        """Render recipe card for grid view"""
        st.markdown('<div class="recipe-card">', unsafe_allow_html=True)
        
        # Recipe image placeholder or thumbnail
        st.markdown("""
        <div style="height: 150px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                    border-radius: 8px; margin-bottom: 0.5rem; display: flex; align-items: center; 
                    justify-content: center; font-size: 2rem;">
            🍽️
        </div>
        """, unsafe_allow_html=True)
        
        # Title (truncated)
        title = recipe.title if len(recipe.title) <= 40 else recipe.title[:40] + "..."
        st.markdown(f"**{title}**")
        
        # Quick stats
        stats = []
        if hasattr(recipe, 'prep_time_minutes') and hasattr(recipe, 'cook_time_minutes'):
            total_time = recipe.prep_time_minutes + recipe.cook_time_minutes
            stats.append(f"⏱️ {total_time}m")
        
        if hasattr(recipe, 'servings'):
            stats.append(f"👥 {recipe.servings}")
        
        if hasattr(recipe, 'difficulty_level'):
            difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(recipe.difficulty_level, "⚪")
            stats.append(f"{difficulty_emoji} {recipe.difficulty_level.title()}")
        
        if stats:
            st.caption(" • ".join(stats))
        
        # Dietary tags
        if hasattr(recipe, 'dietary_tags') and recipe.dietary_tags:
            tags_html = " ".join([
                f'<span class="dietary-tag">{tag}</span>'
                for tag in recipe.dietary_tags[:2]  # Show max 2 tags
            ])
            st.markdown(tags_html, unsafe_allow_html=True)
        
        # Action button
        if st.button("View Recipe", key=f"grid_view_{recipe.id}", use_container_width=True):
            self._handle_recipe_view(recipe, user_id)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def _render_recipe_list_item(self, recipe: Recipe, user_id: Optional[int] = None):
        """Render recipe item for list view"""
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.markdown(f"### {recipe.title}")
            if hasattr(recipe, 'description') and recipe.description:
                desc = recipe.description[:100] + "..." if len(recipe.description) > 100 else recipe.description
                st.caption(desc)
        
        with col2:
            # Recipe stats
            stats = []
            if hasattr(recipe, 'prep_time_minutes') and hasattr(recipe, 'cook_time_minutes'):
                total_time = recipe.prep_time_minutes + recipe.cook_time_minutes
                stats.append(f"⏱️ {total_time} min")
            
            if hasattr(recipe, 'servings'):
                stats.append(f"👥 {recipe.servings} servings")
            
            if hasattr(recipe, 'cuisine_type') and recipe.cuisine_type:
                stats.append(f"🌍 {recipe.cuisine_type}")
            
            for stat in stats:
                st.caption(stat)
        
        with col3:
            if st.button("View", key=f"list_view_{recipe.id}"):
                self._handle_recipe_view(recipe, user_id)
            
            if st.button("❤️", key=f"list_save_{recipe.id}", help="Save to favorites"):
                self._handle_recipe_save(recipe, user_id)
    
    def _render_recipe_detailed_card(self, recipe: Recipe, user_id: Optional[int] = None):
        """Render detailed recipe card"""
        st.markdown('<div class="recipe-detailed-card">', unsafe_allow_html=True)
        
        # Header with title and rating
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"## {recipe.title}")
        with col2:
            if hasattr(recipe, 'rating') and recipe.rating:
                st.metric("Rating", f"{recipe.rating:.1f}⭐")
        
        # Description
        if hasattr(recipe, 'description') and recipe.description:
            st.markdown(recipe.description)
        
        # Recipe metadata in responsive grid
        metadata = []
        if hasattr(recipe, 'prep_time_minutes'):
            metadata.append({"label": "Prep Time", "value": f"{recipe.prep_time_minutes}m"})
        if hasattr(recipe, 'cook_time_minutes'):
            metadata.append({"label": "Cook Time", "value": f"{recipe.cook_time_minutes}m"})
        if hasattr(recipe, 'servings'):
            metadata.append({"label": "Serves", "value": str(recipe.servings)})
        if hasattr(recipe, 'difficulty_level'):
            metadata.append({"label": "Difficulty", "value": recipe.difficulty_level.title()})
        
        if metadata:
            self.responsive.render_responsive_metrics(metadata)
        
        # Tags and categories
        if hasattr(recipe, 'dietary_tags') and recipe.dietary_tags:
            st.markdown("**Dietary Tags:**")
            tags_html = " ".join([
                f'<span class="dietary-tag">{tag}</span>'
                for tag in recipe.dietary_tags
            ])
            st.markdown(tags_html, unsafe_allow_html=True)
        
        # Action buttons
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("👁️ View Full", key=f"card_view_{recipe.id}"):
                self._handle_recipe_view(recipe, user_id)
        with col2:
            if st.button("❤️ Save", key=f"card_save_{recipe.id}"):
                self._handle_recipe_save(recipe, user_id)
        with col3:
            if st.button("📤 Share", key=f"card_share_{recipe.id}"):
                self._handle_recipe_share(recipe)
        with col4:
            if st.button("🍳 Cook", key=f"card_cook_{recipe.id}"):
                self._handle_start_cooking(recipe, user_id)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def _render_empty_state(self):
        """Render empty state when no recipes found"""
        st.markdown("""
        <div style="text-align: center; padding: 3rem 1rem; color: #666;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">🍽️</div>
            <h3>No recipes found</h3>
            <p>Try adjusting your search criteria or browse our collection.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Suggestions
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔍 Clear Filters", use_container_width=True):
                st.experimental_rerun()
        with col2:
            if st.button("🎲 Random Recipe", use_container_width=True):
                st.info("Random recipe feature coming soon!")
        with col3:
            if st.button("➕ Add Recipe", use_container_width=True):
                st.info("Recipe creation feature coming soon!")
    
    def _get_columns_per_row(self) -> int:
        """Get number of columns per row based on screen size"""
        # This would ideally use viewport detection, but Streamlit has limitations
        # For now, we'll use a reasonable default that works well
        return 3  # Good balance for most screen sizes
    
    def _handle_recipe_view(self, recipe: Recipe, user_id: Optional[int] = None):
        """Handle recipe view action"""
        # Store recipe in session state for detailed view
        st.session_state['selected_recipe'] = recipe
        st.success(f"Opening {recipe.title}...")
        # In a real app, this would navigate to a detailed recipe page
    
    def _handle_recipe_save(self, recipe: Recipe, user_id: Optional[int] = None):
        """Handle recipe save/favorite action"""
        if user_id and self.db:
            # Logic to save to user's favorites would go here
            st.success(f"Saved {recipe.title} to favorites!")
        else:
            st.info("Please log in to save recipes to favorites.")
    
    def _handle_recipe_share(self, recipe: Recipe):
        """Handle recipe share action"""
        # Generate shareable link or copy to clipboard
        share_url = f"https://panscookbook.app/recipe/{recipe.id}"
        st.success(f"Share link copied! {share_url}")
    
    def _handle_start_cooking(self, recipe: Recipe, user_id: Optional[int] = None):
        """Handle start cooking mode"""
        st.info(f"Cooking mode for {recipe.title} - feature coming soon!")


# Factory function
def create_responsive_recipe_browser(database_service: Optional[DatabaseService] = None,
                                   search_service: Optional[SearchService] = None) -> ResponsiveRecipeBrowser:
    """Factory function to create responsive recipe browser"""
    return ResponsiveRecipeBrowser(database_service, search_service)