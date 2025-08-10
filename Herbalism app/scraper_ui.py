"Enhanced Recipe Scraper UI with comprehensive service integration.\n\nThis updated interface leverages the new service architecture while maintaining\nthe existing Streamlit UI patterns. Provides comprehensive error display,\nprogress tracking, and detailed debugging information with no error masking.\n"\nimport streamlit as st\nimport time\nimport os\nfrom datetime import datetime\nfrom typing import Dict, Any, List\n\n# Import database functionality for comprehensive integration\nfrom database import (\n    Herb, Recipe, load_herbs_from_db, load_recipes_from_db, \n    update_recipe, delete_recipe, get_database_stats, \n    initialize_database, create_database, migrate_from_csv\n)\nfrom pathlib import Path\n\n# Import new service architecture\nfrom src.scraper.scraper_service import ScraperService\nfrom src.scraper.logger import ScraperLogger, ErrorCategory\nfrom src.scraper.models import ScrapingResult, ParsedRecipe\n\n# --- Configuration ---\nst.set_page_config(page_title="Enhanced Recipe Scraper", layout="wide")\n\n# Initialize services\n@st.cache_resource\ndef initialize_services():\n    """Initialize scraper services with caching for performance."""\n    try:\n        logger = ScraperLogger(debug_mode=True)\n        scraper_service = ScraperService()\n        return scraper_service, logger\n    except Exception as e:\n        st.error(f"Failed to initialize scraper services: {e}")\n        st.stop()\n\nscraper_service, logger = initialize_services()\n\n# --- Database Management Functions ---\n\ndef ensure_database_connectivity():\n    """\n    Ensure SQLite database is properly initialized and accessible.\n    \n    Handles database creation, migration from CSV files, and provides\n    comprehensive error feedback for database connectivity issues.\n    """\n    db_path = Path("herbalism.db")\n    \n    try:\n        # Check if database exists\n        if not db_path.exists():\n            st.info("🔧 Database not found. Initializing SQLite database...")\n            \n            # Create database schema\n            create_database()\n            st.success("✅ Database schema created successfully")\n            \n            # Check for CSV files to migrate\n            csv_files = ["herbs.csv", "recipes.csv"]\n            csv_found = [f for f in csv_files if Path(f).exists()]\n            \n            if csv_found:\n                st.info(f"📁 Found CSV files: {', '.join(csv_found)}. Migrating to database...")\n                migrate_from_csv()\n                st.success("✅ CSV data migrated to SQLite database")\n            else:\n                st.warning("⚠️ No CSV files found. Starting with empty database.")\n        \n        # Verify database connectivity\n        stats = get_database_stats()\n        return True, stats\n        \n    except Exception as e:\n        error_msg = f"❌ Database initialization failed: {str(e)}"\n        st.error(error_msg)\n        \n        # Provide detailed troubleshooting information\n        with st.expander("🔧 Database Troubleshooting"):\n            st.write("**Possible solutions:**")\n            st.write("1. Check file permissions in the current directory")\n            st.write("2. Ensure sufficient disk space")\n            st.write("3. Verify Python has write access to the directory")\n            st.write("4. Try manually deleting herbalism.db and restarting")\n            st.code(f"Error details: {e}")\n        \n        return False, None\n\ndef validate_database_transaction_consistency():\n    """\n    Validate that database transactions are working properly.\n    \n    Performs basic transaction tests to ensure the scraper service\n    can safely perform atomic operations on the database.\n    """\n    try:\n        # Test basic connectivity\n        stats = get_database_stats()\n        \n        # Test herb loading (core functionality)\n        herbs = load_herbs_from_db()\n        \n        return True, {\n            "herbs_loaded": len(herbs),\n            "database_size_mb": stats.get("db_size_mb", 0),\n            "total_herbs": stats.get("herbs", 0),\n            "total_recipes": stats.get("recipes", 0)\n        }\n        \n    except Exception as e:\n        return False, {"error": str(e)}\n\ndef display_database_management_interface():\n    """\n    Display database management and maintenance interface.\n    \n    Provides tools for database maintenance, migration, and troubleshooting\n    to ensure reliable database operations for scraper workflows.\n    """\n    st.subheader("🗄️ Database Management")\n    \n    # Database status check\n    db_ok, db_info = validate_database_transaction_consistency()\n    \n    if db_ok:\n        st.success("✅ Database operational")\n        \n        col1, col2, col3 = st.columns(3)\n        with col1:\n            st.metric("Total Herbs", db_info["total_herbs"])\n        with col2:\n            st.metric("Total Recipes", db_info["total_recipes"])\n        with col3:\n            st.metric("DB Size", f"{db_info['database_size_mb']:.1f} MB")\n    else:\n        st.error("❌ Database connectivity issues detected")\n        st.error(db_info.get("error", "Unknown database error"))\n    \n    # Database maintenance tools\n    st.markdown("---")\n    st.write("**Database Maintenance:**")\n    \n    col1, col2, col3 = st.columns(3)\n    \n    with col1:\n        if st.button("🔄 Refresh Connection"):\n            st.cache_data.clear()  # Clear Streamlit cache\n            st.rerun()\n    \n    with col2:\n        if st.button("🔧 Rebuild Database"):\n            if st.checkbox("⚠️ Confirm rebuild (will recreate from CSV if available)"):\n                try:\n                    db_path = Path("herbalism.db")\n                    if db_path.exists():\n                        db_path.unlink()\n                    \n                    initialize_database()\n                    st.success("✅ Database rebuilt successfully")\n                    st.cache_data.clear()\n                    st.rerun()\n                except Exception as e:\n                    st.error(f"Database rebuild failed: {e}")\n    \n    with col3:\n        if st.button("📊 Database Statistics"):\n            try:\n                detailed_stats = get_database_stats()\n                st.json(detailed_stats)\n            except Exception as e:\n                st.error(f"Stats unavailable: {e}")\n\n# --- Helper Functions ---\n\ndef display_comprehensive_error(result: ScrapingResult, operation_type: str):\n    """\n    Display comprehensive error information with technical details.\n    \n    Shows both user-friendly messages and detailed technical information\n    for debugging. Never hides underlying issues.\n    """\n    if not result.has_errors() and not result.has_warnings():\n        return\n    \n    # Error Summary\n    if result.has_errors():\n        st.error(f"❌ {operation_type} failed with {len(result.errors)} error(s)")\n        \n        with st.expander("📋 Error Details", expanded=True):\n            for i, error in enumerate(result.errors, 1):\n                st.error(f"**Error {i}:** {error}")\n        \n        # Technical debugging information\n        if result.debug_info:\n            with st.expander("🔧 Technical Debug Information"):\n                st.json(result.debug_info)\n    \n    # Warning Summary\n    if result.has_warnings():\n        st.warning(f"⚠️ {len(result.warnings)} warning(s) occurred")\n        \n        with st.expander("📋 Warning Details"):\n            for i, warning in enumerate(result.warnings, 1):\n                st.warning(f"**Warning {i}:** {warning}")\n\ndef display_operation_progress(operation_name: str, steps: List[str]):\n    """Display progress indicators for multi-step operations."""\n    progress_bar = st.progress(0)\n    status_text = st.empty()\n    \n    for i, step in enumerate(steps):\n        progress = (i + 1) / len(steps)\n        progress_bar.progress(progress)\n        status_text.text(f"Step {i + 1}/{len(steps)}: {step}")\n        time.sleep(0.5)  # Visual feedback\n    \n    progress_bar.progress(1.0)\n    status_text.text(f"✅ {operation_name} completed!")\n\ndef display_recipe_editor_form(recipe: Recipe, all_herbs: List[Herb]):\n    """\n    Display an editable form for an existing recipe, allowing updates and deletion.\n    """\n    st.subheader(f"Edit Recipe: {recipe.name}")\n\n    with st.form(key=f"edit_recipe_{recipe.id}"):\n        st.markdown(f"**Editing Recipe ID: {recipe.id}**")\n\n        # Basic Information Section\n        col1, col2 = st.columns([2, 1])\n        \n        with col1:\n            edited_name = st.text_input("Recipe Name *", value=recipe.name)\n            edited_description = st.text_area("Description", value=recipe.description, height=100)\n            edited_category = st.selectbox(\n                "Category *",\n                options=["Remedy", "Tincture", "Tea", "Salve", "Oil", "Shampoo", "Cosmetic", "Other"],\n                index=["Remedy", "Tincture", "Tea", "Salve", "Oil", "Shampoo", "Cosmetic", "Other"].index(recipe.category) if recipe.category in ["Remedy", "Tincture", "Tea", "Salve", "Oil", "Shampoo", "Cosmetic", "Other"] else 7\n            )\n        \n        with col2:\n            edited_route = st.selectbox(\n                "Route/Application",\n                options=["topical", "oral", "otic", "nasal", "inhalation", "bath", "other"],\n                index=["topical", "oral", "otic", "nasal", "inhalation", "bath", "other"].index(recipe.route) if recipe.route in ["topical", "oral", "otic", "nasal", "inhalation", "bath", "other"] else 0\n            )\n            edited_sanitation = st.selectbox(\n                "Sanitation Level",\n                options=["basic", "sterile", "clean", "food-grade"],\n                index=["basic", "sterile", "clean", "food-grade"].index(recipe.sanitation_level) if recipe.sanitation_level in ["basic", "sterile", "clean", "food-grade"] else 0\n            )\n\n        # Ingredients (Herbs) Section\n        st.subheader("🌿 Required Herbs")\n        st.markdown("Select the herbs required for this recipe. You can add or remove herbs here.")\n        \n        herb_map_name_to_id = {h.name: h.id for h in all_herbs}\n        herb_map_id_to_name = {h.id: h.name for h in all_herbs}\n        \n        all_herb_names = sorted(list(herb_map_name_to_id.keys()))\n        \n        selected_herb_names = [herb_map_id_to_name[herb_id] for herb_id in recipe.required_herb_ids if herb_id in herb_map_id_to_name]\n\n        edited_herb_names = st.multiselect(\n            "Select required herbs:",\n            options=all_herb_names,\n            default=selected_herb_names,\n            key=f"edit_herbs_{recipe.id}"\n        )\n\n        # Instructions Section\n        st.subheader("📋 Instructions")\n        edited_instructions = st.text_area("Preparation Instructions", value=recipe.instructions, height=200)\n        \n        # Benefits and Safety Section\n        col1, col2 = st.columns(2)\n        with col1:\n            st.subheader("🌱 Benefits & Uses")\n            edited_benefits = st.text_area("Benefits", value=recipe.benefits, height=150)\n        with col2:\n            st.subheader("⚠️ Safety Information")\n            edited_safety_summary = st.text_area("Safety Summary", value=recipe.safety_summary, height=100)\n            edited_contraindications = st.text_area("Contraindications", value=recipe.contraindications, height=60)\n            edited_interactions = st.text_area("Drug/Herb Interactions", value=recipe.interactions, height=60)\n\n        # Special Population Notes\n        col1, col2 = st.columns(2)\n        with col1:\n            edited_pediatric = st.text_area("Pediatric Notes", value=recipe.pediatric_note, height=60)\n        with col2:\n            edited_pregnancy = st.text_area("Pregnancy Notes", value=recipe.pregnancy_note, height=60)\n\n        # Storage and Batch Information\n        col1, col2, col3 = st.columns(3)\n        with col1:\n            edited_storage = st.text_area("Storage Instructions", value=recipe.storage_instructions, height=80)\n        with col2:\n            edited_shelf_life = st.number_input("Shelf Life (days)", min_value=0, max_value=3650, value=recipe.shelf_life_days)\n            edited_batch_value = st.number_input("Batch Size (amount)", min_value=0.0, value=recipe.batch_size_value, step=0.1)\n        with col3:\n            edited_batch_unit = st.text_input("Batch Unit", value=recipe.batch_size_unit)\n\n        # Action Buttons\n        st.markdown("---")\n        col1, col2, col3 = st.columns([2, 1, 1])\n        with col1:\n            update_button = st.form_submit_button("💾 Update Recipe", type="primary")\n        with col2:\n            delete_button = st.form_submit_button("🗑️ Delete Recipe")\n        with col3:\n            cancel_button = st.form_submit_button("❌ Cancel")\n\n    if update_button:\n        selected_herb_ids = {herb_map_name_to_id[name] for name in edited_herb_names}\n        \n        updated_recipe_obj = Recipe(\n            id=recipe.id,\n            name=edited_name,\n            description=edited_description,\n            instructions=edited_instructions,\n            benefits=edited_benefits,\n            category=edited_category,\n            required_herb_ids=selected_herb_ids,\n            route=edited_route,\n            safety_summary=edited_safety_summary,\n            contraindications=edited_contraindications,\n            interactions=edited_interactions,\n            pediatric_note=edited_pediatric,\n            pregnancy_note=edited_pregnancy,\n            sanitation_level=edited_sanitation,\n            storage_instructions=edited_storage,\n            shelf_life_days=edited_shelf_life,\n            batch_size_value=edited_batch_value,\n            batch_size_unit=edited_batch_unit\n        )\n\n        try:\n            update_recipe(updated_recipe_obj)\n            st.success(f"✅ Recipe '{updated_recipe_obj.name}' updated successfully!")\n            st.info("Clearing cache to reflect changes...")\n            st.cache_data.clear()\n            if 'selected_recipe_to_edit' in st.session_state:\n                del st.session_state['selected_recipe_to_edit']\n            st.rerun()\n        except Exception as e:\n            st.error(f"❌ Failed to update recipe: {e}")\n\n    if delete_button:\n        st.session_state.confirm_delete = True\n\n    if 'confirm_delete' in st.session_state and st.session_state.confirm_delete:\n        st.warning(f"**⚠️ Are you sure you want to delete the recipe '{recipe.name}'?** This action cannot be undone.")\n        col1, col2 = st.columns(2)\n        with col1:\n            if st.button("YES, DELETE IT", type="primary"):\n                try:\n                    delete_recipe(recipe.id)\n                    st.success(f"✅ Recipe '{recipe.name}' has been deleted.")\n                    st.info("Clearing cache to reflect changes...")\n                    st.cache_data.clear()\n                    del st.session_state.confirm_delete\n                    if 'selected_recipe_to_edit' in st.session_state:\n                        del st.session_state['selected_recipe_to_edit']\n                    st.rerun()\n                except Exception as e:\n                    st.error(f"❌ Failed to delete recipe: {e}")\n        with col2:\n            if st.button("NO, CANCEL"):\n                del st.session_state.confirm_delete\n                st.rerun()\n\n    if cancel_button:\n        if 'selected_recipe_to_edit' in st.session_state:\n            del st.session_state['selected_recipe_to_edit']\n        if 'confirm_delete' in st.session_state:\n            del st.session_state.confirm_delete\n        st.rerun()\n\ndef process_unknown_herbs(unknown_herbs: List[str]):\n    """\n    Extract information for unknown herbs and add them to the database.\n    """\n    if not unknown_herbs:\n        return\n\n    st.info(f"🔍 Processing {len(unknown_herbs)} new herbs...")\n    \n    with st.expander("🌿 New Herb Creation Progress", expanded=True):\n        for herb_name in unknown_herbs:\n            with st.spinner(f"Researching and adding '{herb_name}'..."):\n                try:\n                    # Extract and validate herb info\n                    herb_data, warnings = scraper_service.extract_and_validate_herb(herb_name)\n                    \n                    if not herb_data:\n                        st.error(f"❌ Failed to extract information for '{herb_name}'.")\n                        for warning in warnings:\n                            st.warning(warning)\n                        continue\n\n                    # Save to database\n                    herb_id = scraper_service.db_service.create_herb_if_not_exists(herb_data)\n                    if herb_id:\n                        st.success(f"✅ Successfully added '{herb_name}' to the database.")\n                    else:\n                        st.error(f"❌ Failed to save '{herb_name}' to the database.")\n\n                except Exception as e:\n                    st.error(f"❌ An error occurred while processing '{herb_name}': {e}")\n\ndef display_recipe_preview_form(parsed_data: Dict[str, Any]):\n    """\n    Display editable recipe preview form for user approval before saving to database.\n    """\n    st.markdown("---")\n    st.header("📝 Recipe Preview & Approval")\n    st.markdown("**Please review the AI-parsed recipe data below and make any necessary corrections before saving to database.**")\n    \n    recipe = parsed_data['recipe']\n    \n    with st.form(key="recipe_approval_form"):\n        st.subheader("🔍 Parsed Recipe Data")\n        \n        # Basic Information Section\n        col1, col2 = st.columns([2, 1])\n        \n        with col1:\n            edited_name = st.text_input(\n                "Recipe Name *",\n                value=recipe.name or ""
            )\n            \n            edited_description = st.text_area(\n                "Description",\n                value=recipe.description or "",\n                height=100,\n                help="Brief description of what this recipe is for"
            )\n            \n            edited_category = st.selectbox(\n                "Category *",\n                options=["Remedy", "Tincture", "Tea", "Salve", "Oil", "Shampoo", "Cosmetic", "Other"],\n                index=0 if not recipe.category else (\n                    ["Remedy", "Tincture", "Tea", "Salve", "Oil", "Shampoo", "Cosmetic", "Other"].index(recipe.category)\n                    if recipe.category in ["Remedy", "Tincture", "Tea", "Salve", "Oil", "Shampoo", "Cosmetic", "Other"]\n                    else len(["Remedy", "Tincture", "Tea", "Salve", "Oil", "Shampoo", "Cosmetic", "Other"]) - 1\n                ),\n                help="Required field - recipe category"
            )\n        \n        with col2:\n            edited_route = st.selectbox(\n                "Route/Application",\n                options=["topical", "oral", "otic", "nasal", "inhalation", "bath", "other"],\n                index=0 if not recipe.route else (\n                    ["topical", "oral", "otic", "nasal", "inhalation", "bath", "other"].index(recipe.route)\n                    if recipe.route in ["topical", "oral", "otic", "nasal", "inhalation", "bath", "other"]\n                    else 0\n                ),\n                help="How is this recipe applied/used?"
            )\n            \n            edited_sanitation = st.selectbox(\n                "Sanitation Level",\n                options=["basic", "sterile", "clean", "food-grade"],\n                index=0 if not recipe.sanitation_level else (\n                    ["basic", "sterile", "clean", "food-grade"].index(recipe.sanitation_level)\n                    if recipe.sanitation_level in ["basic", "sterile", "clean", "food-grade"]\n                    else 0\n                ),\n                help="Level of cleanliness required"
            )\n        \n        # Instructions Section\n        st.subheader("📋 Instructions")\n        edited_instructions = st.text_area(\n            "Preparation Instructions",\n            value=recipe.instructions or "",\n            height=200,\n            help="Step-by-step preparation instructions"
        )\n        \n        # Benefits and Safety Section\n        col1, col2 = st.columns(2)\n        \n        with col1:\n            st.subheader("🌱 Benefits & Uses")\n            edited_benefits = st.text_area(\n                "Benefits",\n                value=recipe.benefits or "",\n                height=150,\n                help="What benefits does this recipe provide?"
            )\n        \n        with col2:\n            st.subheader("⚠️ Safety Information")\n            edited_safety_summary = st.text_area(\n                "Safety Summary",\n                value=recipe.safety_summary or "",\n                height=100,\n                help="General safety notes and precautions"
            )\n            \n            edited_contraindications = st.text_area(\n                "Contraindications",\n                value=recipe.contraindications or "",\n                height=60,\n                help="When NOT to use this recipe"
            )\n            \n            edited_interactions = st.text_area(\n                "Drug/Herb Interactions",\n                value=recipe.interactions or "",\n                height=60,\n                help="Known interactions with medications or other herbs"
            )\n        \n        # Special Population Notes\n        col1, col2 = st.columns(2)\n        with col1:\n            edited_pediatric = st.text_area(\n                "Pediatric Notes",\n                value=recipe.pediatric_note or "",\n                height=60,\n                help="Special considerations for children"
            )\n        with col2:\n            edited_pregnancy = st.text_area(\n                "Pregnancy Notes", \n                value=recipe.pregnancy_note or "",\n                height=60,\n                help="Special considerations during pregnancy/nursing"
            )\n        \n        # Storage and Batch Information\n        col1, col2, col3 = st.columns(3)\n        \n        with col1:\n            edited_storage = st.text_area(\n                "Storage Instructions",\n                value=recipe.storage_instructions or "",\n                height=80,\n                help="How to properly store this recipe"
            )\n        \n        with col2:\n            edited_shelf_life = st.number_input(\n                "Shelf Life (days)",\n                min_value=0,\n                max_value=3650,\n                value=int(recipe.shelf_life_days) if recipe.shelf_life_days else 0,\n                help="How long does this recipe last?"
            )\n            \n            edited_batch_value = st.number_input(\n                "Batch Size (amount)",\n                min_value=0.0,\n                value=float(recipe.batch_size_value) if recipe.batch_size_value else 0.0,\n                step=0.1,\n                help="How much does this recipe make?"
            )\n        \n        with col3:\n            edited_batch_unit = st.text_input(\n                "Batch Unit",\n                value=recipe.batch_size_unit or "",\n                help="Unit of measurement (cups, ounces, ml, etc.)"
            )\n        \n        # Ingredients Preview\n        if recipe.ingredients:\n            st.subheader("🌿 Detected Ingredients")\n            st.info("The following ingredients were detected in the recipe. These will be matched to herbs in your database.")\n            \n            ingredient_cols = st.columns(min(3, len(recipe.ingredients)))\n            for i, ingredient in enumerate(recipe.ingredients):\n                with ingredient_cols[i % len(ingredient_cols)]:\n                    st.write(f"• {ingredient}")\n        \n        # Editable Unknown Herbs\n        st.subheader("❓ Unknown Herbs to Add")\n        st.markdown("Review and edit the list of new herbs to be added to the database.")\n        unknown_herbs_text = st.text_area(\n            "New Herbs (one per line):",\n            value="\n".join(recipe.unknown_herbs),\n            height=150,\n            key="unknown_herbs_editor"
        )\n        \n        # AI Parsing Quality Assessment\n        ai_result = parsed_data.get('ai_result')\n        if ai_result and hasattr(ai_result, 'confidence_score'):\n            st.subheader("🤖 AI Parsing Assessment")\n            \n            col1, col2, col3 = st.columns(3)\n            with col1:\n                st.metric("Confidence Score", f"{ai_result.confidence_score:.0%}")\n            with col2:\n                st.metric("Fields Parsed", f"{ai_result.completeness_score:.0%}")\n            with col3:\n                repair_attempts = getattr(ai_result, 'repair_attempts', 0)\n                st.metric("JSON Repairs", repair_attempts)\n                if repair_attempts > 0:\n                    st.caption("⚠️ JSON required repair")\n        \n        # Source Information\n        with st.expander("📄 Source Information"):\n            st.write(f"**Source URL:** {parsed_data.get('source_url', 'Unknown')}")\n            st.write(f"**Content Length:** {len(parsed_data.get('page_text', ''))} characters")\n            st.write(f"**Parsed At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")\n        \n        # Action Buttons\n        st.markdown("---")\n        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])\n        \n        with col1:\n            approve_button = st.form_submit_button(\n                "✅ Approve & Save Recipe",\n                type="primary",\n                help="Save this recipe to your database"
            )\n        \n        with col2:\n            reject_button = st.form_submit_button(\n                "❌ Reject Recipe",\n                help="Discard this recipe and start over"
            )\n        \n        with col3:\n            reparse_button = st.form_submit_button(\n                "🔄 Re-parse Content",\n                help="Try parsing the content again with AI"
            )\n            \n        with col4:\n            edit_source_button = st.form_submit_button(\n                "📝 Edit Source Text",\n                help="Manually edit the source content before re-parsing"
            )\n    \n    # Handle form submissions\n    if approve_button:\n        # Parse the edited unknown herbs from the text area\n        edited_unknown_herbs = [line.strip() for line in unknown_herbs_text.split('\n') if line.strip()]\n\n        # Create updated recipe object with user edits\n        \n        updated_recipe = ParsedRecipe(\n            name=edited_name,\n            description=edited_description,\n            instructions=edited_instructions,\n            benefits=edited_benefits,\n            category=edited_category,\n            route=edited_route,\n            safety_summary=edited_safety_summary,\n            contraindications=edited_contraindications,\n            interactions=edited_interactions,\n            pediatric_note=edited_pediatric,\n            pregnancy_note=edited_pregnancy,\n            sanitation_level=edited_sanitation,\n            storage_instructions=edited_storage,\n            shelf_life_days=edited_shelf_life,\n            batch_size_value=edited_batch_value,\n            batch_size_unit=edited_batch_unit,\n            ingredients=recipe.ingredients,\n            unknown_herbs=edited_unknown_herbs
        )\n        \n        # Validate required fields\n        if not updated_recipe.name or not updated_recipe.category:\n            st.error("❌ Recipe name and category are required fields!")\n            return\n        \n        # Save to database using scraper service\n        with st.spinner("Saving recipe to database..."):\n            try:\n                # Process the updated recipe through the database service\n                db_result = scraper_service.db_service.save_recipe_with_herbs(\n                    updated_recipe, \n                    []  # No new herbs yet - will be processed separately
                )\n                \n                if db_result.success:\n                    st.success(f"✅ Recipe successfully saved with ID {db_result.new_record_id}!")\n                    \n                    # Clear the session state to allow new recipes\n                    del st.session_state.parsed_recipe_data\n                    \n                    # Show success details\n                    with st.expander("📊 Save Results"):\n                        st.json({\n                            "recipe_id": db_result.new_record_id,\n                            "affected_rows": db_result.affected_rows,\n                            "timestamp": datetime.now().isoformat()
                        })\n                    \n                    st.info("💡 **Important:** To see the new recipe in the Recipe Finder, please go to that app and click the 'Clear Cache' button.")\n                        \n                    # Process unknown herbs if any\n                    if updated_recipe.unknown_herbs:\n                        process_unknown_herbs(updated_recipe.unknown_herbs)\n                        \n                else:\n                    st.error("❌ Failed to save recipe to database")\n                    for error in db_result.errors:\n                        st.error(f"Database error: {error}")\n                    \n            except Exception as e:\n                st.error(f"❌ Error saving recipe: {str(e)}")\n    \n    elif reject_button:\n        # Clear session state and allow user to start over\n        del st.session_state.parsed_recipe_data\n        st.success("Recipe discarded. You can now scrape a new recipe.")\n        st.rerun()\n    \n    elif reparse_button:\n        # Re-parse the same content\n        with st.spinner("Re-parsing content..."):\n            ai_result = scraper_service.ai_service.parse_recipe(\n                parsed_data['page_text'], \n                parsed_data['source_url']
            )\n            \n            if ai_result.success and ai_result.parsed_data:\n                # Convert parsed data to ParsedRecipe object
                recipe_data = ai_result.parsed_data
                
                recipe = ParsedRecipe(
                    name=recipe_data.get("name", ""),
                    description=recipe_data.get("description", ""),
                    instructions=recipe_data.get("instructions", ""),
                    benefits=recipe_data.get("benefits", ""),
                    category=recipe_data.get("category", ""),
                    route=recipe_data.get("route", ""),
                    safety_summary=recipe_data.get("safety_summary", ""),
                    contraindications=recipe_data.get("contraindications", ""),
                    interactions=recipe_data.get("interactions", ""),
                    pediatric_note=recipe_data.get("pediatric_note", ""),
                    pregnancy_note=recipe_data.get("pregnancy_note", ""),
                    sanitation_level=recipe_data.get("sanitation_level", ""),
                    storage_instructions=recipe_data.get("storage_instructions", ""),
                    shelf_life_days=int(recipe_data.get("shelf_life_days", 0)),
                    batch_size_value=float(recipe_data.get("batch_size_value", 0.0)),
                    batch_size_unit=recipe_data.get("batch_size_unit", ""),
                    ingredients=recipe_data.get("ingredients", []),
                    unknown_herbs=recipe_data.get("unknown_herbs", [])
                )
                
                st.session_state.parsed_recipe_data['recipe'] = recipe
                st.session_state.parsed_recipe_data['ai_result'] = ai_result
                st.success("✅ Content re-parsed successfully!")
                st.rerun()
            else:
                st.error("❌ Re-parsing failed")
    
    elif edit_source_button:
        # Show text editor for manual content editing
        st.subheader("📝 Edit Source Content")
        edited_content = st.text_area(
            "Edit the source content and then re-parse:",
            value=parsed_data['page_text'],
            height=300
        )
        
        if st.button("🔄 Parse Edited Content"):
            with st.spinner("Parsing edited content..."):
                ai_result = scraper_service.ai_service.parse_recipe(
                    edited_content, 
                    parsed_data['source_url']
                )
                
                if ai_result.success and ai_result.parsed_data:
                    # Convert parsed data to ParsedRecipe object
                    recipe_data = ai_result.parsed_data
                    
                    recipe = ParsedRecipe(
                        name=recipe_data.get("name", ""),
                        description=recipe_data.get("description", ""),
                        instructions=recipe_data.get("instructions", ""),
                        benefits=recipe_data.get("benefits", ""),
                        category=recipe_data.get("category", ""),
                        route=recipe_data.get("route", ""),
                        safety_summary=recipe_data.get("safety_summary", ""),
                        contraindications=recipe_data.get("contraindications", ""),
                        interactions=recipe_data.get("interactions", ""),
                        pediatric_note=recipe_data.get("pediatric_note", ""),
                        pregnancy_note=recipe_data.get("pregnancy_note", ""),
                        sanitation_level=recipe_data.get("sanitation_level", ""),
                        storage_instructions=recipe_data.get("storage_instructions", ""),
                        shelf_life_days=int(recipe_data.get("shelf_life_days", 0)),
                        batch_size_value=float(recipe_data.get("batch_size_value", 0.0)),
                        batch_size_unit=recipe_data.get("batch_size_unit", ""),
                        ingredients=recipe_data.get("ingredients", []),
                        unknown_herbs=recipe_data.get("unknown_herbs", [])
                    )
                    
                    st.session_state.parsed_recipe_data['recipe'] = recipe
                    st.session_state.parsed_recipe_data['ai_result'] = ai_result
                    st.success("✅ Edited content parsed successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to parse edited content")

# --- Main UI ---\n\nst.title("🌿 Enhanced Herbal Recipe Scraper")\nst.markdown("""
An intelligent recipe scraper with comprehensive error handling, herb discovery, 
and seamless database integration. All operations provide detailed feedback 
and debugging information.
""", unsafe_allow_html=True)



\nst.markdown("---")\nst.markdown("### 🚀 Scraper Operations")\nst.markdown("Use the tabs below to scrape new recipes or manage your database.")\n\n# --- Database Initialization ---\n# Ensure database is properly set up before proceeding\ndb_ready, db_stats = ensure_database_connectivity()\n\nif not db_ready:\n    st.error("🚫 Database setup required before scraper can function")\n    st.stop()\n\n# --- Sidebar Configuration ---\nwith st.sidebar:\n    st.header("⚙️ Configuration")\n    \n    # Enhanced Database Status\n    st.subheader("🗄️ Database Status")\n    \n    # Perform comprehensive database validation\n    db_validation_ok, db_validation_info = validate_database_transaction_consistency()\n    \n    if db_validation_ok:\n        st.success("✅ Database Operational")\n        col1, col2 = st.columns(2)\n        with col1:\n            st.metric("Herbs", db_validation_info["total_herbs"])\n        with col2:\n            st.metric("Recipes", db_validation_info["total_recipes"])\n        \n        # Transaction consistency indicator\n        st.write(f"💾 {db_validation_info['database_size_mb']:.1f} MB")\n        \n        # Test database service integration\n        try:\n            # Quick test of scraper service database integration\n            test_herbs = scraper_service.db_service.get_herbs_by_names(["test_herb"])\n            st.success("🔗 Scraper DB Integration: OK")\n        except Exception as e:\n            st.warning(f"⚠️ Scraper DB Integration: {str(e)[:50]}...")\n    else:\n        st.error("❌ Database Issues Detected")\n        st.error(db_validation_info.get("error", "Unknown error"))\n        \n        # Quick fix options\n        if st.button("🔧 Quick Fix Database"):\n            try:\n                st.cache_data.clear()\n                st.rerun()\n            except Exception:\n                st.error("Manual intervention required")\n    \n\n    \n    # LM Studio Status\n    st.info("🤖 LM Studio: Please ensure server is running at localhost:1234")\n    \n    # Operation Statistics\n    st.subheader("📈 Operation Statistics")\n    try:\n        stats = scraper_service.get_operation_statistics()\n        if stats.get("total_operations", 0) > 0:\n            st.metric("Total Operations", stats["total_operations"])\n            st.metric("Success Rate", f"{stats['success_rate']:.1%}")\n            st.metric("Recipes Created", stats["total_recipes_created"])\n            st.metric("Herbs Created", stats["total_herbs_created"])\n        else:\n            st.info("No operations yet")\n    except Exception as e:\n        st.warning(f"Statistics unavailable: {e}")\n\n# --- Main Interface Tabs ---\ntab_url, tab_text, tab_manage_recipes, tab_database, tab_debug = st.tabs([\n    "🌐 Scrape from URL", \n    "📝 Paste Recipe Text", \n    "✏️ Manage Recipes",\n    "🗄️ Database Management",\n    "🔧 Debug & Monitoring"
])\n\n# --- URL Scraping Tab ---\nwith tab_url:\n    st.subheader("Scrape Recipe from URL")\n    \n    url = st.text_input(\n        "Enter the URL of a recipe:",\n        placeholder="https://example.com/herbal-remedy",\n        help="Ensure the URL contains a single, well-structured herbal recipe"
    )\n\n    col1, col2 = st.columns([3, 1])\n    \n    with col1:\n        scrape_button = st.button("🚀 Scrape Recipe", type="primary")\n    \n    with col2:\n        if st.button("🔍 Preview URL"):\n            if url:\n                with st.spinner("Fetching preview..."):\n                    try:\n                        # Use scraper service for consistent behavior\n                        page_text, main_found = scraper_service._fetch_page_content(url, ScrapingResult(success=False))\n                        if page_text:\n                            st.text_area("Page Preview:", page_text[:1000] + "..." if len(page_text) > 1000 else page_text, height=200)\n                            st.success(f"Content extraction: {'Main content found' if main_found else 'Full page used'}")\n                        else:\n                            st.error("Failed to fetch page content")\n                    except Exception as e:\n                        st.error(f"Preview failed: {e}")\n    \n    if scrape_button and url:\n        # Clear previous results  \n        if 'scraping_result' in st.session_state:\n            del st.session_state.scraping_result\n        if 'parsed_recipe_data' in st.session_state:\n            del st.session_state.parsed_recipe_data\n        \n        with st.spinner("Scraping and parsing recipe..."):\n            # Step 1: Scrape content without saving to database\n            try:\n                # Fetch and parse content\n                result = ScrapingResult(success=False)\n                page_text, main_found = scraper_service._fetch_page_content(url, result)\n                \n                if page_text:\n                    st.success(f"✅ Content fetched successfully! ({len(page_text)} characters)")\n                    \n                    # Step 2: Parse with AI\n                    ai_result = scraper_service.ai_service.parse_recipe(page_text, url)\n                    \n                    if ai_result.success and ai_result.parsed_data:\n                        # Convert parsed data to ParsedRecipe object\n                        recipe_data = ai_result.parsed_data\n                        \n                        recipe = ParsedRecipe(\n                            name=recipe_data.get("name", ""),
                            description=recipe_data.get("description", ""),
                            instructions=recipe_data.get("instructions", ""),
                            benefits=recipe_data.get("benefits", ""),
                            category=recipe_data.get("category", ""),
                            route=recipe_data.get("route", ""),
                            safety_summary=recipe_data.get("safety_summary", ""),
                            contraindications=recipe_data.get("contraindications", ""),
                            interactions=recipe_data.get("interactions", ""),
                            pediatric_note=recipe_data.get("pediatric_note", ""),
                            pregnancy_note=recipe_data.get("pregnancy_note", ""),
                            sanitation_level=recipe_data.get("sanitation_level", ""),
                            storage_instructions=recipe_data.get("storage_instructions", ""),
                            shelf_life_days=int(recipe_data.get("shelf_life_days", 0)),
                            batch_size_value=float(recipe_data.get("batch_size_value", 0.0)),
                            batch_size_unit=recipe_data.get("batch_size_unit", ""),
                            ingredients=recipe_data.get("ingredients", []),
                            unknown_herbs=recipe_data.get("unknown_herbs", [])
                        )
                        # Store parsed data for preview/approval
                        st.session_state.parsed_recipe_data = {
                            'recipe': recipe,
                            'ai_result': ai_result,
                            'source_url': url,
                            'page_text': page_text
                        }
                        st.success("✅ Recipe parsed successfully! Please review and approve below.")
                    else:
                        st.error("❌ Failed to parse recipe content")
                        if ai_result.errors:
                            for error in ai_result.errors:
                                st.error(f"Parsing error: {error}")
                else:
                    st.error("❌ Failed to fetch content from URL")
                    
            except Exception as e:
                st.error(f"❌ Scraping failed: {str(e)}")
    
    # Display recipe preview and approval form if we have parsed data
    if 'parsed_recipe_data' in st.session_state and st.session_state.parsed_recipe_data.get('source_url') != 'Manual Text Input':
        display_recipe_preview_form(st.session_state.parsed_recipe_data)

# --- Text Parsing Tab ---\nwith tab_text:
    st.subheader("Parse Recipe from Text")
    st.markdown("""
    Paste recipe text directly if the webpage is cluttered or inaccessible.
    The AI will extract structured recipe information from the raw text.
    """)
    
    pasted_text = st.text_area(
        "Paste the recipe text here:",
        height=300,
        key="pasted_text"
    )

    col1, col2 = st.columns([3, 1])
    
    with col1:
        parse_button = st.button("🤖 Parse Recipe Text", type="primary")
    
    with col2:
        text_length = len(pasted_text) if pasted_text else 0
        st.metric("Text Length", f"{text_length:,} chars")
        if text_length > 14000:
            st.warning("⚠️ Text will be truncated")

    if parse_button and pasted_text:
        # Clear previous results  
        if 'parsing_result' in st.session_state:
            del st.session_state.parsing_result
        if 'parsed_recipe_data' in st.session_state:
            del st.session_state.parsed_recipe_data
        
        with st.spinner("Parsing recipe text..."):
            # Parse text without saving to database (same as URL scraping)
            try:
                ai_result = scraper_service.ai_service.parse_recipe(pasted_text, "manual_text_input")
                
                if ai_result.success and ai_result.parsed_data:
                    # Convert parsed data to ParsedRecipe object
                    recipe_data = ai_result.parsed_data
                    
                    recipe = ParsedRecipe(
                        name=recipe_data.get("name", ""),
                        description=recipe_data.get("description", ""),
                        instructions=recipe_data.get("instructions", ""),
                        benefits=recipe_data.get("benefits", ""),
                        category=recipe_data.get("category", ""),
                        route=recipe_data.get("route", ""),
                        safety_summary=recipe_data.get("safety_summary", ""),
                        contraindications=recipe_data.get("contraindications", ""),
                        interactions=recipe_data.get("interactions", ""),
                        pediatric_note=recipe_data.get("pediatric_note", ""),
                        pregnancy_note=recipe_data.get("pregnancy_note", ""),
                        sanitation_level=recipe_data.get("sanitation_level", ""),
                        storage_instructions=recipe_data.get("storage_instructions", ""),
                        shelf_life_days=int(recipe_data.get("shelf_life_days", 0)),
                        batch_size_value=float(recipe_data.get("batch_size_value", 0.0)),
                        batch_size_unit=recipe_data.get("batch_size_unit", ""),
                        ingredients=recipe_data.get("ingredients", []),
                        unknown_herbs=recipe_data.get("unknown_herbs", [])
                    )
                    # Store parsed data for preview/approval
                    st.session_state.parsed_recipe_data = {
                        'recipe': recipe,
                        'ai_result': ai_result,
                        'source_url': 'Manual Text Input',
                        'page_text': pasted_text
                    }
                    st.success("✅ Text parsed successfully! Please review and approve below.")
                else:
                    st.error("❌ Failed to parse recipe text")
                    if ai_result.errors:
                        for error in ai_result.errors:
                            st.error(f"Parsing error: {error}")
                            
            except Exception as e:
                st.error(f"❌ Text parsing failed: {str(e)}")
    
    # Display recipe preview and approval form if we have parsed data
    if 'parsed_recipe_data' in st.session_state and st.session_state.parsed_recipe_data.get('source_url') == 'Manual Text Input':
        display_recipe_preview_form(st.session_state.parsed_recipe_data)

# --- Manage Recipes Tab ---\nwith tab_manage_recipes:
    st.header("✏️ Manage Existing Recipes")
    st.markdown("Select a recipe from the dropdown below to edit its details or delete it.")

    try:
        all_recipes = load_recipes_from_db()
        all_herbs = load_herbs_from_db()
    except Exception as e:
        st.error(f"Failed to load data from database: {e}")
        all_recipes = []
        all_herbs = []

    if not all_recipes:
        st.info("No recipes found in the database to manage.")
    else:
        recipe_options = {f"{r.name} (ID: {r.id})": r for r in sorted(all_recipes, key=lambda x: x.name)}
        
        # Use session state to keep track of selection
        if 'selected_recipe_to_edit' not in st.session_state:
            st.session_state.selected_recipe_to_edit = None

        selected_recipe_key = st.selectbox(
            "Select a recipe to edit:",
            options=[None] + list(recipe_options.keys()),
            format_func=lambda x: "--- Select a Recipe ---" if x is None else x,
            key="recipe_edit_selector"
        )

        if selected_recipe_key:
            st.session_state.selected_recipe_to_edit = recipe_options[selected_recipe_key]

        # Display the editor form if a recipe is selected
        if st.session_state.selected_recipe_to_edit:
            display_recipe_editor_form(st.session_state.selected_recipe_to_edit, all_herbs)

# --- Database Management Tab ---\nwith tab_database:
    st.subheader("🗄️ Database Management & Maintenance")
    
    # Display comprehensive database management interface
    display_database_management_interface()
    
    # Database Migration Tools
    st.markdown("---")
    st.subheader("📁 Data Migration & Import")
    
    # CSV Migration Status
    csv_files = [("herbs.csv", "Herbs"), ("recipes.csv", "Recipes")]
    csv_status = []
    
    for filename, description in csv_files:
        file_path = Path(filename)
        if file_path.exists():
            try:
                # Basic file info
                file_size = file_path.stat().st_size
                csv_status.append({
                    "file": filename,
                    "description": description,
                    "exists": True,
                    "size_kb": round(file_size / 1024, 1)
                })
            except Exception:
                csv_status.append({
                    "file": filename,
                    "description": description,
                    "exists": False,
                    "error": "Access error"
                })
        else:
            csv_status.append({
                "file": filename,
                "description": description,
                "exists": False
            })
    
    # Display CSV status
    for status in csv_files:
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.write(f"**{status['description']} ({status['file']})**")
        with col2:
            if status["exists"]:
                st.success(f"✅ Available ({status.get('size_kb', 0)} KB)")
            else:
                st.info("❌ Not found")
        with col3:
            if status["exists"] and st.button(f"Import {status['description']}", key=f"import_{status['file']}"):
                try:
                    st.info(f"Importing {status['file']}...")
                    migrate_from_csv()
                    st.success(f"✅ {status['description']} imported successfully!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Import failed: {e}")
    
    # Transaction Consistency Testing
    st.markdown("---")
    st.subheader("⚙️ Transaction Consistency Testing")
    
    if st.button("🧪 Run Database Integrity Test"):
        with st.spinner("Testing database integrity..."):
            try:
                # Test basic operations
                test_results = {
                    "herb_loading": False,
                    "recipe_loading": False,
                    "scraper_service_integration": False,
                    "database_stats": False
                }
                
                # Test 1: Herb loading
                try:
                    herbs = load_herbs_from_db()
                    test_results["herb_loading"] = True
                    st.success(f"✅ Herb loading: {len(herbs)} herbs loaded")
                except Exception as e:
                    st.error(f"❌ Herb loading failed: {e}")
                
                # Test 2: Database stats
                try:
                    stats = get_database_stats()
                    test_results["database_stats"] = True
                    st.success(f"✅ Database stats: {stats['herbs']} herbs, {stats['recipes']} recipes")
                except Exception as e:
                    st.error(f"❌ Database stats failed: {e}")
                
                # Test 3: Scraper service integration
                try:
                    # Test database service integration
                    test_herb_result = scraper_service.db_service.get_herbs_by_names(["nonexistent_herb"])
                    test_results["scraper_service_integration"] = True
                    st.success("✅ Scraper service database integration working")
                except Exception as e:
                    st.error(f"❌ Scraper service integration failed: {e}")
                
                # Summary
                passed_tests = sum(test_results.values())
                total_tests = len(test_results)
                
                if passed_tests == total_tests:
                    st.success(f"🎉 All {total_tests} tests passed! Database is fully operational.")
                else:
                    st.warning(f"⚠️ {passed_tests}/{total_tests} tests passed. Some issues detected.")
                
            except Exception as e:
                st.error(f"Integrity test failed: {e}")
    
    # Database Information
    st.markdown("---")
    st.subheader("📊 Database Information")
    
    try:
        detailed_stats = get_database_stats()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Database Contents:**")
            st.json({
                "Total Herbs": detailed_stats["herbs"],
                "Total Recipes": detailed_stats["recipes"],
                "Database Size (MB)": detailed_stats["db_size_mb"]
            })
        
        with col2:
            st.write("**Database File:**")
            db_path = Path("herbalism.db")
            if db_path.exists():
                stat = db_path.stat()
                st.json({
                    "File Size (bytes)": stat.st_size,
                    "Last Modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "Readable": db_path.is_file() and os.access(db_path, os.R_OK),
                    "Writable": db_path.is_file() and os.access(db_path, os.W_OK)
                })
            else:
                st.error("Database file not found!")
                
    except Exception as e:
        st.error(f"Failed to get database information: {e}")

# --- Debug & Monitoring Tab ---\nwith tab_debug:
    st.subheader("🔧 Debug & Monitoring")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Service Statistics")
        
        try:
            stats = scraper_service.get_operation_statistics()
            
            if stats.get("total_operations", 0) > 0:
                # Overall statistics
                st.write("**Overall Performance:**")
                st.json({
                    "Total Operations": stats["total_operations"],
                    "Success Rate": f"{stats['success_rate']:.1%}",
                    "Avg Errors/Operation": f"{stats['average_errors_per_operation']:.2f}",
                    "Avg Warnings/Operation": f"{stats['average_warnings_per_operation']:.2f}"
                })
                
                # Component statistics
                st.write("**Component Performance:**")
                ai_stats = stats.get("ai_parsing_stats", {})
                validation_stats = stats.get("validation_stats", {})
                
                if ai_stats:
                    st.write("🤖 AI Parsing:")
                    st.json(ai_stats)
                
                if validation_stats:
                    st.write("✅ Validation:")
                    st.json(validation_stats)
                
            else:
                st.info("No operations performed yet")
                
        except Exception as e:
            st.error(f"Statistics unavailable: {e}")
    
    with col2:
        st.subheader("📋 Recent Operations")
        
        try:
            recent_ops = scraper_service.get_recent_operations(10)
            
            if recent_ops:
                for i, op in enumerate(recent_ops[-5:], 1):  # Show last 5
                    with st.expander(f"Operation {i}: {op['operation_type']}"):
                        st.json({
                            "Timestamp": op["timestamp"].isoformat() if hasattr(op["timestamp"], "isoformat") else str(op["timestamp"]),
                            "Success": op["success"],
                            "Errors": op["errors"],
                            "Warnings": op["warnings"],
                            "Source": op["source"][:50] + "..." if len(str(op["source"])) > 50 else op["source"]
                        })
            else:
                st.info("No recent operations")
                
        except Exception as e:
            st.error(f"Recent operations unavailable: {e}")
    
    # Error Log Viewer
    st.subheader("🚨 Error Log Viewer")
    
    error_category = st.selectbox(
        "Filter by Error Category:",
        ["All", "AI Parsing", "Database", "Validation", "Network", "Configuration"],
        key="error_category_filter"
    )
    
    try:
        # Map UI selection to ErrorCategory enum
        category_map = {
            "AI Parsing": ErrorCategory.AI_PARSING,
            "Database": ErrorCategory.DATABASE,
            "Validation": ErrorCategory.VALIDATION,
            "Network": ErrorCategory.NETWORK,
            "Configuration": ErrorCategory.CONFIGURATION
        }
        
        selected_category = category_map.get(error_category) if error_category != "All" else None
        recent_errors = logger.get_recent_errors(10, selected_category)
        
        if recent_errors:
            for i, error in enumerate(recent_errors, 1):
                with st.expander(f"Error {i}: {error['category']} - {error['operation']}"):
                    st.error(error['message'])
                    st.write(f"**Timestamp:** {error['timestamp']}")
                    st.write(f"**Context Keys:** {', '.join(error['context_keys'])}")
                    if error['has_stack_trace']:
                        st.warning("Stack trace available in detailed logs")
        else:
            st.success("No recent errors found! 🎉")
            
    except Exception as e:
        st.error(f"Error log unavailable: {e}")
    
    # Export Debug Data
    if st.button("📥 Export Debug Data"):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scraper_debug_{timestamp}.json"
            logger.export_debug_data(filename)
            st.success(f"Debug data exported to {filename}")
        except Exception as e:
            st.error(f"Export failed: {e}")

# --- Footer ---\nst.markdown("---")\nst.markdown("""
<div style=\"text-align: center; color: #666; font-size: 0.8em;\">
Enhanced Recipe Scraper v2.0 | Powered by LM Studio AI | 
<a href=\"#\" onclick=\"window.location.reload()">Refresh Page</a>
</div>
""", unsafe_allow_html=True)