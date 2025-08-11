"""
Pantry management UI for Pans Cookbook application.

Main user interface for managing ingredient inventory and finding recipes
that can be made with available ingredients. Core user experience.
"""

import streamlit as st
from typing import List, Optional, Dict, Any, Set
from datetime import datetime

from models import Recipe, Ingredient
from services import DatabaseService, get_pantry_service
from services.pantry_service import PantryService, PantryItem, RecipeMatch
from ui.responsive_design import ResponsiveDesign, MobileOptimizations
from utils import get_logger

logger = get_logger(__name__)


class PantryManagerInterface:
    """
    Main pantry management interface - the heart of the application.
    
    Provides:
    - Pantry inventory management (what ingredients you have)
    - Recipe matching (what you can make)
    - Shopping list generation
    - Recipe suggestions
    """
    
    def __init__(self, database_service: Optional[DatabaseService] = None):
        self.db = database_service or DatabaseService()
        self.pantry_service = get_pantry_service(database_service)
        self.responsive = ResponsiveDesign()
        
        # Session state keys
        self.PANTRY_STATE_KEY = "pantry_items"
        self.SELECTED_RECIPES_KEY = "selected_recipes"
        self.VIEW_MODE_KEY = "pantry_view_mode"
    
    def render_pantry_manager(self, user_id: int = 1, mobile_mode: bool = False):
        """Render the complete pantry management interface"""
        
        # Header with quick stats
        self._render_pantry_header(user_id)
        
        # Main tabs
        if mobile_mode:
            # Mobile: simplified single-column layout
            self._render_mobile_pantry_interface(user_id)
        else:
            # Desktop: full tabbed interface
            tab1, tab2, tab3, tab4 = st.tabs([
                "🥕 My Pantry", 
                "🍽️ What Can I Make?", 
                "🛒 Shopping List", 
                "💡 Suggestions"
            ])
            
            with tab1:
                self._render_pantry_management(user_id)
            
            with tab2:
                self._render_recipe_matching(user_id)
            
            with tab3:
                self._render_shopping_list(user_id)
            
            with tab4:
                self._render_recipe_suggestions(user_id)
    
    def _render_pantry_header(self, user_id: int):
        """Render pantry overview header with quick stats"""
        st.title("🍳 My Kitchen")
        
        # Get pantry stats
        pantry_items = self.pantry_service.get_user_pantry(user_id)
        available_count = len([item for item in pantry_items if item.is_available])
        total_count = len(pantry_items)
        
        # Get recipe match stats
        makeable_recipes = self.pantry_service.find_makeable_recipes(user_id, strict_mode=True)
        almost_ready = self.pantry_service.suggest_recipes_to_complete_pantry(user_id, max_missing=2)
        
        # Quick stats
        metrics = [
            {"label": "Ingredients Available", "value": str(available_count), "delta": f"of {total_count}"},
            {"label": "Recipes I Can Make", "value": str(len(makeable_recipes)), "delta": "Ready now"},
            {"label": "Almost Ready", "value": str(len(almost_ready)), "delta": "Need 1-2 items"}
        ]
        
        self.responsive.render_responsive_metrics(metrics, mobile_stack=False)
        
        # Quick actions
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("➕ Add Common Items", help="Add typical pantry ingredients"):
                added = self.pantry_service.add_common_ingredients_to_pantry(user_id)
                st.success(f"Added {added} common ingredients to your pantry!")
                st.experimental_rerun()
        
        with col2:
            if st.button("🔄 Refresh Pantry", help="Reload pantry data"):
                st.experimental_rerun()
        
        with col3:
            if st.button("📊 View All Recipes", help="Browse complete recipe library"):
                st.info("Recipe library view - feature coming soon!")
        
        with col4:
            if st.button("🎯 Quick Match", help="Find recipes you can make right now"):
                st.session_state["quick_match_mode"] = True
                st.experimental_rerun()
    
    def _render_mobile_pantry_interface(self, user_id: int):
        """Render mobile-optimized single-column pantry interface"""
        st.markdown("### Quick Actions")
        
        # Mobile action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 What Can I Make?", use_container_width=True):
                st.session_state["mobile_view"] = "recipes"
        with col2:
            if st.button("🥕 Manage Pantry", use_container_width=True):
                st.session_state["mobile_view"] = "pantry"
        
        # Show selected view
        mobile_view = st.session_state.get("mobile_view", "recipes")
        
        if mobile_view == "recipes":
            self._render_recipe_matching(user_id, mobile_mode=True)
        else:
            self._render_pantry_management(user_id, mobile_mode=True)
    
    def _render_pantry_management(self, user_id: int, mobile_mode: bool = False):
        """Render pantry inventory management interface with smart categorization"""
        st.markdown("### 🥕 My Pantry Inventory")
        st.caption("Manage your ingredients by category - only shows items you've added")
        
        # Get pantry organized by category
        pantry_categories = self.pantry_service.get_pantry_categories(user_id)
        
        if not pantry_categories:
            st.info("🏪 **Welcome to your pantry!** Let's get you set up.")
            
            # Pantry setup wizard
            self._render_pantry_setup_wizard(user_id)
            return
        
        # Pantry overview stats
        self._render_pantry_overview(pantry_categories)
        
        # Smart pantry management interface
        management_mode = st.selectbox(
            "Choose how to manage your pantry:",
            ["category_view", "smart_add", "quick_check", "bulk_edit"],
            format_func=lambda x: {
                "category_view": "📦 By Category (browse what I have)",
                "smart_add": "➕ Smart Add (add new ingredients)",  
                "quick_check": "⚡ Quick Check (mark available/unavailable)",
                "bulk_edit": "📝 Bulk Edit (manage many at once)"
            }.get(x, x),
            key="pantry_management_mode"
        )
        
        if management_mode == "category_view":
            self._render_category_view(user_id, pantry_categories, mobile_mode)
        elif management_mode == "smart_add":
            self._render_smart_add_interface(user_id)
        elif management_mode == "quick_check":
            self._render_quick_check_interface(user_id, pantry_categories)
        else:  # bulk_edit
            self._render_bulk_edit_interface(user_id, pantry_categories)
    
    def _render_pantry_setup_wizard(self, user_id: int):
        """Render pantry setup wizard for new users"""
        st.markdown("#### 🚀 Pantry Setup Wizard")
        
        # Step 1: Add common pantry staples by category
        st.markdown("**Step 1: Add your pantry staples**")
        st.caption("Select categories of ingredients you typically have:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            basic_seasonings = st.checkbox("🧂 Basic Seasonings", help="Salt, pepper, garlic powder, etc.")
            cooking_oils = st.checkbox("🫒 Cooking Oils & Fats", help="Olive oil, butter, vegetable oil")
            baking_basics = st.checkbox("🍞 Baking Basics", help="Flour, sugar, baking powder, vanilla")
            fresh_produce = st.checkbox("🥬 Fresh Produce", help="Common vegetables like onions, garlic")
        
        with col2:
            proteins = st.checkbox("🥩 Proteins", help="Chicken, beef, eggs")
            dairy_basics = st.checkbox("🥛 Dairy Basics", help="Milk, cheese, yogurt")
            pantry_staples = st.checkbox("🏪 Pantry Staples", help="Rice, pasta, canned goods")
            herbs_spices = st.checkbox("🌿 Herbs & Spices", help="Common cooking herbs and spices")
        
        if st.button("🎯 Set Up My Pantry", type="primary"):
            categories_to_add = []
            
            if basic_seasonings:
                categories_to_add.extend(['seasoning'])
            if cooking_oils:
                categories_to_add.extend(['oil'])
            if baking_basics:
                categories_to_add.extend(['grain', 'sweetener'])
            if fresh_produce:
                categories_to_add.extend(['vegetable'])
            if proteins:
                categories_to_add.extend(['protein'])
            if dairy_basics:
                categories_to_add.extend(['dairy'])
            if pantry_staples:
                categories_to_add.extend(['grain', 'pantry'])
            if herbs_spices:
                categories_to_add.extend(['spice'])
            
            if categories_to_add:
                added_count = self.pantry_service.add_common_ingredients_to_pantry(user_id, categories_to_add)
                st.success(f"🎉 Added {added_count} ingredients to your pantry!")
                st.experimental_rerun()
            else:
                st.warning("Please select at least one category to get started.")
        
        st.markdown("---")
        st.markdown("**Step 2: Or add specific ingredients**")
        self._render_add_ingredient_form(user_id, simplified=True)
    
    def _render_pantry_overview(self, pantry_categories: Dict):
        """Render pantry overview with quick stats"""
        total_items = sum(len(items) for items in pantry_categories.values())
        available_items = sum(len([item for item in items if item.is_available]) 
                            for items in pantry_categories.values())
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Ingredients", total_items)
        with col2:
            st.metric("Available Now", available_items)
        with col3:
            st.metric("Categories", len(pantry_categories))
        with col4:
            availability_pct = (available_items / total_items * 100) if total_items > 0 else 0
            st.metric("Availability", f"{availability_pct:.0f}%")
        
        # Low stock alerts
        low_stock_items = []
        for category, items in pantry_categories.items():
            for item in items:
                if item.is_available and item.quantity_estimate == "running low":
                    low_stock_items.append(item.ingredient_name)
        
        if low_stock_items:
            st.warning(f"⚠️ Running low on: {', '.join(low_stock_items[:3])}{'...' if len(low_stock_items) > 3 else ''}")
    
    def _render_category_view(self, user_id: int, pantry_categories: Dict, mobile_mode: bool):
        """Render traditional category-based view"""
        # Search/filter
        search_term = st.text_input("🔍 Search your pantry", key="pantry_search")
        
        # Category priority (show most useful first)
        category_priority = {
            'protein': 1, 'vegetable': 2, 'dairy': 3, 'oil': 4, 'grain': 5,
            'spice': 6, 'seasoning': 7, 'fruit': 8, 'sweetener': 9, 'other': 10
        }
        
        sorted_categories = sorted(pantry_categories.items(), 
                                 key=lambda x: category_priority.get(x[0], 10))
        
        for category, items in sorted_categories:
            if search_term:
                items = [item for item in items if search_term.lower() in item.ingredient_name.lower()]
                if not items:
                    continue
            
            # Category icons
            category_icons = {
                'protein': '🥩', 'vegetable': '🥕', 'fruit': '🍎', 'dairy': '🥛',
                'grain': '🌾', 'oil': '🫒', 'spice': '🌶️', 'seasoning': '🧂',
                'sweetener': '🍯', 'other': '📦'
            }
            icon = category_icons.get(category, '📦')
            
            available_count = len([i for i in items if i.is_available])
            
            with st.expander(f"{icon} {category.title()} ({available_count}/{len(items)} available)", 
                           expanded=False):
                
                # Quick actions for category
                cat_col1, cat_col2, cat_col3 = st.columns(3)
                with cat_col1:
                    if st.button(f"✅ Mark All Available", key=f"all_avail_{category}"):
                        self._bulk_update_category(user_id, category, items, True)
                        st.experimental_rerun()
                        
                with cat_col2:
                    if st.button(f"❌ Mark All Unavailable", key=f"all_unavail_{category}"):
                        self._bulk_update_category(user_id, category, items, False)
                        st.experimental_rerun()
                
                with cat_col3:
                    if st.button(f"➕ Add to {category.title()}", key=f"add_to_{category}"):
                        st.session_state[f"add_to_category"] = category
                
                # Show items in clean grid
                cols_per_row = 2 if mobile_mode else 3
                for i in range(0, len(items), cols_per_row):
                    cols = st.columns(cols_per_row)
                    
                    for j, col in enumerate(cols):
                        if i + j < len(items):
                            item = items[i + j]
                            with col:
                                self._render_pantry_item_card(user_id, item)
    
    def _render_smart_add_interface(self, user_id: int):
        """Render smart ingredient addition interface"""
        st.markdown("#### ➕ Smart Add Ingredients")
        st.caption("Quickly add ingredients with smart suggestions")
        
        # Smart ingredient search with autocomplete
        ingredient_search = st.text_input(
            "Start typing an ingredient name:",
            key="smart_ingredient_search",
            help="We'll show suggestions as you type"
        )
        
        if ingredient_search and len(ingredient_search) >= 2:
            # Search existing ingredients
            suggestions = self.db.search_ingredients(ingredient_search)
            
            if suggestions:
                st.markdown("**Found matching ingredients:**")
                
                # Show suggestions in a nice grid
                for i, suggestion in enumerate(suggestions[:6]):  # Limit to 6 suggestions
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{suggestion.name}** _{suggestion.category}_")
                    
                    with col2:
                        have_it = st.button("✅ Have It", key=f"have_{suggestion.id}")
                    
                    with col3:
                        need_it = st.button("🛒 Need It", key=f"need_{suggestion.id}")
                    
                    with col4:
                        quantity = st.selectbox(
                            "Amount", 
                            ["plenty", "just enough", "running low"],
                            key=f"qty_{suggestion.id}",
                            label_visibility="collapsed"
                        )
                    
                    if have_it:
                        self.pantry_service.update_pantry_item(user_id, suggestion.id, True, quantity)
                        st.success(f"Added '{suggestion.name}' as available!")
                        st.experimental_rerun()
                    
                    if need_it:
                        self.pantry_service.update_pantry_item(user_id, suggestion.id, False, None)
                        st.success(f"Added '{suggestion.name}' to shopping list!")
                        st.experimental_rerun()
            
            # Option to create new ingredient if not found
            st.markdown("---")
            with st.expander("🆕 Create New Ingredient", expanded=False):
                self._render_add_ingredient_form(user_id, prefilled_name=ingredient_search)
    
    def _render_quick_check_interface(self, user_id: int, pantry_categories: Dict):
        """Render quick availability checking interface"""
        st.markdown("#### ⚡ Quick Availability Check")
        st.caption("Quickly mark what you have vs. what you're out of")
        
        # Filter options
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            show_category = st.selectbox(
                "Show category:",
                ["all"] + list(pantry_categories.keys()),
                format_func=lambda x: "All Categories" if x == "all" else x.title()
            )
        
        with filter_col2:
            show_status = st.selectbox(
                "Show items:",
                ["all", "available", "unavailable"],
                format_func=lambda x: {"all": "All Items", "available": "Available Only", "unavailable": "Out of Stock Only"}.get(x, x)
            )
        
        # Get filtered items
        all_items = []
        categories_to_show = [show_category] if show_category != "all" else pantry_categories.keys()
        
        for category in categories_to_show:
            if category in pantry_categories:
                for item in pantry_categories[category]:
                    if show_status == "all" or (show_status == "available" and item.is_available) or (show_status == "unavailable" and not item.is_available):
                        all_items.append((category, item))
        
        if not all_items:
            st.info("No items match your filter criteria.")
            return
        
        # Show items in compact list with quick toggle
        st.markdown(f"**{len(all_items)} items to check:**")
        
        # Batch actions
        batch_col1, batch_col2, batch_col3 = st.columns(3)
        with batch_col1:
            if st.button("✅ Mark All Available"):
                for category, item in all_items:
                    self.pantry_service.update_pantry_item(user_id, item.ingredient_id, True)
                st.experimental_rerun()
        
        with batch_col2:
            if st.button("❌ Mark All Unavailable"):
                for category, item in all_items:
                    self.pantry_service.update_pantry_item(user_id, item.ingredient_id, False)
                st.experimental_rerun()
        
        with batch_col3:
            if st.button("🔄 Refresh List"):
                st.experimental_rerun()
        
        # Items list
        for category, item in all_items:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                status_icon = "✅" if item.is_available else "❌"
                st.write(f"{status_icon} **{item.ingredient_name}** _{category}_")
            
            with col2:
                new_status = st.checkbox(
                    "Available",
                    value=item.is_available,
                    key=f"quick_check_{item.ingredient_id}",
                    label_visibility="collapsed"
                )
                
                if new_status != item.is_available:
                    self.pantry_service.update_pantry_item(user_id, item.ingredient_id, new_status)
                    st.experimental_rerun()
            
            with col3:
                if item.is_available:
                    quantity = st.selectbox(
                        "Qty",
                        ["plenty", "just enough", "running low"],
                        index=["plenty", "just enough", "running low"].index(item.quantity_estimate or "plenty"),
                        key=f"quick_qty_{item.ingredient_id}",
                        label_visibility="collapsed"
                    )
                    if quantity != item.quantity_estimate:
                        self.pantry_service.update_pantry_item(user_id, item.ingredient_id, True, quantity)
            
            with col4:
                if st.button("🗑️", key=f"remove_{item.ingredient_id}", help="Remove from pantry"):
                    # Remove item from pantry (implement this method)
                    st.warning("Remove feature coming soon!")
    
    def _render_bulk_edit_interface(self, user_id: int, pantry_categories: Dict):
        """Render bulk editing interface for power users"""
        st.markdown("#### 📝 Bulk Edit Mode")
        st.caption("For power users - manage many ingredients at once")
        
        # Category selection for bulk operations
        selected_categories = st.multiselect(
            "Select categories to bulk edit:",
            list(pantry_categories.keys()),
            format_func=lambda x: x.title()
        )
        
        if not selected_categories:
            st.info("Select one or more categories to begin bulk editing.")
            return
        
        # Get all items from selected categories
        bulk_items = []
        for category in selected_categories:
            for item in pantry_categories[category]:
                bulk_items.append((category, item))
        
        st.success(f"Bulk editing {len(bulk_items)} items from {len(selected_categories)} categories")
        
        # Bulk operations
        st.markdown("**Bulk Operations:**")
        bulk_col1, bulk_col2, bulk_col3, bulk_col4 = st.columns(4)
        
        with bulk_col1:
            if st.button("✅ All Available"):
                for category, item in bulk_items:
                    self.pantry_service.update_pantry_item(user_id, item.ingredient_id, True, "plenty")
                st.experimental_rerun()
        
        with bulk_col2:
            if st.button("❌ All Unavailable"):
                for category, item in bulk_items:
                    self.pantry_service.update_pantry_item(user_id, item.ingredient_id, False)
                st.experimental_rerun()
        
        with bulk_col3:
            if st.button("⚠️ All Running Low"):
                for category, item in bulk_items:
                    if item.is_available:
                        self.pantry_service.update_pantry_item(user_id, item.ingredient_id, True, "running low")
                st.experimental_rerun()
        
        with bulk_col4:
            if st.button("🗑️ Remove Selected"):
                st.warning("Bulk remove feature coming soon!")
        
        # Show items with checkboxes for selection
        st.markdown("---")
        st.markdown("**Individual Items:**")
        
        # Create a more compact table-like view
        for category, item in bulk_items:
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
            
            with col1:
                st.write(f"**{item.ingredient_name}** _{category}_")
            
            with col2:
                new_available = st.checkbox("✓", value=item.is_available, key=f"bulk_avail_{item.ingredient_id}")
                if new_available != item.is_available:
                    self.pantry_service.update_pantry_item(user_id, item.ingredient_id, new_available)
            
            with col3:
                if new_available:
                    qty = st.selectbox(
                        "Q",
                        ["plenty", "enough", "low"],
                        index=["plenty", "enough", "low"].index("plenty"),
                        key=f"bulk_qty_{item.ingredient_id}",
                        label_visibility="collapsed"
                    )
            
            with col4:
                days_old = (datetime.now() - item.last_updated).days if item.last_updated else 0
                st.caption(f"{days_old}d ago")
            
            with col5:
                if st.button("🗑️", key=f"bulk_remove_{item.ingredient_id}"):
                    st.warning("Remove feature coming soon!")
    
    def _render_pantry_item_card(self, user_id: int, item: PantryItem):
        """Render individual pantry item card"""
        # Status indicator
        status_icon = "✅" if item.is_available else "❌"
        
        new_availability = st.checkbox(
            f"{status_icon} {item.ingredient_name}",
            value=item.is_available,
            key=f"item_card_{item.ingredient_id}",
            help=f"Category: {item.category}"
        )
        
        if new_availability != item.is_available:
            self.pantry_service.update_pantry_item(user_id, item.ingredient_id, new_availability)
            st.experimental_rerun()
        
        # Quantity selector for available items
        if new_availability:
            quantity = st.selectbox(
                "Amount:",
                ["plenty", "just enough", "running low"],
                index=["plenty", "just enough", "running low"].index(item.quantity_estimate or "plenty"),
                key=f"card_qty_{item.ingredient_id}"
            )
            
            if quantity != item.quantity_estimate:
                self.pantry_service.update_pantry_item(user_id, item.ingredient_id, new_availability, quantity)
    
    def _bulk_update_category(self, user_id: int, category: str, items: List[PantryItem], availability: bool):
        """Bulk update all items in a category"""
        for item in items:
            self.pantry_service.update_pantry_item(
                user_id, item.ingredient_id, availability, 
                "plenty" if availability else None
            )
    
    def _render_recipe_matching(self, user_id: int, mobile_mode: bool = False):
        """Render recipe matching interface - core feature"""
        st.markdown("### 🍽️ Recipes I Can Make")
        
        # Quick mode toggle
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            strict_mode = st.checkbox(
                "✅ Only show recipes I can make completely",
                value=True,
                help="Uncheck to see recipes missing 1-2 ingredients"
            )
        
        with col2:
            sort_by = st.selectbox(
                "Sort by:",
                ["match", "difficulty", "name"],
                format_func=lambda x: {"match": "Best Match", "difficulty": "Easiest First", "name": "Name"}.get(x, x)
            )
        
        with col3:
            max_results = st.selectbox("Show:", [10, 25, 50], index=1)
        
        # Get matching recipes
        with st.spinner("Finding recipes you can make..."):
            recipe_matches = self.pantry_service.find_makeable_recipes(
                user_id,
                strict_mode=strict_mode,
                include_partial_matches=not strict_mode
            )
        
        if not recipe_matches:
            st.warning("No recipes found that match your current pantry!")
            st.info("💡 **Try:**")
            st.info("• Adding more ingredients to your pantry")
            st.info("• Unchecking 'strict mode' to see almost-ready recipes")
            st.info("• Adding some common ingredients like salt, oil, or flour")
            return
        
        # Apply sorting
        if sort_by == "difficulty":
            recipe_matches.sort(key=lambda x: x.difficulty_score)
        elif sort_by == "name":
            recipe_matches.sort(key=lambda x: x.recipe.name)
        # Default is already sorted by match percentage
        
        # Limit results
        recipe_matches = recipe_matches[:max_results]
        
        st.success(f"Found {len(recipe_matches)} recipes you can make!")
        
        # Display recipes
        for i, match in enumerate(recipe_matches, 1):
            self._render_recipe_match_card(match, i, user_id, mobile_mode)
    
    def _render_recipe_match_card(self, match: RecipeMatch, index: int, user_id: int, mobile_mode: bool = False):
        """Render individual recipe match card"""
        recipe = match.recipe
        
        with st.container():
            # Recipe header
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**{index}. {recipe.name}** {match.match_status}")
                if recipe.description:
                    desc = recipe.description[:80] + "..." if len(recipe.description) > 80 else recipe.description
                    st.caption(desc)
            
            with col2:
                # Timing info
                if hasattr(recipe, 'prep_time_minutes') and hasattr(recipe, 'cook_time_minutes'):
                    total_time = recipe.prep_time_minutes + recipe.cook_time_minutes
                    st.metric("Time", f"{total_time}m")
            
            with col3:
                # Match percentage
                st.metric("Match", f"{match.match_percentage:.0%}")
            
            # Ingredient analysis
            if not mobile_mode or st.checkbox(f"Show ingredients for {recipe.name}", key=f"show_ingredients_{recipe.id}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    if match.available_ingredients:
                        st.markdown("**✅ You have:**")
                        for ingredient in match.available_ingredients[:5]:  # Show max 5
                            st.write(f"• {ingredient}")
                        if len(match.available_ingredients) > 5:
                            st.caption(f"...and {len(match.available_ingredients) - 5} more")
                
                with col2:
                    if match.missing_ingredients:
                        st.markdown("**❌ You need:**")
                        for ingredient in match.missing_ingredients:
                            st.write(f"• {ingredient}")
            
            # Action buttons
            action_col1, action_col2, action_col3 = st.columns(3)
            
            with action_col1:
                if st.button(f"👁️ View Recipe", key=f"view_recipe_{recipe.id}"):
                    self._show_recipe_details(recipe)
            
            with action_col2:
                if st.button(f"🛒 Add to List", key=f"add_shopping_{recipe.id}"):
                    self._add_recipe_to_shopping_list(recipe.id)
                    st.success("Added to shopping list!")
            
            with action_col3:
                if match.can_make:
                    if st.button(f"🍳 Start Cooking", key=f"cook_{recipe.id}", type="primary"):
                        self._start_cooking_mode(recipe)
            
            st.markdown("---")
    
    def _render_shopping_list(self, user_id: int):
        """Render shopping list generation interface"""
        st.markdown("### 🛒 Shopping List Generator")
        
        # Get selected recipes for shopping list
        selected_recipes = st.session_state.get(self.SELECTED_RECIPES_KEY, [])
        
        if not selected_recipes:
            st.info("Add recipes to your shopping list from the 'What Can I Make?' tab to see ingredients you need to buy.")
            return
        
        # Generate shopping list
        shopping_list = self.pantry_service.get_shopping_list(user_id, selected_recipes)
        
        if not shopping_list:
            st.info("All ingredients for selected recipes are already in your pantry!")
            return
        
        st.success(f"Shopping list for {len(selected_recipes)} recipes:")
        
        # Display shopping list by category
        for category, ingredients in shopping_list.items():
            with st.expander(f"📦 {category.title()} ({len(ingredients)} items)", expanded=True):
                for ingredient in ingredients:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"• {ingredient}")
                    with col2:
                        if st.button("✅", key=f"check_{ingredient.replace(' ', '_')}", help="Got it!"):
                            st.success("👍")
        
        # Export options
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📧 Email List", help="Send shopping list via email"):
                st.info("Email feature coming soon!")
        
        with col2:
            if st.button("📱 Text List", help="Send to phone"):
                st.info("SMS feature coming soon!")
        
        with col3:
            if st.button("🖨️ Print List", help="Print shopping list"):
                # Generate printable version
                printable_text = "SHOPPING LIST\n" + "="*20 + "\n\n"
                for category, ingredients in shopping_list.items():
                    printable_text += f"{category.upper()}:\n"
                    for ingredient in ingredients:
                        printable_text += f"  □ {ingredient}\n"
                    printable_text += "\n"
                
                st.text_area("Copy this shopping list:", printable_text, height=200)
    
    def _render_recipe_suggestions(self, user_id: int):
        """Render recipe suggestions interface"""
        st.markdown("### 💡 Recipe Suggestions")
        
        # Suggestions for recipes that need just a few more ingredients
        suggestions = self.pantry_service.suggest_recipes_to_complete_pantry(user_id, max_missing=3)
        
        if not suggestions:
            st.info("No suggestions right now. Try adding more ingredients to your pantry!")
            return
        
        st.info(f"Found {len(suggestions)} recipes you could make with just a few more ingredients:")
        
        for suggestion in suggestions[:10]:  # Top 10 suggestions
            recipe = suggestion.recipe
            
            with st.expander(f"🎯 {recipe.name} (need {len(suggestion.missing_ingredients)} more ingredients)"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Recipe:** {recipe.name}")
                    if recipe.description:
                        st.write(recipe.description[:100] + "...")
                    
                    # Show timing and difficulty
                    if hasattr(recipe, 'prep_time_minutes') and hasattr(recipe, 'cook_time_minutes'):
                        total_time = recipe.prep_time_minutes + recipe.cook_time_minutes
                        st.write(f"**Total time:** {total_time} minutes")
                    
                    st.write(f"**Difficulty:** {recipe.difficulty_level}")
                
                with col2:
                    st.write(f"**You need to buy:**")
                    for ingredient in suggestion.missing_ingredients:
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            st.write(f"• {ingredient}")
                        with col_b:
                            if st.button("🛒", key=f"add_single_{recipe.id}_{ingredient}", help="Add to shopping list"):
                                st.success("Added!")
                
                # Action buttons
                button_col1, button_col2 = st.columns(2)
                with button_col1:
                    if st.button(f"📝 Add All to Shopping List", key=f"add_all_suggest_{recipe.id}"):
                        self._add_recipe_to_shopping_list(recipe.id)
                        st.success("All ingredients added to shopping list!")
                
                with button_col2:
                    if st.button(f"👁️ View Full Recipe", key=f"view_suggest_{recipe.id}"):
                        self._show_recipe_details(recipe)
    
    def _render_add_ingredient_form(self, user_id: int, simplified: bool = False, prefilled_name: str = ""):
        """Render form to add new ingredients to pantry"""
        form_title = "➕ Add New Ingredient" if not simplified else "Add Ingredient"
        expanded = simplified  # Simplified form is always expanded
        
        with st.expander(form_title, expanded=expanded):
            form_key = "add_ingredient_simple" if simplified else "add_ingredient_form"
            
            with st.form(form_key):
                if simplified:
                    # Simplified single-column form
                    new_ingredient_name = st.text_input(
                        "Ingredient name", 
                        value=prefilled_name,
                        placeholder="e.g. chicken breast, olive oil, garlic"
                    )
                    col1, col2 = st.columns(2)
                    with col1:
                        category = st.selectbox(
                            "Category",
                            ["protein", "vegetable", "fruit", "grain", "dairy", "spice", "seasoning", "oil", "sweetener", "other"]
                        )
                    with col2:
                        is_available = st.checkbox("I have this", value=True)
                else:
                    # Full two-column form
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        new_ingredient_name = st.text_input(
                            "Ingredient name", 
                            value=prefilled_name,
                            placeholder="e.g. chicken breast, olive oil, garlic"
                        )
                        category = st.selectbox(
                            "Category",
                            ["protein", "vegetable", "fruit", "grain", "dairy", "spice", "seasoning", "oil", "sweetener", "other"]
                        )
                    
                    with col2:
                        is_available = st.checkbox("I have this ingredient", value=True)
                        quantity = st.selectbox("How much?", ["plenty", "just enough", "running low"])
                
                # Submit button
                submit_text = "Add to Pantry" if not simplified else "Add"
                if st.form_submit_button(submit_text, type="primary"):
                    if new_ingredient_name.strip():
                        # Find or create ingredient
                        ingredients = self.db.search_ingredients(new_ingredient_name)
                        ingredient = None
                        
                        if ingredients:
                            # Use existing ingredient if close match found
                            exact_match = next((ing for ing in ingredients 
                                              if ing.name.lower() == new_ingredient_name.lower().strip()), None)
                            if exact_match:
                                ingredient = exact_match
                        
                        if not ingredient:
                            # Create new ingredient
                            ingredient = self.db.create_ingredient(new_ingredient_name.strip(), category)
                        
                        if ingredient:
                            # Add to pantry
                            default_quantity = "plenty" if simplified else quantity
                            success = self.pantry_service.update_pantry_item(
                                user_id, ingredient.id, is_available, default_quantity
                            )
                            
                            if success:
                                st.success(f"Added '{ingredient.name}' to your pantry!")
                                st.experimental_rerun()
                            else:
                                st.error("Failed to add ingredient to pantry")
                        else:
                            st.error("Failed to create ingredient")
                    else:
                        st.error("Please enter an ingredient name")
    
    def _show_recipe_details(self, recipe: Recipe):
        """Show detailed recipe view"""
        st.session_state["selected_recipe_details"] = recipe
        st.info(f"Recipe details for '{recipe.name}' - detailed view feature coming soon!")
    
    def _add_recipe_to_shopping_list(self, recipe_id: int):
        """Add recipe to shopping list"""
        selected_recipes = st.session_state.get(self.SELECTED_RECIPES_KEY, [])
        if recipe_id not in selected_recipes:
            selected_recipes.append(recipe_id)
            st.session_state[self.SELECTED_RECIPES_KEY] = selected_recipes
    
    def _start_cooking_mode(self, recipe: Recipe):
        """Start cooking mode for recipe"""
        st.session_state["cooking_recipe"] = recipe
        st.success(f"Starting cooking mode for '{recipe.name}' - cooking assistant feature coming soon!")


# Factory function
def create_pantry_manager(database_service: Optional[DatabaseService] = None) -> PantryManagerInterface:
    """Factory function to create pantry manager interface"""
    return PantryManagerInterface(database_service)