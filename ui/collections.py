"""
Collections management UI for Pans Cookbook application.

Provides collection creation, management, sharing, shopping list generation,
and integration with recipe browsing. Leverages Herbalism app UI patterns
with recipe-specific collection features.
"""

import streamlit as st
from typing import List, Dict, Set, Optional, Any, Tuple
import json
from datetime import datetime
import secrets
import base64

from models import Collection, Recipe, ShoppingList, User
from services import CollectionService, DatabaseService, get_database_service, get_collection_service
from utils import get_logger

logger = get_logger(__name__)


class CollectionsInterface:
    """
    Collections management interface for organizing and sharing recipe collections.
    
    Features collection CRUD operations, favorites management, sharing functionality,
    and shopping list generation with persistent user state management.
    """
    
    def __init__(self, collection_service: Optional[CollectionService] = None,
                 database_service: Optional[DatabaseService] = None):
        self.collection_service = collection_service or get_collection_service()
        self.db = database_service or get_database_service()
        
        # Initialize custom CSS styling
        self._inject_custom_css()
        
        # Session state keys
        self.CURRENT_COLLECTION_KEY = "current_collection_id"
        self.EDIT_MODE_KEY = "collection_edit_mode"
        self.SHOW_SHARING_KEY = "show_sharing_interface"
        self.SHOPPING_LIST_KEY = "current_shopping_list"
    
    def render_collections_page(self, current_user: User) -> None:
        """Render the main collections management page"""
        if not current_user:
            st.error("🔒 Please log in to access collections.")
            return
        
        st.title("📚 My Recipe Collections")
        st.markdown("*Organize your recipes into collections and generate shopping lists*")
        
        # Main navigation tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📖 My Collections", "➕ Create Collection", "🛒 Shopping Lists", "🔗 Shared Collections"
        ])
        
        with tab1:
            self._render_collections_list(current_user)
        
        with tab2:
            self._render_collection_creator(current_user)
        
        with tab3:
            self._render_shopping_lists(current_user)
        
        with tab4:
            self._render_shared_collections(current_user)
    
    def _render_collections_list(self, current_user: User) -> None:
        """Render user's collections list with management options"""
        st.header("📚 Your Collections")
        
        # Get user collections
        collections = self.collection_service.get_user_collections(current_user.id, include_public=False)
        
        if not collections:
            st.info("🎯 You haven't created any collections yet. Use the 'Create Collection' tab to get started!")
            return
        
        # Collection actions header
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown("### Manage Your Collections")
        with col2:
            if st.button("🔄 Refresh", key="refresh_collections"):
                st.rerun()
        with col3:
            show_public = st.checkbox("Show Public", key="show_public_collections")
        
        if show_public:
            collections = self.collection_service.get_user_collections(current_user.id, include_public=True)
        
        # Display collections
        for collection in collections:
            self._render_collection_card(collection, current_user)
    
    def _render_collection_card(self, collection: Collection, current_user: User) -> None:
        """Render a single collection card with management options"""
        is_owner = collection.user_id == current_user.id
        
        with st.container():
            # Collection header with favorite indicator
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                favorite_icon = "⭐" if collection.is_favorite else "📂"
                public_icon = "🌍" if collection.is_public else "🔒"
                st.markdown(f"### {favorite_icon} {collection.name} {public_icon}")
                
                if collection.description:
                    st.markdown(f"*{collection.description}*")
                
                # Collection metadata
                recipe_count = collection.get_recipe_count()
                st.markdown(f"📖 **{recipe_count}** recipes")
                
                if collection.tags:
                    tags_display = " ".join([f"`{tag}`" for tag in collection.tags])
                    st.markdown(f"🏷️ {tags_display}")
            
            with col2:
                if is_owner and st.button("✏️ Edit", key=f"edit_{collection.id}"):
                    st.session_state[self.CURRENT_COLLECTION_KEY] = collection.id
                    st.session_state[self.EDIT_MODE_KEY] = True
                    st.rerun()
            
            with col3:
                if st.button("👁️ View", key=f"view_{collection.id}"):
                    st.session_state[self.CURRENT_COLLECTION_KEY] = collection.id
                    st.session_state[self.EDIT_MODE_KEY] = False
                    st.rerun()
            
            with col4:
                if is_owner:
                    if st.button("🗑️ Delete", key=f"delete_{collection.id}"):
                        if st.session_state.get(f"confirm_delete_{collection.id}", False):
                            success = self.collection_service.delete_collection(collection.id, current_user.id)
                            if success:
                                st.success(f"✅ Deleted collection '{collection.name}'")
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete collection")
                        else:
                            st.session_state[f"confirm_delete_{collection.id}"] = True
                            st.warning("Click delete again to confirm")
            
            # Show collection detail modal if selected
            if st.session_state.get(self.CURRENT_COLLECTION_KEY) == collection.id:
                self._render_collection_detail_modal(collection, current_user)
            
            st.divider()
    
    def _render_collection_detail_modal(self, collection: Collection, current_user: User) -> None:
        """Render detailed collection view/edit modal"""
        is_owner = collection.user_id == current_user.id
        edit_mode = st.session_state.get(self.EDIT_MODE_KEY, False)
        
        if edit_mode and is_owner:
            st.markdown("### ✏️ Edit Collection")
            self._render_collection_editor(collection, current_user)
        else:
            st.markdown("### 👁️ Collection Details")
            self._render_collection_viewer(collection, current_user)
        
        # Close button
        if st.button("❌ Close", key=f"close_{collection.id}"):
            st.session_state.pop(self.CURRENT_COLLECTION_KEY, None)
            st.session_state.pop(self.EDIT_MODE_KEY, None)
            st.rerun()
    
    def _render_collection_viewer(self, collection: Collection, current_user: User) -> None:
        """Render collection in view mode"""
        is_owner = collection.user_id == current_user.id
        
        # Collection info
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"**Name:** {collection.name}")
            st.markdown(f"**Description:** {collection.description}")
            st.markdown(f"**Privacy:** {'Public' if collection.is_public else 'Private'}")
            st.markdown(f"**Created:** {collection.created_at}")
            
            if collection.tags:
                st.markdown(f"**Tags:** {', '.join(collection.tags)}")
        
        with col2:
            # Favorite management
            if is_owner:
                current_favorite = collection.is_favorite
                if st.button(f"{'⭐ Remove from Favorites' if current_favorite else '⭐ Set as Favorite'}", 
                           key=f"fav_{collection.id}"):
                    success = self.collection_service.set_favorite_collection(
                        collection.id, current_user.id, not current_favorite
                    )
                    if success:
                        st.success("✅ Favorites updated!")
                        st.rerun()
            
            # Sharing management
            if is_owner:
                if st.button("🔗 Share Collection", key=f"share_{collection.id}"):
                    st.session_state[self.SHOW_SHARING_KEY] = collection.id
                    st.rerun()
            
            # Shopping list generation
            if st.button("🛒 Generate Shopping List", key=f"shopping_{collection.id}"):
                shopping_list = self.collection_service.generate_shopping_list(collection.id)
                if shopping_list:
                    st.session_state[self.SHOPPING_LIST_KEY] = shopping_list
                    st.success("✅ Shopping list generated!")
                    st.rerun()
                else:
                    st.error("❌ Failed to generate shopping list")
        
        # Show sharing interface if requested
        if st.session_state.get(self.SHOW_SHARING_KEY) == collection.id:
            self._render_sharing_interface(collection, current_user)
        
        # Show shopping list if generated
        if st.session_state.get(self.SHOPPING_LIST_KEY):
            shopping_list = st.session_state[self.SHOPPING_LIST_KEY]
            if shopping_list.collection_id == collection.id:
                self._render_shopping_list_display(shopping_list)
        
        # Collection recipes
        st.markdown("### 📖 Recipes in Collection")
        recipes = self.collection_service.get_collection_recipes(collection.id)
        
        if not recipes:
            st.info("📝 No recipes in this collection yet.")
            return
        
        # Display recipes in a nice format
        for recipe in recipes:
            with st.expander(f"🍳 {recipe.name}", expanded=False):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown(f"**Description:** {recipe.description}")
                    st.markdown(f"**Servings:** {recipe.servings}")
                    
                with col2:
                    st.markdown(f"**Prep:** {recipe.prep_time_minutes}m")
                    st.markdown(f"**Cook:** {recipe.cook_time_minutes}m")
                    
                with col3:
                    st.markdown(f"**Difficulty:** {recipe.difficulty_level}")
                    if recipe.cuisine_type:
                        st.markdown(f"**Cuisine:** {recipe.cuisine_type}")
                
                # Remove recipe option for owners
                if is_owner:
                    if st.button(f"🗑️ Remove from Collection", key=f"remove_recipe_{recipe.id}_{collection.id}"):
                        success = self.collection_service.remove_recipe_from_collection(recipe.id, collection.id)
                        if success:
                            st.success(f"✅ Removed '{recipe.name}' from collection")
                            st.rerun()
    
    def _render_collection_editor(self, collection: Collection, current_user: User) -> None:
        """Render collection editor form"""
        with st.form(f"edit_collection_{collection.id}"):
            # Collection basic info
            name = st.text_input("Collection Name", value=collection.name, max_chars=100)
            description = st.text_area("Description", value=collection.description, max_chars=500)
            
            # Tags
            tags_str = ", ".join(collection.tags) if collection.tags else ""
            tags_input = st.text_input("Tags (comma-separated)", value=tags_str)
            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()] if tags_input else []
            
            # Privacy setting
            is_public = st.checkbox("Make collection public", value=collection.is_public)
            
            # Submit buttons
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.form_submit_button("💾 Save Changes", type="primary"):
                    success = self.collection_service.update_collection(
                        collection.id,
                        name=name,
                        description=description,
                        tags=tags,
                        is_public=is_public
                    )
                    
                    if success:
                        st.success("✅ Collection updated successfully!")
                        st.session_state.pop(self.EDIT_MODE_KEY, None)
                        st.rerun()
                    else:
                        st.error("❌ Failed to update collection")
            
            with col2:
                if st.form_submit_button("❌ Cancel"):
                    st.session_state.pop(self.EDIT_MODE_KEY, None)
                    st.rerun()
    
    def _render_collection_creator(self, current_user: User) -> None:
        """Render collection creation form"""
        st.header("➕ Create New Collection")
        
        with st.form("create_collection"):
            # Basic collection info
            name = st.text_input("Collection Name *", max_chars=100, 
                               placeholder="e.g., 'Sunday Dinners', 'Quick Weekday Meals'")
            description = st.text_area("Description", max_chars=500,
                                     placeholder="Describe your collection...")
            
            # Tags
            tags_input = st.text_input("Tags (comma-separated)", 
                                     placeholder="dinner, family, quick, healthy")
            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()] if tags_input else []
            
            # Privacy setting
            is_public = st.checkbox("Make collection public", value=False,
                                   help="Public collections can be discovered and viewed by other users")
            
            # Create button
            if st.form_submit_button("🎯 Create Collection", type="primary"):
                if not name.strip():
                    st.error("❌ Collection name is required")
                else:
                    collection = self.collection_service.create_collection(
                        name=name.strip(),
                        user_id=current_user.id,
                        description=description.strip(),
                        tags=tags,
                        is_public=is_public
                    )
                    
                    if collection:
                        st.success(f"✅ Created collection '{collection.name}'!")
                        
                        # Option to set as favorite
                        if st.button("⭐ Set as Favorite"):
                            self.collection_service.set_favorite_collection(collection.id, current_user.id, True)
                            st.success("⭐ Set as favorite collection!")
                        
                        # Clear form and refresh
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Failed to create collection")
    
    def _render_shopping_lists(self, current_user: User) -> None:
        """Render shopping list management interface"""
        st.header("🛒 Shopping Lists")
        
        # Collection selector for shopping list generation
        collections = self.collection_service.get_user_collections(current_user.id)
        
        if not collections:
            st.info("📝 Create some collections first to generate shopping lists!")
            return
        
        # Select collection
        collection_options = {f"{c.name} ({c.get_recipe_count()} recipes)": c.id for c in collections}
        selected_name = st.selectbox("Select Collection for Shopping List", list(collection_options.keys()))
        
        if selected_name:
            selected_id = collection_options[selected_name]
            selected_collection = next(c for c in collections if c.id == selected_id)
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.button("🛒 Generate Shopping List", type="primary"):
                    shopping_list = self.collection_service.generate_shopping_list(selected_id)
                    if shopping_list:
                        st.session_state[self.SHOPPING_LIST_KEY] = shopping_list
                        st.success("✅ Shopping list generated!")
                        st.rerun()
            
            with col2:
                if st.button("🔄 Clear List"):
                    st.session_state.pop(self.SHOPPING_LIST_KEY, None)
                    st.rerun()
        
        # Display current shopping list
        if st.session_state.get(self.SHOPPING_LIST_KEY):
            shopping_list = st.session_state[self.SHOPPING_LIST_KEY]
            self._render_shopping_list_display(shopping_list)
    
    def _render_shopping_list_display(self, shopping_list: ShoppingList) -> None:
        """Render shopping list with categorization and export options"""
        st.markdown("### 🛒 Shopping List")
        st.markdown(f"**Collection:** {shopping_list.collection_name}")
        st.markdown(f"**Recipes:** {shopping_list.total_recipes}")
        st.markdown(f"**Total Items:** {shopping_list.get_total_items()}")
        st.markdown(f"**Generated:** {shopping_list.generated_at.strftime('%Y-%m-%d %H:%M')}")
        
        # Export options
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("📋 Copy to Clipboard"):
                shopping_text = self._generate_shopping_list_text(shopping_list)
                # Note: Actual clipboard functionality would require additional libraries
                st.info("📋 Shopping list text generated (copy manually below)")
        
        with col2:
            if st.button("📧 Email List"):
                st.info("📧 Email functionality would integrate with user's email service")
        
        with col3:
            if st.button("🖨️ Print View"):
                st.info("🖨️ Print-friendly view would open in new window")
        
        # Display shopping list by category
        categories = shopping_list.get_items_by_category()
        
        for category, items in categories.items():
            with st.expander(f"🏷️ {category} ({len(items)} items)", expanded=True):
                for item in items:
                    # Item with checkbox for checking off
                    checked = st.checkbox(
                        f"**{item.ingredient_name}**: {item.total_quantity:g} {item.unit}",
                        key=f"shopping_item_{item.ingredient_name}_{category}",
                        help=f"Used in: {', '.join(item.recipe_names)}"
                    )
                    
                    # Show which recipes use this ingredient
                    if len(item.recipe_names) > 1:
                        st.caption(f"📖 Used in {len(item.recipe_names)} recipes: {', '.join(item.recipe_names)}")
        
        # Raw text output for copying
        with st.expander("📝 Raw Text (for copying)", expanded=False):
            shopping_text = self._generate_shopping_list_text(shopping_list)
            st.text(shopping_text)
    
    def _generate_shopping_list_text(self, shopping_list: ShoppingList) -> str:
        """Generate plain text version of shopping list"""
        lines = [
            f"Shopping List: {shopping_list.collection_name}",
            f"Generated: {shopping_list.generated_at.strftime('%Y-%m-%d %H:%M')}",
            f"Recipes: {shopping_list.total_recipes}",
            f"Total Items: {shopping_list.get_total_items()}",
            "",
        ]
        
        categories = shopping_list.get_items_by_category()
        for category, items in categories.items():
            lines.append(f"{category.upper()}:")
            for item in items:
                lines.append(f"  • {item.ingredient_name}: {item.total_quantity:g} {item.unit}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _render_shared_collections(self, current_user: User) -> None:
        """Render shared collections discovery interface"""
        st.header("🔗 Shared Collections")
        
        # Access collection by share token
        st.subheader("🔑 Access Shared Collection")
        share_token = st.text_input("Enter Share Token", placeholder="Paste collection share link or token here")
        
        if share_token and st.button("🔍 Load Collection"):
            # Clean up token if it's a full URL
            if "token=" in share_token:
                share_token = share_token.split("token=")[-1]
            
            shared_collection = self.collection_service.get_collection_by_share_token(share_token)
            
            if shared_collection:
                st.success(f"✅ Found collection: '{shared_collection.name}'")
                
                # Display shared collection
                with st.container():
                    st.markdown(f"### 📚 {shared_collection.name}")
                    st.markdown(f"**Description:** {shared_collection.description}")
                    st.markdown(f"**Recipes:** {shared_collection.get_recipe_count()}")
                    
                    # Option to view recipes
                    if st.button("👁️ View Recipes"):
                        st.session_state[self.CURRENT_COLLECTION_KEY] = shared_collection.id
                        st.rerun()
            else:
                st.error("❌ Collection not found or token is invalid")
        
        # Browse public collections
        st.subheader("🌍 Browse Public Collections")
        public_collections = self.collection_service.get_user_collections(
            current_user.id, include_public=True
        )
        
        # Filter to only public collections from other users
        public_collections = [c for c in public_collections if c.is_public and c.user_id != current_user.id]
        
        if public_collections:
            st.markdown(f"Found {len(public_collections)} public collections:")
            
            for collection in public_collections:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**📚 {collection.name}**")
                        st.markdown(f"*{collection.description}*")
                        st.markdown(f"📖 {collection.get_recipe_count()} recipes")
                        
                        if collection.tags:
                            tags_display = " ".join([f"`{tag}`" for tag in collection.tags])
                            st.markdown(f"🏷️ {tags_display}")
                    
                    with col2:
                        if st.button("👁️ View", key=f"view_public_{collection.id}"):
                            st.session_state[self.CURRENT_COLLECTION_KEY] = collection.id
                            st.session_state[self.EDIT_MODE_KEY] = False
                            st.rerun()
                
                st.divider()
        else:
            st.info("🌟 No public collections available yet. Create and share your own!")
    
    def _render_sharing_interface(self, collection: Collection, current_user: User) -> None:
        """Render collection sharing interface"""
        with st.container():
            st.markdown("### 🔗 Share Collection")
            
            if collection.share_token:
                # Collection is already shared
                st.success("✅ Collection is currently shared")
                
                # Generate share URL (in real app, this would use the actual domain)
                share_url = f"https://panscookbook.app/shared?token={collection.share_token}"
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.text_input("Share Link", value=share_url, key=f"share_url_{collection.id}")
                
                with col2:
                    if st.button("📋 Copy"):
                        st.info("📋 Link copied! (manual copy required)")
                
                # Revoke sharing option
                if st.button("🚫 Stop Sharing", key=f"revoke_{collection.id}"):
                    success = self.collection_service.revoke_share_token(collection.id, current_user.id)
                    if success:
                        st.success("✅ Sharing disabled")
                        st.session_state.pop(self.SHOW_SHARING_KEY, None)
                        st.rerun()
            else:
                # Collection is not shared
                st.info("🔒 Collection is currently private")
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    if st.button("🔗 Generate Share Link", type="primary"):
                        token = self.collection_service.generate_share_token(collection.id, current_user.id)
                        if token:
                            st.success("✅ Share link generated!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to generate share link")
                
                with col2:
                    if st.button("❌ Cancel"):
                        st.session_state.pop(self.SHOW_SHARING_KEY, None)
                        st.rerun()
    
    def render_collections_sidebar(self, current_user: User) -> Optional[Collection]:
        """Render collections sidebar for quick access"""
        if not current_user:
            return None
        
        st.sidebar.markdown("### 📚 Collections")
        
        # Get user's favorite collection
        favorite = self.collection_service.get_favorite_collection(current_user.id)
        
        if favorite:
            st.sidebar.markdown(f"⭐ **{favorite.name}**")
            st.sidebar.markdown(f"📖 {favorite.get_recipe_count()} recipes")
            
            if st.sidebar.button("👁️ View Favorite"):
                return favorite
        
        # Quick collection selector
        collections = self.collection_service.get_user_collections(current_user.id)[:5]  # Top 5
        
        if collections:
            collection_names = ["Select a collection..."] + [c.name for c in collections]
            selected_name = st.sidebar.selectbox("Quick Access", collection_names)
            
            if selected_name != "Select a collection...":
                selected_collection = next(c for c in collections if c.name == selected_name)
                return selected_collection
        
        # Quick actions
        if st.sidebar.button("➕ New Collection"):
            st.switch_page("collections")
        
        return None
    
    def _inject_custom_css(self):
        """Inject custom CSS styling for collections interface"""
        st.markdown("""
        <style>
            .collection-card {
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 1.5rem;
                margin: 1rem 0;
                background-color: #fafafa;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .collection-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
            }
            
            .collection-stats {
                display: flex;
                gap: 1rem;
                margin: 0.5rem 0;
            }
            
            .stat-badge {
                background-color: #e3f2fd;
                color: #1976d2;
                padding: 0.25rem 0.5rem;
                border-radius: 6px;
                font-size: 0.9rem;
            }
            
            .favorite-collection {
                border-left: 4px solid #ffd700;
            }
            
            .public-collection {
                border-left: 4px solid #4caf50;
            }
            
            .shopping-list-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.5rem;
                margin: 0.25rem 0;
                background-color: white;
                border-radius: 6px;
                border-left: 3px solid #2196f3;
            }
            
            .shopping-category {
                background-color: #f5f5f5;
                padding: 1rem;
                border-radius: 8px;
                margin: 0.5rem 0;
            }
            
            .share-interface {
                background-color: #e8f5e8;
                padding: 1rem;
                border-radius: 8px;
                border: 1px solid #4caf50;
                margin: 1rem 0;
            }
            
            .collection-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.5);
                z-index: 1000;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            
            .modal-content {
                background-color: white;
                padding: 2rem;
                border-radius: 12px;
                max-width: 800px;
                max-height: 80vh;
                overflow-y: auto;
            }
        </style>
        """, unsafe_allow_html=True)


def create_collections_interface(collection_service: Optional[CollectionService] = None) -> CollectionsInterface:
    """Factory function to create collections interface"""
    return CollectionsInterface(collection_service)