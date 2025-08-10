
import streamlit as st
from pathlib import Path
import pandas as pd
from database import (
    Herb, Recipe, initialize_database, load_herbs_from_db, 
    load_recipes_from_db, get_database_stats
)

# --- Database Management ---
# Data classes and database functions are imported from database.py

# --- Database Initialization ---

def ensure_database_exists():
    """Ensure the database exists and is initialized"""
    if not Path("herbalism.db").exists():
        st.info("🔧 Initializing database from CSV files...")
        initialize_database()
        st.success("✅ Database initialized successfully!")
        st.rerun()

# --- Core Application Logic & UI ---

st.set_page_config(page_title="Herbal Alchemy", layout="wide")

# --- Aesthetic Considerations (CSS) ---
st.markdown("""
<style>
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #4A7C59;
        color: white;
    }
    .owned-ingredient {
        color: #2E7D32;
        font-weight: bold;
        background-color: #E8F5E9;
        padding: 2px 6px;
        border-radius: 4px;
        border: 1px solid #A5D6A7;
    }
    .missing-ingredient {
        color: #C62828;
        text-decoration: line-through;
        background-color: #FFEBEE;
        padding: 2px 6px;
        border-radius: 4px;
        border: 1px solid #EF9A9A;
    }
    .craft-status-can-make {
        color: #1B5E20;
        font-weight: bold;
    }
    .craft-status-missing {
        color: #B71C1C;
        font-weight: bold;
    }
    .field-label {
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- Main Page Layout ---
st.title("🌿 Herbal Alchemy: Your Crafting Guide")
st.markdown("Select the herbs you have on hand to discover the recipes you can craft.")

# --- Data Loading and Initialization ---
ensure_database_exists()

# Add cache clearing and database management buttons
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("🔄 Clear Cache"):
        st.cache_data.clear()
        st.rerun()

with col2:
    if st.button("🔧 Rebuild DB"):
        if Path("herbalism.db").exists():
            Path("herbalism.db").unlink()
        initialize_database()
        st.cache_data.clear()
        st.rerun()

# Load data from SQLite database
all_herbs = load_herbs_from_db()
all_recipes = load_recipes_from_db()
HERB_MAP = {h.id: h for h in all_herbs}

# Debug info with database stats
db_stats = get_database_stats()
st.sidebar.write(f"📊 Database: {db_stats['herbs']} herbs, {db_stats['recipes']} recipes")
st.sidebar.write(f"💾 Size: {db_stats['db_size_mb']} MB")

# Debug section for selected recipe
if st.sidebar.checkbox("🔧 Debug Mode"):
    if 'selected_recipe' in st.session_state:
        st.sidebar.success(f"✅ Recipe selected: {st.session_state['selected_recipe'].name}")
        st.sidebar.write(f"ID: {st.session_state['selected_recipe'].id}")
    else:
        st.sidebar.info("No recipe currently selected")

# --- "My Herbs" Selection Area ---
# Handle herbs with missing symbols
herb_display_map = {}
for h in all_herbs:
    symbol = h.symbol if h.symbol and h.symbol.strip() else "🌿"
    display_name = f"{symbol} {h.name}"
    herb_display_map[display_name] = h

st.sidebar.header("My Herb Pouch")
selected_herb_display_names = st.sidebar.multiselect(
    "Select the herbs you possess:",
    options=sorted(herb_display_map.keys())
)

# Get the set of IDs for the herbs the user owns
owned_herb_objects = [herb_display_map[name] for name in selected_herb_display_names]
owned_herb_ids = {h.id for h in owned_herb_objects}

# --- Recipe Browser ---
st.sidebar.markdown("---")
st.sidebar.header("📜 Recipe Browser")

if all_recipes:
    # Create recipe dropdown with simplified display names (no parentheses)
    recipe_options = ["-- Select a recipe to view --"] + [f"{recipe.name} - {recipe.category}" for recipe in all_recipes]
    
    # Use a try-except block to handle potential rendering issues
    try:
        selected_recipe_display = st.sidebar.selectbox(
            "Browse all recipes:",
            options=recipe_options,
            key="recipe_browser"
        )
    except Exception as e:
        st.sidebar.error(f"Error loading recipe browser: {str(e)}")
        selected_recipe_display = "-- Select a recipe to view --"
    
    if selected_recipe_display != "-- Select a recipe to view --":
        # Find the selected recipe (format: "Recipe Name - Category")
        recipe_name = selected_recipe_display.split(" - ")[0]
        selected_recipe = next((r for r in all_recipes if r.name == recipe_name), None)
        
        if selected_recipe:
            st.session_state['selected_recipe'] = selected_recipe
            st.sidebar.success(f"📖 Viewing: {recipe_name}")
else:
    st.sidebar.info("No recipes available in database")

# --- Herb-Recipe Connections ---
st.sidebar.header("🌿➡️📜 Herb Connections")

if all_herbs:
    try:
        herb_options = ["-- Select herb --"] + [f"{herb.symbol} {herb.name}" for herb in all_herbs[:50]]  # Limit for performance
        selected_herb_for_recipes = st.sidebar.selectbox(
            "See recipes using this herb:",
            options=herb_options,
            key="herb_recipe_lookup"
        )
    except Exception as e:
        st.sidebar.error(f"Error loading herb browser: {str(e)}")
        selected_herb_for_recipes = "-- Select herb --"
    
    if selected_herb_for_recipes != "-- Select herb --":
        # Find recipes containing this herb
        herb_name = selected_herb_for_recipes.split(" ", 1)[1]
        selected_herb_obj = next((h for h in all_herbs if h.name == herb_name), None)
        
        if selected_herb_obj:
            # Find recipes using this herb
            recipes_with_herb = [r for r in all_recipes if selected_herb_obj.id in r.required_herb_ids]
            
            if recipes_with_herb:
                st.sidebar.success(f"🌿 {herb_name} is used in {len(recipes_with_herb)} recipe(s):")
                
                # Show recipes with herb availability status
                for recipe in recipes_with_herb[:5]:  # Show up to 5 recipes
                    missing_for_recipe = recipe.required_herb_ids - owned_herb_ids
                    
                    if len(missing_for_recipe) == 0:
                        status_emoji = "✅"  # Can make
                        status_text = "Can make!"
                    elif len(missing_for_recipe) < len(recipe.required_herb_ids):
                        status_emoji = "⚠️"   # Partially available
                        status_text = f"Missing {len(missing_for_recipe)} herbs"
                    else:
                        status_emoji = "❌"  # Cannot make
                        status_text = "Need more herbs"
                    
                    button_label = f"{status_emoji} {recipe.name}"
                    
                    if st.sidebar.button(button_label, key=f"herb_recipe_conn_{recipe.id}_{selected_herb_obj.id}"):
                        st.session_state['selected_recipe'] = recipe
                        st.rerun()
                        
                if len(recipes_with_herb) > 5:
                    st.sidebar.info(f"...and {len(recipes_with_herb) - 5} more recipes")
            else:
                st.sidebar.info(f"🌿 {herb_name} is not used in any recipes yet")
else:
    st.sidebar.info("No herbs available in database")

# --- Herb Information Display ---
if owned_herb_objects:
    # Show info for the most recently selected herb (last in the list)
    featured_herb = owned_herb_objects[-1]
    
    st.header("🌿 Herb Information")
    
    # Create an attractive info box
    with st.container():
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown(f"<div style='font-size: 4em; text-align: center;'>{featured_herb.symbol}</div>", 
                       unsafe_allow_html=True)
        
        with col2:
            st.subheader(featured_herb.name)
            if featured_herb.scientific_name:
                st.markdown(f"*{featured_herb.scientific_name}*")
            st.write(featured_herb.description)
    
    # Expandable sections for detailed information
    with st.expander("📋 Traditional Uses"):
        st.write(featured_herb.traditional_uses or "No traditional uses documented.")
    
    with st.expander("🎨 Craft & Aesthetic Uses"):
        st.write(featured_herb.craft_uses or "General potpourri and botanical craft uses.")
    
    with st.expander("🔬 Current Evidence"):
        st.write(featured_herb.current_evidence_summary or "Limited scientific evidence available.")
    
    with st.expander("⚠️ Safety Information"):
        if featured_herb.contraindications:
            st.markdown(f"**Contraindications:** {featured_herb.contraindications}")
        if featured_herb.interactions:
            st.markdown(f"**Interactions:** {featured_herb.interactions}")
        if featured_herb.toxicity_notes:
            st.markdown(f"**Toxicity Notes:** {featured_herb.toxicity_notes}")
        if not any([featured_herb.contraindications, featured_herb.interactions, featured_herb.toxicity_notes]):
            st.write("No specific safety concerns documented.")
    
    st.divider()

# --- Recipe Display Area ---
# Check if a specific recipe is selected for viewing
if 'selected_recipe' in st.session_state and st.session_state['selected_recipe'] is not None:
    selected_recipe = st.session_state['selected_recipe']
    
    # Recipe Header
    st.header(f"📖 {selected_recipe.name}")
    st.markdown(f"*Selected from Recipe Browser*")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.subheader(f"Category: {selected_recipe.category}")
        if selected_recipe.route:
            st.write(f"**Route:** {selected_recipe.route}")
    with col2:
        if selected_recipe.batch_size_value > 0:
            st.metric("Batch Size", f"{selected_recipe.batch_size_value} {selected_recipe.batch_size_unit}")
    with col3:
        if selected_recipe.shelf_life_days > 0:
            st.metric("Shelf Life", f"{selected_recipe.shelf_life_days} days")
    
    # Recipe Description
    if selected_recipe.description:
        st.write(f"**Description:** {selected_recipe.description}")
    
    # Required Herbs Analysis with Ownership Status
    required_herbs = [HERB_MAP.get(herb_id) for herb_id in selected_recipe.required_herb_ids if herb_id in HERB_MAP]
    required_herbs = [h for h in required_herbs if h]  # Filter out None values
    
    if required_herbs:
        st.subheader("🌿 Required Herbs")
        
        # Show crafting status for this recipe
        missing_herb_ids = selected_recipe.required_herb_ids - owned_herb_ids
        if len(missing_herb_ids) == 0:
            st.success("✅ You have all herbs needed to make this recipe!")
        elif len(missing_herb_ids) < len(selected_recipe.required_herb_ids):
            owned_count = len(selected_recipe.required_herb_ids) - len(missing_herb_ids)
            st.warning(f"⚠️ You have {owned_count}/{len(selected_recipe.required_herb_ids)} herbs. Missing {len(missing_herb_ids)} herbs.")
        else:
            st.error("❌ You don't have any of the required herbs for this recipe.")
        
        # Display herbs in columns with ownership status
        cols = st.columns(min(4, len(required_herbs)))
        for i, herb in enumerate(required_herbs):
            with cols[i % len(cols)]:
                # Show ownership status
                if herb.id in owned_herb_ids:
                    st.success(f"✅ {herb.symbol} **{herb.name}**")
                else:
                    st.error(f"❌ {herb.symbol} **{herb.name}**")
                
                if herb.scientific_name:
                    st.caption(f"*{herb.scientific_name}*")
                
                # Show herb details in expander
                with st.expander(f"About {herb.name}"):
                    if herb.description:
                        st.write(f"**Description:** {herb.description}")
                    if herb.traditional_uses:
                        st.write(f"**Traditional Uses:** {herb.traditional_uses}")
                    if herb.contraindications or herb.interactions or herb.toxicity_notes:
                        st.warning("⚠️ **Safety Information:**")
                        if herb.contraindications:
                            st.write(f"**Contraindications:** {herb.contraindications}")
                        if herb.interactions:
                            st.write(f"**Interactions:** {herb.interactions}")
                        if herb.toxicity_notes:
                            st.write(f"**Toxicity Notes:** {herb.toxicity_notes}")
                    
                    # Show which other recipes use this herb
                    recipes_with_this_herb = [r for r in all_recipes if herb.id in r.required_herb_ids and r.id != selected_recipe.id]
                    if recipes_with_this_herb:
                        st.write(f"**Also used in:** {', '.join([r.name for r in recipes_with_this_herb[:3]])}")
                        if len(recipes_with_this_herb) > 3:
                            st.write(f"...and {len(recipes_with_this_herb) - 3} more recipes")
                        
                        # Show buttons to view those recipes
                        for other_recipe in recipes_with_this_herb[:2]:  # Limit to 2 buttons per herb
                            if st.button(f"View {other_recipe.name}", key=f"cross_recipe_{other_recipe.id}_{herb.id}_{selected_recipe.id}"):
                                st.session_state['selected_recipe'] = other_recipe
                                st.rerun()
    
    # Recipe Content Sections (replaced tabs with expandable sections to prevent JS errors)
    with st.expander("📋 Instructions", expanded=True):
        if selected_recipe.instructions:
            # Format instructions with proper line breaks
            formatted_instructions = selected_recipe.instructions.replace('\\n', '\n')
            st.info(formatted_instructions)
        else:
            st.warning("No instructions available for this recipe")
        
        # Storage and sanitation info
        if selected_recipe.storage_instructions or selected_recipe.sanitation_level:
            st.markdown("**Preparation Notes**")
            if selected_recipe.sanitation_level:
                st.write(f"**Sanitation Level:** {selected_recipe.sanitation_level.title()}")
            if selected_recipe.storage_instructions:
                st.write(f"**Storage:** {selected_recipe.storage_instructions}")
    
    with st.expander("🌱 Benefits & Uses"):
        if selected_recipe.benefits:
            st.success(selected_recipe.benefits)
        else:
            st.info("No benefits information available")
    
    with st.expander("⚠️ Safety Information"):
        safety_info_available = any([
            selected_recipe.safety_summary,
            selected_recipe.contraindications,
            selected_recipe.interactions,
            selected_recipe.pediatric_note,
            selected_recipe.pregnancy_note
        ])
        
        if safety_info_available:
            if selected_recipe.safety_summary:
                st.warning(f"**General Safety:** {selected_recipe.safety_summary}")
            
            if selected_recipe.contraindications:
                st.error(f"**Contraindications:** {selected_recipe.contraindications}")
            
            if selected_recipe.interactions:
                st.error(f"**Drug Interactions:** {selected_recipe.interactions}")
            
            if selected_recipe.pediatric_note:
                st.warning(f"**Pediatric Considerations:** {selected_recipe.pediatric_note}")
            
            if selected_recipe.pregnancy_note:
                st.warning(f"**Pregnancy Considerations:** {selected_recipe.pregnancy_note}")
        else:
            st.info("No specific safety information documented for this recipe")
    
    # Navigation buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔙 Back to Craftable Recipes", key="back_to_craftable"):
            if 'selected_recipe' in st.session_state:
                del st.session_state['selected_recipe']
            st.rerun()
    with col2:
        if st.button("🔄 Clear Selection", key="clear_recipe_selection"):
            if 'selected_recipe' in st.session_state:
                del st.session_state['selected_recipe']
            st.rerun()
    with col3:
        if st.button("🌿 Add Herbs to Pouch", key="add_herbs_to_pouch"):
            # Add missing herbs to the selection
            missing_herbs = [HERB_MAP[herb_id] for herb_id in (selected_recipe.required_herb_ids - owned_herb_ids) if herb_id in HERB_MAP]
            if missing_herbs:
                # This would ideally update the multiselect, but Streamlit doesn't allow direct updates
                st.info(f"To make this recipe, you need: {', '.join([h.name for h in missing_herbs])}")
                st.info("Add these herbs using the 'My Herb Pouch' selector in the sidebar.")
            else:
                st.success("You already have all required herbs!")
    
    st.markdown("---")
    
    # Force a visual separator
    st.empty()
    st.empty()

# Only show Craftable Recipes header if no specific recipe is selected
if not ('selected_recipe' in st.session_state and st.session_state['selected_recipe'] is not None):
    st.header("Craftable Recipes")
else:
    st.markdown("## Browse More Recipes Below")
    st.markdown("*Or use the sidebar to select different recipes*")

if not owned_herb_ids:
    st.info("Select some herbs from your pouch on the left to see what you can make!")
else:
    # --- Recipe Filtering Logic ---
    recipes_to_display = []
    for recipe in all_recipes:
        missing_herb_ids = recipe.required_herb_ids - owned_herb_ids
        if len(missing_herb_ids) < len(recipe.required_herb_ids):
            recipes_to_display.append((recipe, missing_herb_ids))

    # Sort recipes: fully craftable first, then by fewest missing ingredients
    recipes_to_display.sort(key=lambda x: (len(x[1]), x[0].name))

    if not recipes_to_display:
        st.warning("You don't have the right combination of herbs for any known recipes. Try selecting more herbs!")
    else:
        for recipe, missing_ids in recipes_to_display:
            num_missing = len(missing_ids)

            # --- Crafting Status Indicator ---
            if num_missing == 0:
                status_text = '<span class="craft-status-can-make">CAN MAKE!</span>'
            else:
                missing_herbs = sorted([HERB_MAP[herb_id] for herb_id in missing_ids], key=lambda h: h.name)
                missing_herbs_str = ", ".join([f'<span class="missing-ingredient">{h.symbol} {h.name}</span>' for h in missing_herbs])
                status_text = f'<span class="craft-status-missing">Missing: {missing_herbs_str}</span>'

            st.subheader(f"{recipe.name} - {recipe.category}")
            st.markdown(f"**Status:** {status_text}", unsafe_allow_html=True)
            st.write(recipe.description)

            with st.expander("View Full Recipe & Ingredients"):
                # --- Required Herbs List ---
                st.markdown("##### Required Herbs:")
                required_herbs = sorted([HERB_MAP[herb_id] for herb_id in recipe.required_herb_ids], key=lambda h: h.name)
                cols = st.columns(len(required_herbs) if required_herbs else 1)
                for i, herb in enumerate(required_herbs):
                    with cols[i]:
                        if herb.id in owned_herb_ids:
                            st.markdown(f'<div style="text-align: center;"><span class="owned-ingredient">{herb.symbol} {herb.name}</span></div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div style="text-align: center;"><span class="missing-ingredient">{herb.symbol} {herb.name}</span></div>', unsafe_allow_html=True)

                st.markdown("---")
                st.markdown("##### Instructions:")
                st.info(recipe.instructions)

                st.markdown("##### Benefits:")
                st.success(recipe.benefits)

                # --- Safety Section ---
                if recipe.safety_summary or recipe.contraindications or recipe.interactions:
                    st.markdown("##### Safety")
                    if recipe.safety_summary:
                        st.warning(recipe.safety_summary)
                    with st.expander("Contraindications, Interactions & Special Populations"):
                        if recipe.contraindications:
                            st.markdown(f"<span class='field-label'>Contraindications:</span> {recipe.contraindications}", unsafe_allow_html=True)
                        if recipe.interactions:
                            st.markdown(f"<span class='field-label'>Interactions:</span> {recipe.interactions}", unsafe_allow_html=True)
                        if recipe.pediatric_note:
                            st.markdown(f"<span class='field-label'>Pediatric:</span> {recipe.pediatric_note}", unsafe_allow_html=True)
                        if recipe.pregnancy_note:
                            st.markdown(f"<span class='field-label'>Pregnancy:</span> {recipe.pregnancy_note}", unsafe_allow_html=True)

                # --- Sanitation & Storage ---
                if recipe.sanitation_level or recipe.storage_instructions or recipe.shelf_life_days:
                    st.markdown("##### Sanitation & Storage")
                    if recipe.sanitation_level:
                        st.markdown(f"<span class='field-label'>Sanitation Level:</span> {recipe.sanitation_level.title()}", unsafe_allow_html=True)
                    if recipe.storage_instructions:
                        st.markdown(f"<span class='field-label'>Storage:</span> {recipe.storage_instructions}", unsafe_allow_html=True)
                    if recipe.shelf_life_days:
                        st.markdown(f"<span class='field-label'>Shelf life:</span> {int(recipe.shelf_life_days)} days", unsafe_allow_html=True)

                # --- Batch Info ---
                if recipe.batch_size_value:
                    st.markdown("##### Batch")
                    st.markdown(f"{recipe.batch_size_value} {recipe.batch_size_unit}")
                
                # --- Recipe View Button ---
                if st.button(f"📖 View Full Recipe: {recipe.name}", key=f"view_recipe_{recipe.id}"):
                    st.session_state['selected_recipe'] = recipe
                    st.rerun()
            st.markdown("---")
