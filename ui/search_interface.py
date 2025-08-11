"""
Advanced search interface for Pans Cookbook application.

Provides comprehensive search UI with time filtering, cuisine selection,
dietary restrictions, and other advanced filtering options.
Built on top of the SearchService with intuitive user controls.
"""

import streamlit as st
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from models import Recipe
from services import SearchService, SearchFilters, TimeRange, SortOrder, get_search_service, DatabaseService
from utils import get_logger
from .responsive_design import ResponsiveDesign, MobileOptimizations

logger = get_logger(__name__)


class SearchInterface:
    """
    Advanced search interface with comprehensive filtering options.
    
    Provides an intuitive UI for recipe search with time ranges, cuisine filters,
    dietary restrictions, and ingredient-based searching.
    """
    
    def __init__(self, search_service: Optional[SearchService] = None,
                 database_service: Optional[DatabaseService] = None):
        self.search_service = search_service or get_search_service(database_service)
        self.responsive = ResponsiveDesign()
        
        # Initialize custom CSS
        self._inject_search_css()
        
        # Session state keys
        self.SEARCH_RESULTS_KEY = "search_results"
        self.LAST_SEARCH_KEY = "last_search_params"
        self.FILTER_STATE_KEY = "search_filters_state"
    
    def render_search_interface(self, user_id: Optional[int] = None, mobile_mode: bool = False):
        """Render the complete search interface"""
        st.subheader("🔍 Advanced Recipe Search")
        
        # Get filter suggestions for dropdowns
        filter_options = self.search_service.get_filter_suggestions(user_id)
        
        # Mobile-optimized search bar
        if mobile_mode:
            search_query = MobileOptimizations.render_mobile_search_bar()
            mobile_filters = MobileOptimizations.render_mobile_filter_drawer()
        
        # Create search form
        with self.responsive.create_mobile_friendly_form("recipe_search_form"):
            # Text search
            search_query = self._render_text_search()
            
            # Advanced filters in expandable sections
            time_filters = self._render_time_filters()
            category_filters = self._render_category_filters(filter_options)
            dietary_filters = self._render_dietary_filters(filter_options)
            ingredient_filters = self._render_ingredient_filters()
            
            # Search button and options
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                search_clicked = st.form_submit_button("🔍 Search Recipes", type="primary")
            with col2:
                sort_option = st.selectbox("Sort by", options=[
                    ("relevance", "Relevance"),
                    ("title_asc", "Title A-Z"),
                    ("prep_time_asc", "Prep Time ↑"),
                    ("total_time_asc", "Total Time ↑"),
                    ("created_desc", "Newest First")
                ], format_func=lambda x: x[1], key="sort_option")
            with col3:
                results_per_page = st.selectbox("Results", [10, 25, 50, 100], 
                                              index=1, key="results_per_page")
        
        # Execute search when form submitted
        if search_clicked:
            filters = self._build_search_filters(
                search_query, time_filters, category_filters, 
                dietary_filters, ingredient_filters
            )
            
            sort_order = SortOrder(sort_option[0])
            results = self.search_service.search_recipes(
                filters, sort_by=sort_order, limit=results_per_page, user_id=user_id
            )
            
            # Store results in session state
            st.session_state[self.SEARCH_RESULTS_KEY] = results
            st.session_state[self.LAST_SEARCH_KEY] = {
                'filters': filters,
                'sort_order': sort_order,
                'timestamp': datetime.now()
            }
        
        # Display search results
        if self.SEARCH_RESULTS_KEY in st.session_state:
            self._render_search_results(st.session_state[self.SEARCH_RESULTS_KEY])
        else:
            self._render_search_tips()
    
    def _render_text_search(self) -> str:
        """Render text search input"""
        st.markdown("#### 📝 Search Query")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            query = st.text_input(
                "Search recipes, ingredients, or cooking methods",
                placeholder="e.g., chocolate chip cookies, pasta with garlic, 30-minute meals",
                key="search_query",
                help="Search across recipe titles, descriptions, ingredients, and instructions"
            )
        
        with col2:
            search_scope = st.multiselect(
                "Search in:",
                options=["Titles", "Ingredients", "Instructions"],
                default=["Titles", "Ingredients"],
                key="search_scope"
            )
        
        return query
    
    def _render_time_filters(self) -> Dict[str, Any]:
        """Render time-based filters"""
        with st.expander("⏱️ Time Filters", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Quick Time Presets:**")
                time_preset = st.selectbox(
                    "Choose preset:",
                    options=["", "quick", "moderate", "long", "weeknight", "weekend"],
                    format_func=lambda x: {
                        "": "Custom range",
                        "quick": "Quick (≤30 min)",
                        "moderate": "Moderate (30-60 min)", 
                        "long": "Long cooking (≥60 min)",
                        "weeknight": "Weeknight (≤45 min)",
                        "weekend": "Weekend project (≥60 min)"
                    }.get(x, x),
                    key="time_preset"
                )
            
            with col2:
                st.markdown("**Custom Time Ranges:**")
                
                # Prep time range
                prep_min, prep_max = st.slider(
                    "Prep time (minutes)",
                    min_value=0, max_value=120,
                    value=(0, 60),
                    key="prep_time_range"
                )
                
                # Total time range  
                total_min, total_max = st.slider(
                    "Total time (minutes)",
                    min_value=0, max_value=300,
                    value=(0, 120),
                    key="total_time_range"
                )
        
        return {
            'preset': time_preset,
            'prep_range': (prep_min, prep_max) if prep_min > 0 or prep_max < 60 else None,
            'total_range': (total_min, total_max) if total_min > 0 or total_max < 120 else None
        }
    
    def _render_category_filters(self, filter_options: Dict[str, List[str]]) -> Dict[str, Any]:
        """Render category-based filters"""
        with st.expander("🍽️ Categories & Cuisine", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                # Cuisine types
                cuisines = st.multiselect(
                    "Cuisine Types",
                    options=filter_options.get('cuisines', []),
                    key="selected_cuisines",
                    help="Select one or more cuisine types"
                )
                
                # Difficulty levels
                difficulties = st.multiselect(
                    "Difficulty Levels", 
                    options=filter_options.get('difficulties', []),
                    key="selected_difficulties"
                )
            
            with col2:
                # Meal categories
                categories = st.multiselect(
                    "Meal Categories",
                    options=filter_options.get('categories', []),
                    key="selected_categories"
                )
                
                # Serving size range
                min_servings, max_servings = st.slider(
                    "Serving size",
                    min_value=1, max_value=12,
                    value=(1, 8),
                    key="serving_range"
                )
        
        return {
            'cuisines': cuisines if cuisines else None,
            'categories': categories if categories else None,
            'difficulties': difficulties if difficulties else None,
            'servings': (min_servings, max_servings) if min_servings > 1 or max_servings < 8 else None
        }
    
    def _render_dietary_filters(self, filter_options: Dict[str, List[str]]) -> Dict[str, Any]:
        """Render dietary restriction filters"""
        with st.expander("🌱 Dietary Restrictions", expanded=False):
            dietary_tags = st.multiselect(
                "Dietary Requirements",
                options=filter_options.get('dietary_tags', []),
                key="selected_dietary_tags",
                help="Recipes matching your dietary needs. Vegan recipes will appear in vegetarian searches."
            )
            
            if dietary_tags:
                inclusive_logic = st.checkbox(
                    "Use inclusive logic (e.g., show vegan recipes when searching vegetarian)",
                    value=True,
                    key="inclusive_dietary",
                    help="When enabled, more restrictive diets are included (vegan shows up in vegetarian)"
                )
            else:
                inclusive_logic = True
        
        return {
            'dietary_tags': dietary_tags if dietary_tags else None,
            'inclusive': inclusive_logic
        }
    
    def _render_ingredient_filters(self) -> Dict[str, Any]:
        """Render ingredient-based filters"""
        with st.expander("🥕 Ingredient Filters", expanded=False):
            st.markdown("**Filter by ingredients you have or want to avoid:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Required ingredients (must have ALL)
                required_ingredients = st.text_area(
                    "Must include ingredients:",
                    placeholder="chicken, garlic, tomatoes\n(one per line or comma-separated)",
                    key="required_ingredients",
                    help="Recipes must contain ALL of these ingredients"
                )
                
                # Optional ingredients (must have ANY)
                optional_ingredients = st.text_area(
                    "Should include (any of):",
                    placeholder="herbs, spices, cheese",
                    key="optional_ingredients", 
                    help="Recipes should contain at least ONE of these ingredients"
                )
            
            with col2:
                # Excluded ingredients (must have NONE)
                excluded_ingredients = st.text_area(
                    "Must NOT include:",
                    placeholder="nuts, shellfish, dairy",
                    key="excluded_ingredients",
                    help="Recipes must NOT contain any of these ingredients"
                )
                
                # Common allergens quick selection
                st.markdown("**Quick allergen filters:**")
                allergen_excludes = st.multiselect(
                    "Exclude common allergens:",
                    options=["nuts", "dairy", "eggs", "gluten", "shellfish", "soy"],
                    key="allergen_excludes"
                )
        
        def parse_ingredients(text: str) -> List[str]:
            """Parse ingredient text into list"""
            if not text.strip():
                return []
            # Split by newlines or commas, clean up
            ingredients = []
            for line in text.strip().split('\n'):
                ingredients.extend([ing.strip() for ing in line.split(',') if ing.strip()])
            return ingredients
        
        required = parse_ingredients(required_ingredients)
        optional = parse_ingredients(optional_ingredients) 
        excluded = parse_ingredients(excluded_ingredients) + allergen_excludes
        
        return {
            'required': required if required else None,
            'optional': optional if optional else None,
            'excluded': excluded if excluded else None
        }
    
    def _build_search_filters(self, query: str, time_filters: Dict, category_filters: Dict,
                            dietary_filters: Dict, ingredient_filters: Dict) -> SearchFilters:
        """Build SearchFilters object from UI inputs"""
        
        # Handle time ranges
        prep_range = None
        total_range = None
        
        if time_filters['preset']:
            preset_range = self.search_service.get_time_preset(time_filters['preset'])
            if preset_range:
                total_range = preset_range
        
        if time_filters['prep_range']:
            min_prep, max_prep = time_filters['prep_range']
            prep_range = TimeRange(min_prep if min_prep > 0 else None, 
                                 max_prep if max_prep < 60 else None)
        
        if time_filters['total_range'] and not total_range:
            min_total, max_total = time_filters['total_range']
            total_range = TimeRange(min_total if min_total > 0 else None,
                                  max_total if max_total < 120 else None)
        
        # Handle serving size
        min_servings = None
        max_servings = None
        if category_filters['servings']:
            min_servings, max_servings = category_filters['servings']
            if min_servings <= 1:
                min_servings = None
            if max_servings >= 8:
                max_servings = None
        
        return SearchFilters(
            query=query.strip() if query.strip() else None,
            prep_time_range=prep_range,
            total_time_range=total_range,
            cuisine_types=category_filters['cuisines'],
            meal_categories=category_filters['categories'],
            difficulty_levels=category_filters['difficulties'],
            dietary_tags=dietary_filters['dietary_tags'],
            include_dietary_supersets=dietary_filters['inclusive'],
            required_ingredients=ingredient_filters['required'],
            optional_ingredients=ingredient_filters['optional'],
            excluded_ingredients=ingredient_filters['excluded'],
            min_servings=min_servings,
            max_servings=max_servings
        )
    
    def _render_search_results(self, results):
        """Render search results"""
        st.markdown("---")
        st.subheader("🍽️ Search Results")
        
        if not results.has_results:
            st.warning("No recipes found matching your search criteria.")
            st.info("💡 **Try adjusting your filters:**\n"
                   "- Remove some dietary restrictions\n"
                   "- Expand time ranges\n" 
                   "- Use broader ingredient terms\n"
                   "- Try different cuisine types")
            return
        
        # Results summary
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.success(f"Found {results.filtered_count} recipes matching your criteria")
        with col2:
            st.metric("Search Time", f"{results.execution_time_ms:.1f}ms")
        with col3:
            if results.total_count > results.filtered_count:
                st.info(f"Filtered from {results.total_count} total recipes")
        
        # Display results
        for i, result in enumerate(results.results, 1):
            recipe = result.recipe
            
            with st.container():
                # Recipe header
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**{i}. {recipe.title}**")
                    if recipe.description:
                        st.caption(recipe.description[:120] + "..." if len(recipe.description) > 120 else recipe.description)
                
                with col2:
                    if hasattr(recipe, 'prep_time_minutes') and hasattr(recipe, 'cook_time_minutes'):
                        total_time = recipe.prep_time_minutes + recipe.cook_time_minutes
                        st.metric("Total Time", f"{total_time}m")
                
                with col3:
                    st.metric("Serves", recipe.servings if hasattr(recipe, 'servings') else "N/A")
                
                # Recipe details
                details_col1, details_col2 = st.columns([2, 1])
                
                with details_col1:
                    # Tags and categories
                    tags = []
                    if hasattr(recipe, 'cuisine_type') and recipe.cuisine_type:
                        tags.append(f"🌍 {recipe.cuisine_type}")
                    if hasattr(recipe, 'meal_category') and recipe.meal_category:
                        tags.append(f"🍽️ {recipe.meal_category}")
                    if hasattr(recipe, 'difficulty_level') and recipe.difficulty_level:
                        tags.append(f"⚡ {recipe.difficulty_level}")
                    
                    if tags:
                        st.write(" • ".join(tags))
                    
                    # Dietary tags
                    if hasattr(recipe, 'dietary_tags') and recipe.dietary_tags:
                        dietary_badge_html = " ".join([
                            f'<span style="background-color: #E8F5E9; color: #2E7D32; padding: 2px 6px; border-radius: 4px; font-size: 0.8em;">{tag}</span>'
                            for tag in recipe.dietary_tags
                        ])
                        st.markdown(dietary_badge_html, unsafe_allow_html=True)
                
                with details_col2:
                    # Relevance score for text searches
                    if result.relevance_score > 0:
                        st.metric("Relevance", f"{result.relevance_score:.1f}")
                    
                    # Matched terms
                    if result.matched_terms:
                        st.caption(f"Matches: {', '.join(result.matched_terms[:3])}")
                
                # Action buttons
                button_col1, button_col2, button_col3 = st.columns([1, 1, 2])
                with button_col1:
                    if st.button("👁️ View", key=f"view_{recipe.id}_{i}"):
                        st.info("Recipe details view would open here")
                
                with button_col2:
                    if st.button("❤️ Save", key=f"save_{recipe.id}_{i}"):
                        st.success("Recipe saved to favorites!")
                
                st.markdown("---")
    
    def _render_search_tips(self):
        """Render search tips when no search has been performed"""
        st.info("🔍 **Search Tips:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **Text Search Examples:**
            - `chocolate chip cookies` - Find specific recipes
            - `quick dinner` - Broad category search  
            - `garlic pasta` - Ingredient + dish type
            - `30 minute meals` - Time-based search
            """)
        
        with col2:
            st.markdown("""
            **Filter Combinations:**
            - Set time limits for busy weeknights
            - Choose cuisines you're in the mood for
            - Filter by dietary restrictions
            - Exclude ingredients you don't have
            """)
        
        st.markdown("---")
        st.markdown("**💡 Start by entering a search term above or use the filters to browse recipes!**")
    
    def _inject_search_css(self):
        """Inject custom CSS for search interface"""
        st.markdown("""
        <style>
            .search-container {
                background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%);
                border-radius: 8px;
                padding: 1rem;
                margin: 1rem 0;
            }
            
            .search-result-item {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 1rem;
                margin: 0.5rem 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
            
            .search-result-item:hover {
                border-color: #2196F3;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            
            .dietary-tag {
                background-color: #E8F5E9;
                color: #2E7D32;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 0.8em;
                margin: 2px;
                display: inline-block;
            }
        </style>
        """, unsafe_allow_html=True)


# Factory function
def create_search_interface(search_service: Optional[SearchService] = None,
                           database_service: Optional[DatabaseService] = None) -> SearchInterface:
    """Factory function to create search interface"""
    return SearchInterface(search_service, database_service)