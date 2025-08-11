"""
Simplified recipe validation interface with clean UX.

Focuses on essential validation with automatic ingredient creation and pantry integration.
Removes confusing form elements and provides clear recipe format output.
"""

import streamlit as st
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from models import ParsedRecipe, ValidationResult, ScrapedRecipe
from services.ai_ingredient_parser import AIIngredientParser, ParsedIngredient
from services import DatabaseService, get_pantry_service
from utils import get_logger

logger = get_logger(__name__)


class SimpleValidationInterface:
    """
    Simplified validation interface with clean UX.
    
    Key improvements:
    - Clean recipe format display
    - Simple checkbox validation  
    - Automatic ingredient creation
    - Pantry integration
    - No confusing parsing details
    """
    
    def __init__(self, ai_parser: AIIngredientParser, database_service: DatabaseService):
        self.ai_parser = ai_parser
        self.db = database_service
        self.pantry_service = get_pantry_service(database_service)
    
    def validate_recipe_simple(self, scraped_recipe: ScrapedRecipe, user_id: int) -> Optional[ValidationResult]:
        """
        Simple validation interface with clean UX.
        
        Args:
            scraped_recipe: Raw scraped recipe data
            user_id: User performing validation
            
        Returns:
            ValidationResult if validated, None if still in progress
        """
        st.markdown("### 🔍 Recipe Review")
        st.markdown("Review this recipe and make any necessary corrections before saving to your cookbook.")
        
        # Parse ingredients with AI
        parsed_ingredients = self._get_parsed_ingredients(scraped_recipe)
        
        with st.form(key=f"simple_validation_{id(scraped_recipe)}", clear_on_submit=False):
            
            # Recipe overview in clean format
            validated_data = self._render_recipe_overview(scraped_recipe)
            
            # Ingredients section with simple validation
            ingredient_validation = self._render_ingredient_validation(parsed_ingredients, user_id)
            
            # Instructions review
            validated_instructions = self._render_instructions_validation(scraped_recipe)
            validated_data['instructions'] = validated_instructions
            
            # Action buttons
            col1, col2 = st.columns([2, 1])
            with col1:
                save_recipe = st.form_submit_button("💾 Save to My Cookbook", type="primary", use_container_width=True)
            with col2:
                reject_recipe = st.form_submit_button("❌ Discard", type="secondary", use_container_width=True)
            
            # Process validation
            if save_recipe:
                return self._create_validation_result(
                    scraped_recipe, validated_data, ingredient_validation, 
                    user_id, is_valid=True
                )
            elif reject_recipe:
                st.warning("Recipe discarded.")
                return ValidationResult(
                    is_valid=False,
                    validated_data={},
                    ingredient_assignments={},
                    new_ingredients=[],
                    validation_notes="Recipe rejected by user",
                    user_id=user_id
                )
        
        return None
    
    def _get_parsed_ingredients(self, scraped_recipe: ScrapedRecipe) -> List[ParsedIngredient]:
        """Get AI-parsed ingredients with caching"""
        cache_key = f"parsed_ingredients_{id(scraped_recipe)}"
        
        if cache_key not in st.session_state:
            with st.spinner("🤖 AI is parsing ingredients..."):
                parsed_ingredients = self.ai_parser.parse_ingredients_with_ai(scraped_recipe.ingredients_raw)
                st.session_state[cache_key] = parsed_ingredients
        
        return st.session_state[cache_key]
    
    def _render_recipe_overview(self, scraped_recipe: ScrapedRecipe) -> Dict:
        """Render clean recipe overview for validation"""
        st.markdown("#### 📋 Recipe Details")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Basic recipe info
            title = st.text_input("Recipe Title", value=scraped_recipe.title, key="title")
            description = st.text_area(
                "Description", 
                value=scraped_recipe.description or "", 
                height=80,
                key="description",
                help="Brief description of the recipe"
            )
        
        with col2:
            # Time and serving info in a compact layout
            col2a, col2b = st.columns(2)
            
            with col2a:
                prep_time = st.number_input(
                    "Prep (min)", 
                    value=self._parse_time_minutes(scraped_recipe.prep_time_text),
                    min_value=0,
                    key="prep_time"
                )
                servings = st.number_input(
                    "Servings", 
                    value=self._parse_servings(scraped_recipe.servings_text),
                    min_value=1,
                    key="servings"
                )
            
            with col2b:
                cook_time = st.number_input(
                    "Cook (min)", 
                    value=self._parse_time_minutes(scraped_recipe.cook_time_text),
                    min_value=0,
                    key="cook_time"
                )
                difficulty = st.selectbox(
                    "Difficulty",
                    ["easy", "medium", "hard"],
                    index=["easy", "medium", "hard"].index(self._parse_difficulty(scraped_recipe.difficulty_text)),
                    key="difficulty"
                )
        
        # Optional metadata
        with st.expander("🏷️ Additional Info (Optional)", expanded=False):
            col3, col4 = st.columns(2)
            
            with col3:
                cuisine = st.text_input("Cuisine Type", value=scraped_recipe.cuisine_text or "", key="cuisine")
                meal_category = st.selectbox(
                    "Meal Category",
                    ["", "breakfast", "lunch", "dinner", "snack", "dessert", "appetizer"],
                    index=0,
                    key="meal_category"
                )
            
            with col4:
                dietary_tags = st.text_input(
                    "Dietary Tags", 
                    value="",
                    key="dietary_tags",
                    help="Separate with commas (e.g., vegetarian, gluten-free, dairy-free)"
                )
        
        return {
            'title': title,
            'description': description,
            'prep_time_minutes': prep_time,
            'cook_time_minutes': cook_time,
            'servings': servings,
            'difficulty_level': difficulty,
            'cuisine_type': cuisine,
            'meal_category': meal_category,
            'dietary_tags': [tag.strip() for tag in dietary_tags.split(',') if tag.strip()]
        }
    
    def _render_ingredient_validation(self, parsed_ingredients: List[ParsedIngredient], user_id: int) -> Dict:
        """Render simplified ingredient validation"""
        st.markdown("#### 🥕 Ingredients")
        st.markdown("AI has parsed your ingredients. Review the list and check any that look incorrect.")
        
        validated_ingredients = []
        new_ingredients_to_create = []
        pantry_updates = []
        
        # Show ingredients in a clean format
        for i, ingredient in enumerate(parsed_ingredients):
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Format ingredient display
                    display_text = self._format_ingredient_display(ingredient)
                    
                    # Show status and allow editing
                    edited_text = st.text_input(
                        f"Ingredient {i+1}",
                        value=display_text,
                        key=f"ingredient_{i}",
                        help="Edit if the AI parsing looks wrong"
                    )
                    
                    # Re-parse if user edited
                    if edited_text != display_text:
                        # User made edits, re-parse this ingredient
                        ingredient = self._reparse_single_ingredient(edited_text, ingredient.original_text)
                
                with col2:
                    # Database status
                    if ingredient.exists_in_db:
                        st.success("✅ In Database")
                        
                        # Check pantry status
                        user_pantry = self.pantry_service.get_user_pantry(user_id)
                        in_pantry = any(item.ingredient_id == ingredient.suggested_ingredient_id and item.is_available 
                                      for item in user_pantry)
                        
                        if in_pantry:
                            st.info("🥬 In Your Pantry")
                        else:
                            st.warning("🛒 Need to Buy")
                            # Allow user to mark as available if they have it
                            if st.checkbox(f"I have this", key=f"have_{i}"):
                                pantry_updates.append((ingredient.suggested_ingredient_id, True))
                    else:
                        st.info("✨ Will Create New")
                        new_ingredients_to_create.append({
                            'name': ingredient.name,
                            'category': self._guess_ingredient_category(ingredient.name)
                        })
                        
                        # This will be marked as not in pantry (user needs to buy)
                        st.warning("🛒 Add to Shopping List")
                
                validated_ingredients.append(ingredient)
                
                # Add visual separator
                if i < len(parsed_ingredients) - 1:
                    st.divider()
        
        return {
            'validated_ingredients': validated_ingredients,
            'new_ingredients_to_create': new_ingredients_to_create,
            'pantry_updates': pantry_updates
        }
    
    def _render_instructions_validation(self, scraped_recipe: ScrapedRecipe) -> str:
        """Render instructions validation"""
        st.markdown("#### 👩‍🍳 Instructions")
        
        instructions = st.text_area(
            "Cooking Instructions",
            value=scraped_recipe.instructions_raw,
            height=200,
            key="instructions",
            help="Review and edit the cooking instructions as needed"
        )
        
        return instructions
    
    def _format_ingredient_display(self, ingredient: ParsedIngredient) -> str:
        """Format ingredient for clean display"""
        parts = []
        
        # Add quantity and unit
        if ingredient.quantity > 0:
            # Format quantity nicely
            if ingredient.quantity == int(ingredient.quantity):
                parts.append(str(int(ingredient.quantity)))
            else:
                parts.append(str(ingredient.quantity))
        
        if ingredient.unit:
            parts.append(ingredient.unit)
        
        # Add ingredient name
        if ingredient.name:
            parts.append(ingredient.name)
        
        # Add preparation if any
        if ingredient.preparation:
            if ingredient.preparation.startswith('(') and ingredient.preparation.endswith(')'):
                parts.append(ingredient.preparation)
            else:
                parts.append(f"({ingredient.preparation})")
        
        # Add optional indicator
        if ingredient.optional:
            parts.append("(optional)")
        
        return " ".join(parts) if parts else ingredient.original_text
    
    def _reparse_single_ingredient(self, edited_text: str, original_text: str) -> ParsedIngredient:
        """Re-parse single ingredient when user edits it"""
        # For now, create a basic parsed ingredient from edited text
        # In the future, this could call AI again for single ingredient
        return ParsedIngredient(
            original_text=original_text,
            quantity=0.0,
            unit="",
            name=edited_text,
            preparation="",
            optional=False,
            confidence=0.8
        )
    
    def _create_validation_result(self, scraped_recipe: ScrapedRecipe, validated_data: Dict,
                                ingredient_validation: Dict, user_id: int, is_valid: bool) -> ValidationResult:
        """Create validation result with pantry integration"""
        
        # Create ingredient assignments and new ingredients
        ingredient_assignments = {}
        new_ingredients = []
        
        for ingredient in ingredient_validation['validated_ingredients']:
            if ingredient.exists_in_db and ingredient.suggested_ingredient_id:
                ingredient_assignments[ingredient.original_text] = ingredient.suggested_ingredient_id
            else:
                new_ingredients.append(ingredient.name)
        
        # Add new ingredients from the to_create list
        for new_ing in ingredient_validation['new_ingredients_to_create']:
            if new_ing['name'] not in new_ingredients:
                new_ingredients.append(new_ing['name'])
        
        # Update pantry for ingredients user marked as available
        for ingredient_id, is_available in ingredient_validation.get('pantry_updates', []):
            try:
                self.pantry_service.update_pantry_item(user_id, ingredient_id, is_available)
            except Exception as e:
                logger.warning(f"Failed to update pantry item {ingredient_id}: {e}")
        
        result = ValidationResult(
            is_valid=is_valid,
            validated_data=validated_data,
            ingredient_assignments=ingredient_assignments,
            new_ingredients=new_ingredients,
            validation_notes="Validated with simplified interface and pantry integration",
            user_id=user_id
        )
        
        # Add success message with pantry summary
        if is_valid:
            total_ingredients = len(ingredient_validation['validated_ingredients'])
            existing_ingredients = len(ingredient_assignments)
            new_ingredient_count = len(new_ingredients)
            
            st.success(f"""
            ✅ **Recipe Validated Successfully!**
            
            - **{total_ingredients}** total ingredients processed
            - **{existing_ingredients}** matched to existing ingredients  
            - **{new_ingredient_count}** new ingredients will be created
            - Pantry has been updated with your availability choices
            
            Recipe is ready to save to your cookbook! 🍳
            """)
        
        return result
    
    # Helper methods for parsing basic data
    def _parse_time_minutes(self, time_text: str) -> int:
        """Parse time text to minutes"""
        if not time_text:
            return 0
        
        import re
        # Look for patterns like "30 minutes", "1 hour", "1h 30m"
        minutes = 0
        
        # Find hours
        hour_match = re.search(r'(\d+)\s*(?:hours?|hrs?|h)', time_text.lower())
        if hour_match:
            minutes += int(hour_match.group(1)) * 60
        
        # Find minutes
        minute_match = re.search(r'(\d+)\s*(?:minutes?|mins?|m)', time_text.lower())
        if minute_match:
            minutes += int(minute_match.group(1))
        
        # If no units found, assume it's minutes if it's a reasonable number
        if minutes == 0:
            number_match = re.search(r'(\d+)', time_text)
            if number_match:
                num = int(number_match.group(1))
                if 1 <= num <= 600:  # Reasonable minute range
                    minutes = num
        
        return minutes
    
    def _parse_servings(self, servings_text: str) -> int:
        """Parse servings text to number"""
        if not servings_text:
            return 4  # Default
        
        import re
        match = re.search(r'(\d+)', servings_text)
        if match:
            servings = int(match.group(1))
            return max(1, min(20, servings))  # Reasonable range
        
        return 4  # Default
    
    def _parse_difficulty(self, difficulty_text: str) -> str:
        """Parse difficulty text to standard level"""
        if not difficulty_text:
            return "medium"
        
        text_lower = difficulty_text.lower()
        if "easy" in text_lower or "simple" in text_lower or "beginner" in text_lower:
            return "easy"
        elif "hard" in text_lower or "difficult" in text_lower or "advanced" in text_lower:
            return "hard"
        else:
            return "medium"
    
    def _guess_ingredient_category(self, ingredient_name: str) -> str:
        """Guess ingredient category for new ingredients"""
        name_lower = ingredient_name.lower()
        
        # Simple categorization rules
        if any(word in name_lower for word in ['chicken', 'beef', 'pork', 'fish', 'turkey', 'bacon']):
            return 'protein'
        elif any(word in name_lower for word in ['milk', 'cheese', 'butter', 'cream', 'yogurt']):
            return 'dairy'
        elif any(word in name_lower for word in ['tomato', 'onion', 'carrot', 'celery', 'pepper']):
            return 'vegetable'
        elif any(word in name_lower for word in ['flour', 'rice', 'pasta', 'bread', 'oats']):
            return 'grain'
        elif any(word in name_lower for word in ['oil', 'olive oil', 'coconut oil']):
            return 'oil'
        elif any(word in name_lower for word in ['salt', 'pepper', 'garlic', 'basil', 'oregano']):
            return 'seasoning'
        elif any(word in name_lower for word in ['sugar', 'honey', 'syrup']):
            return 'sweetener'
        else:
            return 'other'