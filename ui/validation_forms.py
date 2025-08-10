"""
Manual validation forms for scraped recipe data.

Provides Streamlit-based interface for users to review, correct, and validate
scraped recipe information before saving to the database.
Adapted from Herbalism app UI patterns with recipe-specific workflows.
"""

import streamlit as st
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from models import ParsedRecipe, ValidationResult, Ingredient
from services import ParsingService, DatabaseService
from utils import get_logger

logger = get_logger(__name__)


class ValidationInterface:
    """
    Manual validation interface for scraped recipe data.
    
    Provides forms for users to review and correct parsed recipe information,
    assign ingredients to database entries, and create new ingredients as needed.
    """
    
    def __init__(self, parsing_service: ParsingService, database_service: DatabaseService):
        self.parser = parsing_service
        self.db = database_service
        
        # Initialize CSS styling
        self._inject_custom_css()
    
    def validate_recipe(self, parsed_recipe: ParsedRecipe, user_id: int) -> Optional[ValidationResult]:
        """
        Display validation form and return user-validated result.
        
        Args:
            parsed_recipe: Recipe data to validate
            user_id: ID of user performing validation
            
        Returns:
            ValidationResult if validation completed, None if form still in progress
        """
        st.subheader("🔍 Recipe Validation")
        
        # Show original parsing quality
        self._display_parsing_summary(parsed_recipe)
        
        # Create validation form
        with st.form(key=f"validate_recipe_{id(parsed_recipe)}", clear_on_submit=False):
            st.markdown("### 📝 Review and Correct Recipe Details")
            
            # Basic recipe information
            validated_data = self._validate_basic_info(parsed_recipe)
            
            # Time and serving information
            validated_data.update(self._validate_time_serving_info(parsed_recipe))
            
            # Category and tags
            validated_data.update(self._validate_categories_tags(parsed_recipe))
            
            # Ingredient validation (most complex part)
            ingredient_assignments, new_ingredients = self._validate_ingredients(parsed_recipe)
            
            # Submit buttons
            col1, col2 = st.columns([1, 1])
            with col1:
                accept_recipe = st.form_submit_button("✅ Accept Recipe", type="primary")
            with col2:
                reject_recipe = st.form_submit_button("❌ Reject Recipe", type="secondary")
            
            # Process form submission
            if accept_recipe:
                return self._create_validation_result(
                    parsed_recipe, validated_data, ingredient_assignments, 
                    new_ingredients, user_id, is_valid=True
                )
            elif reject_recipe:
                return self._create_validation_result(
                    parsed_recipe, validated_data, ingredient_assignments,
                    new_ingredients, user_id, is_valid=False
                )
        
        return None
    
    def _display_parsing_summary(self, parsed_recipe: ParsedRecipe):
        """Display summary of parsing quality and issues"""
        with st.expander("🔍 Parsing Summary", expanded=False):
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                st.metric("Ingredients Found", len(parsed_recipe.ingredients))
                st.metric("Total Time", f"{parsed_recipe.get_total_time()} min")
            
            with col2:
                st.metric("Servings", parsed_recipe.servings)
                st.metric("Difficulty", parsed_recipe.difficulty_level.title())
            
            with col3:
                st.metric("Cuisine", parsed_recipe.cuisine_type or "Unknown")
                st.metric("Category", parsed_recipe.meal_category or "Unknown")
            
            # Show parsing issues if any
            if parsed_recipe.parsing_issues:
                st.warning("**Parsing Issues Detected:**")
                for issue in parsed_recipe.parsing_issues:
                    st.write(f"• {issue}")
            
            # Show fields needing review
            if parsed_recipe.fields_needing_review:
                st.info(f"**Fields Needing Review:** {', '.join(parsed_recipe.fields_needing_review)}")
    
    def _validate_basic_info(self, parsed_recipe: ParsedRecipe) -> Dict[str, Any]:
        """Validate basic recipe information"""
        st.markdown("#### Basic Information")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            title = st.text_input(
                "Recipe Title",
                value=parsed_recipe.title,
                key=f"title_{id(parsed_recipe)}"
            )
            
            description = st.text_area(
                "Description",
                value=parsed_recipe.description,
                height=100,
                key=f"description_{id(parsed_recipe)}"
            )
            
            instructions = st.text_area(
                "Cooking Instructions",
                value=parsed_recipe.instructions,
                height=200,
                key=f"instructions_{id(parsed_recipe)}"
            )
        
        with col2:
            source_url = st.text_input(
                "Source URL",
                value=parsed_recipe.source_url,
                disabled=True,
                key=f"source_{id(parsed_recipe)}"
            )
        
        return {
            'title': title,
            'description': description,
            'instructions': instructions,
            'source_url': source_url
        }
    
    def _validate_time_serving_info(self, parsed_recipe: ParsedRecipe) -> Dict[str, Any]:
        """Validate time and serving information"""
        st.markdown("#### Time & Servings")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            prep_time = st.number_input(
                "Prep Time (minutes)",
                min_value=0,
                max_value=600,
                value=parsed_recipe.prep_time_minutes,
                key=f"prep_time_{id(parsed_recipe)}"
            )
        
        with col2:
            cook_time = st.number_input(
                "Cook Time (minutes)",
                min_value=0,
                max_value=1440,
                value=parsed_recipe.cook_time_minutes,
                key=f"cook_time_{id(parsed_recipe)}"
            )
        
        with col3:
            servings = st.number_input(
                "Servings",
                min_value=1,
                max_value=50,
                value=parsed_recipe.servings,
                key=f"servings_{id(parsed_recipe)}"
            )
        
        return {
            'prep_time_minutes': prep_time,
            'cook_time_minutes': cook_time,
            'servings': servings
        }
    
    def _validate_categories_tags(self, parsed_recipe: ParsedRecipe) -> Dict[str, Any]:
        """Validate categories and dietary tags"""
        st.markdown("#### Categories & Tags")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Difficulty level
            difficulty = st.selectbox(
                "Difficulty Level",
                options=["easy", "medium", "hard"],
                index=["easy", "medium", "hard"].index(parsed_recipe.difficulty_level),
                key=f"difficulty_{id(parsed_recipe)}"
            )
            
            # Cuisine type
            cuisine_options = [
                "", "American", "Italian", "Mexican", "Chinese", "Indian", 
                "French", "Thai", "Japanese", "Mediterranean", "Other"
            ]
            cuisine_index = 0
            if parsed_recipe.cuisine_type in cuisine_options:
                cuisine_index = cuisine_options.index(parsed_recipe.cuisine_type)
            
            cuisine = st.selectbox(
                "Cuisine Type",
                options=cuisine_options,
                index=cuisine_index,
                key=f"cuisine_{id(parsed_recipe)}"
            )
        
        with col2:
            # Meal category
            category_options = ["", "breakfast", "lunch", "dinner", "snack", "dessert"]
            category_index = 0
            if parsed_recipe.meal_category in category_options:
                category_index = category_options.index(parsed_recipe.meal_category)
            
            meal_category = st.selectbox(
                "Meal Category",
                options=category_options,
                index=category_index,
                key=f"category_{id(parsed_recipe)}"
            )
            
            # Dietary tags
            available_tags = [
                "vegetarian", "vegan", "gluten-free", "dairy-free", 
                "low-carb", "high-protein", "healthy", "keto"
            ]
            
            dietary_tags = st.multiselect(
                "Dietary Tags",
                options=available_tags,
                default=parsed_recipe.dietary_tags,
                key=f"tags_{id(parsed_recipe)}"
            )
        
        return {
            'difficulty_level': difficulty,
            'cuisine_type': cuisine,
            'meal_category': meal_category,
            'dietary_tags': dietary_tags
        }
    
    def _validate_ingredients(self, parsed_recipe: ParsedRecipe) -> Tuple[Dict[str, int], List[str]]:
        """Validate and match ingredients - most complex validation step"""
        st.markdown("#### 🥕 Ingredient Validation")
        st.markdown("Review each ingredient and assign it to existing database entries or mark for creation.")
        
        ingredient_assignments = {}  # ingredient_text -> ingredient_id
        new_ingredients = []
        
        # Load all available ingredients from database
        all_db_ingredients = self.db.get_all_ingredients()
        ingredient_options = ["[Create New]"] + [f"{ing.name} ({ing.category})" for ing in all_db_ingredients]
        ingredient_map = {f"{ing.name} ({ing.category})": ing.id for ing in all_db_ingredients}
        
        for i, ingredient_data in enumerate(parsed_recipe.ingredients):
            with st.container():
                st.markdown(f"**Ingredient {i+1}:**")
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    # Display original ingredient text
                    original_text = ingredient_data.get('original_text', '')
                    st.text_input(
                        "Original Text",
                        value=original_text,
                        disabled=True,
                        key=f"orig_{i}_{id(parsed_recipe)}"
                    )
                    
                    # Show parsed components
                    quantity = ingredient_data.get('quantity', 0.0)
                    unit = ingredient_data.get('unit', '')
                    name = ingredient_data.get('name', '')
                    preparation = ingredient_data.get('preparation', '')
                    optional = ingredient_data.get('optional', False)
                    
                    col1a, col1b = st.columns([1, 1])
                    with col1a:
                        st.text_input(f"Quantity", value=str(quantity), disabled=True, key=f"qty_{i}_{id(parsed_recipe)}")
                        st.text_input(f"Name", value=name, disabled=True, key=f"name_{i}_{id(parsed_recipe)}")
                    with col1b:
                        st.text_input(f"Unit", value=unit, disabled=True, key=f"unit_{i}_{id(parsed_recipe)}")
                        st.text_input(f"Prep", value=preparation, disabled=True, key=f"prep_{i}_{id(parsed_recipe)}")
                
                with col2:
                    # Find potential matches
                    potential_matches = self.parser.suggest_ingredient_matches(name, max_suggestions=5)
                    
                    if potential_matches:
                        st.markdown("**Suggested Matches:**")
                        for match_ingredient, confidence in potential_matches[:3]:
                            confidence_color = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.5 else "🔴"
                            st.write(f"{confidence_color} {match_ingredient.name} ({match_ingredient.category}) - {confidence:.0%}")
                    
                    # Assignment dropdown
                    default_selection = 0  # "[Create New]"
                    if potential_matches and potential_matches[0][1] > 0.7:
                        # Auto-select high confidence match
                        best_match = potential_matches[0][0]
                        match_key = f"{best_match.name} ({best_match.category})"
                        if match_key in ingredient_options:
                            default_selection = ingredient_options.index(match_key)
                    
                    assignment = st.selectbox(
                        "Assign to Database Ingredient",
                        options=ingredient_options,
                        index=default_selection,
                        key=f"assign_{i}_{id(parsed_recipe)}"
                    )
                    
                    # Process assignment
                    if assignment == "[Create New]":
                        new_ingredient_name = st.text_input(
                            "New Ingredient Name",
                            value=name,
                            key=f"new_name_{i}_{id(parsed_recipe)}"
                        )
                        if new_ingredient_name.strip():
                            new_ingredients.append(new_ingredient_name.strip())
                    else:
                        ingredient_id = ingredient_map[assignment]
                        ingredient_assignments[original_text] = ingredient_id
                
                st.markdown("---")
        
        # Summary of assignments
        if ingredient_assignments or new_ingredients:
            with st.expander("📋 Assignment Summary", expanded=False):
                if ingredient_assignments:
                    st.markdown("**Assigned to Existing:**")
                    for text, ing_id in ingredient_assignments.items():
                        ing = next((ing for ing in all_db_ingredients if ing.id == ing_id), None)
                        if ing:
                            st.write(f"• {text} → {ing.name} ({ing.category})")
                
                if new_ingredients:
                    st.markdown("**New Ingredients to Create:**")
                    for new_ing in new_ingredients:
                        st.write(f"• {new_ing}")
        
        return ingredient_assignments, new_ingredients
    
    def _create_validation_result(
        self, 
        parsed_recipe: ParsedRecipe, 
        validated_data: Dict[str, Any],
        ingredient_assignments: Dict[str, int],
        new_ingredients: List[str],
        user_id: int,
        is_valid: bool
    ) -> ValidationResult:
        """Create validation result from form data"""
        
        result = ValidationResult(
            is_valid=is_valid,
            ingredient_assignments=ingredient_assignments,
            new_ingredients=new_ingredients,
            validated_by=user_id,
            validated_at=datetime.now()
        )
        
        # Record field corrections
        original_data = {
            'title': parsed_recipe.title,
            'description': parsed_recipe.description,
            'instructions': parsed_recipe.instructions,
            'prep_time_minutes': parsed_recipe.prep_time_minutes,
            'cook_time_minutes': parsed_recipe.cook_time_minutes,
            'servings': parsed_recipe.servings,
            'difficulty_level': parsed_recipe.difficulty_level,
            'cuisine_type': parsed_recipe.cuisine_type,
            'meal_category': parsed_recipe.meal_category,
            'dietary_tags': parsed_recipe.dietary_tags
        }
        
        for field, original_value in original_data.items():
            if field in validated_data and validated_data[field] != original_value:
                result.add_correction(field, original_value, validated_data[field])
        
        # Create validated recipe
        if is_valid:
            validated_recipe = ParsedRecipe(
                title=validated_data['title'],
                description=validated_data['description'],
                instructions=validated_data['instructions'],
                source_url=validated_data['source_url'],
                prep_time_minutes=validated_data['prep_time_minutes'],
                cook_time_minutes=validated_data['cook_time_minutes'],
                servings=validated_data['servings'],
                difficulty_level=validated_data['difficulty_level'],
                cuisine_type=validated_data['cuisine_type'],
                meal_category=validated_data['meal_category'],
                dietary_tags=validated_data['dietary_tags'],
                ingredients=parsed_recipe.ingredients  # Keep original ingredient data
            )
            result.validated_recipe = validated_recipe
        
        # Add validation notes
        correction_count = len(result.field_corrections)
        assignment_count = len(ingredient_assignments)
        new_count = len(new_ingredients)
        
        result.validation_notes.append(
            f"Manual validation completed: {correction_count} corrections, "
            f"{assignment_count} ingredient assignments, {new_count} new ingredients"
        )
        
        if not is_valid:
            result.validation_notes.append("Recipe rejected during manual validation")
        
        logger.info(f"Validation result created for recipe: {parsed_recipe.title}, valid: {is_valid}")
        
        return result
    
    def _inject_custom_css(self):
        """Inject custom CSS styling similar to Herbalism app"""
        st.markdown("""
        <style>
            .validation-container {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 1rem;
                margin: 1rem 0;
                background-color: #fafafa;
            }
            
            .ingredient-match-high {
                color: #2E7D32;
                font-weight: bold;
                background-color: #E8F5E9;
                padding: 2px 6px;
                border-radius: 4px;
                border: 1px solid #A5D6A7;
            }
            
            .ingredient-match-medium {
                color: #F57F17;
                background-color: #FFFDE7;
                padding: 2px 6px;
                border-radius: 4px;
                border: 1px solid #FFECB3;
            }
            
            .ingredient-match-low {
                color: #C62828;
                background-color: #FFEBEE;
                padding: 2px 6px;
                border-radius: 4px;
                border: 1px solid #EF9A9A;
            }
            
            .validation-header {
                font-weight: 600;
                color: #1976D2;
                margin-bottom: 0.5rem;
            }
            
            .parsing-issue {
                color: #E65100;
                background-color: #FFF3E0;
                padding: 4px 8px;
                border-radius: 4px;
                border-left: 4px solid #FF9800;
                margin: 4px 0;
            }
        </style>
        """, unsafe_allow_html=True)


def create_validation_interface(parsing_service: ParsingService, database_service: DatabaseService) -> ValidationInterface:
    """Factory function to create validation interface"""
    return ValidationInterface(parsing_service, database_service)