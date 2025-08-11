"""
Responsive design utilities and CSS for Pans Cookbook application.

Provides mobile-friendly layouts, responsive CSS injection, and adaptive
component sizing for optimal viewing on all device types.
"""

import streamlit as st
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ResponsiveDesign:
    """
    Responsive design utility class for Streamlit applications.
    
    Handles mobile-first design patterns, responsive breakpoints,
    and device-specific optimizations.
    """
    
    # Responsive breakpoints (based on common device sizes)
    BREAKPOINTS = {
        'mobile': 480,
        'tablet': 768,
        'desktop': 1024,
        'large': 1200
    }
    
    def __init__(self):
        self._inject_responsive_css()
        self._setup_responsive_config()
    
    def _inject_responsive_css(self):
        """Inject responsive CSS styles"""
        st.markdown("""
        <style>
        /* Global responsive styles */
        .main > div {
            padding-top: 1rem;
        }
        
        /* Mobile-first approach */
        @media (max-width: 480px) {
            .stApp {
                padding: 0.5rem;
            }
            
            .main .block-container {
                padding: 1rem 0.5rem;
                max-width: 100%;
            }
            
            .stTabs [data-baseweb="tab-list"] {
                gap: 0;
                flex-wrap: wrap;
            }
            
            .stTabs [data-baseweb="tab"] {
                font-size: 0.8rem;
                padding: 0.5rem;
                min-width: auto;
            }
            
            /* Responsive buttons */
            .stButton button {
                width: 100%;
                font-size: 0.9rem;
                padding: 0.5rem;
            }
            
            /* Responsive metrics */
            [data-testid="metric-container"] {
                margin: 0.25rem 0;
            }
            
            /* Responsive columns */
            .row-widget {
                gap: 0.5rem;
            }
            
            /* Form elements */
            .stTextInput input,
            .stTextArea textarea,
            .stSelectbox select {
                font-size: 1rem;
                padding: 0.75rem;
            }
            
            /* Search interface mobile */
            .search-container {
                padding: 0.5rem;
                margin: 0.5rem 0;
            }
            
            .search-result-item {
                padding: 0.75rem;
                margin: 0.5rem 0;
            }
            
            /* Recipe cards mobile */
            .recipe-card {
                padding: 0.75rem;
                margin: 0.5rem 0;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
            
            .recipe-card h4 {
                font-size: 1.1rem;
                margin-bottom: 0.5rem;
            }
            
            .recipe-meta {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                font-size: 0.85rem;
            }
            
            /* AI features mobile */
            .ai-feature-panel {
                padding: 0.75rem;
                margin: 0.5rem 0;
            }
            
            .ai-status-compact {
                flex-direction: column;
                align-items: flex-start;
                gap: 0.5rem;
            }
        }
        
        /* Tablet styles */
        @media (min-width: 481px) and (max-width: 768px) {
            .main .block-container {
                padding: 1.5rem 1rem;
            }
            
            .stTabs [data-baseweb="tab"] {
                font-size: 0.9rem;
                padding: 0.75rem 1rem;
            }
            
            .recipe-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 1rem;
            }
            
            .search-filters {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1rem;
            }
        }
        
        /* Desktop styles */
        @media (min-width: 769px) and (max-width: 1024px) {
            .recipe-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 1.5rem;
            }
            
            .search-filters {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 1rem;
            }
            
            .ai-features-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1.5rem;
            }
        }
        
        /* Large screen styles */
        @media (min-width: 1025px) {
            .recipe-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 2rem;
            }
            
            .search-filters {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 1.5rem;
            }
            
            .ai-features-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 2rem;
            }
        }
        
        /* Responsive utilities */
        .flex-mobile {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        @media (min-width: 769px) {
            .flex-mobile {
                flex-direction: row;
                align-items: center;
                gap: 1rem;
            }
        }
        
        .hide-mobile {
            display: none;
        }
        
        @media (min-width: 769px) {
            .hide-mobile {
                display: block;
            }
        }
        
        .show-mobile {
            display: block;
        }
        
        @media (min-width: 769px) {
            .show-mobile {
                display: none;
            }
        }
        
        /* Touch-friendly improvements */
        button, .stButton button {
            min-height: 44px;
            touch-action: manipulation;
        }
        
        /* Improved contrast for accessibility */
        .dietary-tag {
            background-color: #E8F5E9;
            color: #1B5E20;
            border: 1px solid #C8E6C9;
            font-weight: 500;
        }
        
        /* Loading states */
        .loading-skeleton {
            background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
            background-size: 200% 100%;
            animation: loading 1.5s infinite;
        }
        
        @keyframes loading {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }
        
        /* Focus indicators for accessibility */
        button:focus,
        input:focus,
        select:focus,
        textarea:focus {
            outline: 2px solid #2196F3;
            outline-offset: 2px;
        }
        
        /* Print styles */
        @media print {
            .stSidebar,
            .stButton,
            .stTabs [data-baseweb="tab-list"] {
                display: none !important;
            }
            
            .recipe-card {
                break-inside: avoid;
                border: 1px solid #000;
            }
        }
        </style>
        """, unsafe_allow_html=True)
    
    def _setup_responsive_config(self):
        """Setup responsive configuration"""
        # Enable mobile viewport
        st.markdown("""
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        """, unsafe_allow_html=True)
    
    def get_responsive_columns(self, device_type: str = "auto") -> Tuple[int, int, int]:
        """
        Get responsive column configuration based on device type.
        
        Args:
            device_type: Device type or 'auto' for automatic detection
            
        Returns:
            Tuple of (mobile_cols, tablet_cols, desktop_cols)
        """
        if device_type == "mobile":
            return (1, 2, 3)
        elif device_type == "tablet":
            return (2, 3, 4)
        else:  # desktop or auto
            return (1, 2, 4)
    
    def create_responsive_grid(self, items: List, cols_config: Tuple[int, int, int] = None):
        """
        Create responsive grid layout for items.
        
        Args:
            items: List of items to display
            cols_config: Column configuration (mobile, tablet, desktop)
        """
        if not cols_config:
            cols_config = self.get_responsive_columns()
        
        # For Streamlit, we'll use columns with responsive CSS
        st.markdown('<div class="recipe-grid">', unsafe_allow_html=True)
        
        # Create columns dynamically (Streamlit limitation - we'll use CSS grid instead)
        for i, item in enumerate(items):
            with st.container():
                st.markdown('<div class="recipe-card">', unsafe_allow_html=True)
                yield item, i
                st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def create_mobile_friendly_form(self, form_key: str):
        """Create mobile-friendly form with optimized inputs"""
        return st.form(key=form_key, clear_on_submit=False)
    
    def render_responsive_metrics(self, metrics: List[Dict[str, str]], 
                                 mobile_stack: bool = True):
        """
        Render metrics in responsive layout.
        
        Args:
            metrics: List of metric dictionaries with 'label' and 'value'
            mobile_stack: Whether to stack metrics on mobile
        """
        if mobile_stack:
            st.markdown('<div class="flex-mobile">', unsafe_allow_html=True)
        
        cols = st.columns(len(metrics))
        for i, metric in enumerate(metrics):
            with cols[i]:
                st.metric(
                    label=metric['label'],
                    value=metric['value'],
                    delta=metric.get('delta', None)
                )
        
        if mobile_stack:
            st.markdown('</div>', unsafe_allow_html=True)
    
    def create_responsive_tabs(self, tab_config: List[Dict[str, str]], 
                             mobile_scroll: bool = True):
        """
        Create responsive tabs that work well on mobile.
        
        Args:
            tab_config: List of tab configurations with 'label' and 'icon'
            mobile_scroll: Whether tabs should scroll on mobile
        """
        tab_labels = []
        for config in tab_config:
            if 'icon' in config:
                label = f"{config['icon']} {config['label']}"
            else:
                label = config['label']
            tab_labels.append(label)
        
        return st.tabs(tab_labels)
    
    def render_loading_skeleton(self, height: str = "100px", count: int = 1):
        """Render loading skeleton for better UX"""
        for i in range(count):
            st.markdown(f"""
            <div class="loading-skeleton" style="height: {height}; margin: 1rem 0; border-radius: 8px;">
            </div>
            """, unsafe_allow_html=True)
    
    def is_mobile_viewport(self) -> bool:
        """
        Detect if user is on mobile viewport (approximation).
        Note: Streamlit doesn't have direct viewport detection,
        so this is a best-effort approach.
        """
        # This is a placeholder - in a real app, you might use JavaScript
        # or check user agent strings, but Streamlit has limitations here
        return False
    
    def create_mobile_navigation_menu(self, menu_items: List[Dict[str, str]]):
        """Create mobile-friendly navigation menu"""
        st.markdown('<div class="mobile-nav show-mobile">', unsafe_allow_html=True)
        
        selected_item = st.selectbox(
            "Navigate to:",
            options=[item['label'] for item in menu_items],
            key="mobile_nav_select"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        return selected_item
    
    def optimize_images_responsive(self, image_url: str, alt_text: str = "",
                                  max_width: str = "100%"):
        """Render responsive images with proper sizing"""
        st.markdown(f"""
        <img src="{image_url}" alt="{alt_text}" 
             style="max-width: {max_width}; height: auto; border-radius: 8px;"
             loading="lazy">
        """, unsafe_allow_html=True)
    
    def create_collapsible_section(self, title: str, content_key: str,
                                  expanded_on_desktop: bool = True,
                                  expanded_on_mobile: bool = False):
        """Create sections that are collapsible on mobile for better UX"""
        # On mobile, default to collapsed to save space
        default_expanded = expanded_on_mobile  # Assume mobile for now
        
        with st.expander(title, expanded=default_expanded):
            return True  # Return context for content rendering


class MobileOptimizations:
    """
    Mobile-specific optimizations for Pans Cookbook.
    """
    
    @staticmethod
    def render_mobile_search_bar():
        """Render mobile-optimized search bar"""
        st.markdown("""
        <style>
        .mobile-search {
            position: sticky;
            top: 0;
            background: white;
            z-index: 1000;
            padding: 0.5rem 0;
            border-bottom: 1px solid #e0e0e0;
            margin-bottom: 1rem;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="mobile-search">', unsafe_allow_html=True)
        search_query = st.text_input(
            "Search recipes...",
            placeholder="🔍 What would you like to cook?",
            key="mobile_search"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        return search_query
    
    @staticmethod
    def render_mobile_recipe_card(recipe, show_full_details: bool = False):
        """Render mobile-optimized recipe card"""
        st.markdown('<div class="recipe-card">', unsafe_allow_html=True)
        
        # Title
        st.markdown(f"#### {recipe.title}")
        
        # Meta information in compact format
        meta_items = []
        if hasattr(recipe, 'prep_time_minutes'):
            total_time = recipe.prep_time_minutes + getattr(recipe, 'cook_time_minutes', 0)
            meta_items.append(f"⏱️ {total_time}min")
        
        if hasattr(recipe, 'servings'):
            meta_items.append(f"👥 {recipe.servings}")
        
        if hasattr(recipe, 'difficulty_level'):
            meta_items.append(f"📊 {recipe.difficulty_level}")
        
        if meta_items:
            st.markdown(f'<div class="recipe-meta">{" • ".join(meta_items)}</div>', 
                       unsafe_allow_html=True)
        
        # Description (truncated on mobile)
        if hasattr(recipe, 'description') and recipe.description:
            desc = recipe.description
            if not show_full_details and len(desc) > 100:
                desc = desc[:100] + "..."
            st.caption(desc)
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("👁️ View", key=f"view_mobile_{recipe.id}"):
                return "view"
        with col2:
            if st.button("❤️ Save", key=f"save_mobile_{recipe.id}"):
                return "save"
        with col3:
            if st.button("📤 Share", key=f"share_mobile_{recipe.id}"):
                return "share"
        
        st.markdown('</div>', unsafe_allow_html=True)
        return None
    
    @staticmethod
    def render_mobile_filter_drawer():
        """Render mobile-friendly filter drawer"""
        with st.expander("🔧 Filters", expanded=False):
            st.markdown("### Quick Filters")
            
            # Quick time filters
            time_filter = st.selectbox(
                "Cooking Time",
                ["Any time", "Quick (≤30min)", "Moderate (30-60min)", "Long (≥60min)"],
                key="mobile_time_filter"
            )
            
            # Quick cuisine filter
            cuisine_filter = st.multiselect(
                "Cuisine",
                ["Italian", "American", "Asian", "Mediterranean", "Mexican"],
                key="mobile_cuisine_filter"
            )
            
            # Quick dietary filter
            dietary_filter = st.multiselect(
                "Dietary",
                ["Vegetarian", "Vegan", "Gluten-free", "Dairy-free", "Keto"],
                key="mobile_dietary_filter"
            )
            
            return {
                'time': time_filter,
                'cuisine': cuisine_filter,
                'dietary': dietary_filter
            }


# Factory functions for easy usage
def get_responsive_design() -> ResponsiveDesign:
    """Get responsive design utility instance"""
    return ResponsiveDesign()


def apply_mobile_optimizations():
    """Apply mobile optimizations to current page"""
    responsive = ResponsiveDesign()
    # Additional mobile-specific setup can be added here
    return responsive


def create_responsive_layout(layout_type: str = "standard") -> ResponsiveDesign:
    """
    Create responsive layout with specific configuration.
    
    Args:
        layout_type: Type of layout ('standard', 'search', 'recipe', 'admin')
    """
    responsive = ResponsiveDesign()
    
    # Layout-specific configurations can be added here
    if layout_type == "search":
        # Search-specific responsive configurations
        pass
    elif layout_type == "recipe":
        # Recipe-specific responsive configurations
        pass
    
    return responsive