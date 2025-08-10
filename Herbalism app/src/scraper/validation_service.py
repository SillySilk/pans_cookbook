"""
Validation service for recipe and herb data with comprehensive safety checking.

This module provides validation for all scraped data before database storage,
with particular emphasis on safety validation for herbs. All validation issues
are explicitly reported - no silent failures or fallback masking.
"""
import re
from typing import List, Set, Dict, Any
from .models import (
    ParsedRecipe, ParsedHerb, ValidationResult, SafetyValidationResult
)


class ValidationService:
    """
    Comprehensive validation service for recipe and herb data.
    
    Provides field-level validation, safety checking, and dangerous content
    detection. Never fails silently - all validation issues are reported
    with specific context for debugging and user guidance.
    """
    
    # Known dangerous plants and compounds that require special attention
    DANGEROUS_PLANTS = {
        "aconitum", "aconite", "monkshood", "wolfsbane", "foxglove", "digitalis",
        "belladonna", "deadly nightshade", "castor bean", "ricin", "oleander",
        "yew", "taxus", "hemlock", "conium", "pokeweed", "phytolacca",
        "jimsonweed", "datura", "angel trumpets", "brugmansia", "manchineel",
        "strychnine", "nux vomica", "cerbera", "suicide tree", "rosary pea",
        "abrin", "coral tree", "ergot", "claviceps"
    }
    
    # Compounds that require expert review
    HIGH_RISK_COMPOUNDS = {
        "alkaloids", "glycosides", "saponins", "tannins", "coumarins",
        "pyrrolizidine", "hepatotoxic", "nephrotoxic", "cardiotoxic",
        "neurotoxic", "phototoxic", "abortifacient", "emmenagogue"
    }
    
    # Valid recipe categories from database schema
    VALID_CATEGORIES = {
        "Remedy", "Salve", "Balm", "Shampoo", "Tea", "Tincture", 
        "Syrup", "Poultice", "Compress", "Rinse"
    }
    
    # Valid administration routes
    VALID_ROUTES = {
        "topical", "oral", "otic", "inhaled", "rinse", "compress"
    }
    
    # Valid sanitation levels
    VALID_SANITATION_LEVELS = {
        "sterile", "clean", "basic"
    }
    
    def __init__(self):
        """Initialize validation service with safety databases."""
        self.validation_history: List[Dict[str, Any]] = []
    
    def validate_recipe_data(self, recipe: ParsedRecipe) -> ValidationResult:
        """
        Comprehensive validation of recipe data.
        
        Validates all fields for completeness, format, and safety.
        Never silently accepts invalid data - all issues are reported.
        
        Args:
            recipe: ParsedRecipe object to validate
            
        Returns:
            ValidationResult with detailed validation feedback
        """
        result = ValidationResult(is_valid=True)
        
        # Required field validation
        if not recipe.name or not recipe.name.strip():
            result.add_field_error("name", "Recipe name is required")
        elif len(recipe.name.strip()) > 200:
            result.add_field_error("name", "Recipe name too long (max 200 characters)")
        
        if not recipe.description or not recipe.description.strip():
            result.add_field_error("description", "Recipe description is required")
        
        if not recipe.instructions or not recipe.instructions.strip():
            result.add_field_error("instructions", "Recipe instructions are required")
        
        if not recipe.category:
            result.add_field_error("category", "Recipe category is required")
        elif recipe.category not in self.VALID_CATEGORIES:
            result.add_field_error(
                "category", 
                f"Invalid category '{recipe.category}'. Must be one of: {', '.join(self.VALID_CATEGORIES)}"
            )
        
        # Route validation
        if recipe.route and recipe.route not in self.VALID_ROUTES:
            result.add_field_error(
                "route",
                f"Invalid route '{recipe.route}'. Must be one of: {', '.join(self.VALID_ROUTES)}"
            )
        
        # Sanitation level validation
        if recipe.sanitation_level and recipe.sanitation_level not in self.VALID_SANITATION_LEVELS:
            result.add_field_error(
                "sanitation_level",
                f"Invalid sanitation level '{recipe.sanitation_level}'. Must be one of: {', '.join(self.VALID_SANITATION_LEVELS)}"
            )
        
        # Numeric field validation
        if recipe.shelf_life_days < 0:
            result.add_field_error("shelf_life_days", "Shelf life cannot be negative")
        elif recipe.shelf_life_days > 3650:  # 10 years max
            result.add_field_error("shelf_life_days", "Shelf life seems unrealistic (max 10 years)")
        
        if recipe.batch_size_value < 0:
            result.add_field_error("batch_size_value", "Batch size cannot be negative")
        elif recipe.batch_size_value > 10000:  # Reasonable upper limit
            result.add_field_error("batch_size_value", "Batch size seems unrealistic")
        
        # Ingredients validation
        if not recipe.ingredients:
            result.add_field_error("ingredients", "Recipe must have at least one ingredient")
        elif len(recipe.ingredients) > 50:
            result.add_field_error("ingredients", "Too many ingredients (max 50)")
        
        # Safety content validation
        dangerous_content = self._check_recipe_for_dangerous_content(recipe)
        for warning in dangerous_content:
            result.add_safety_warning(warning)
        
        # Critical safety issues
        critical_issues = self._check_for_critical_safety_issues(recipe)
        for issue in critical_issues:
            result.add_critical_issue(issue)
        
        # Log validation attempt
        self.validation_history.append({
            "type": "recipe",
            "recipe_name": recipe.name,
            "is_valid": result.is_valid,
            "error_count": len(result.get_all_errors()),
            "safety_warnings": len(result.safety_warnings)
        })
        
        return result
    
    def validate_herb_safety(self, herb: ParsedHerb) -> SafetyValidationResult:
        """
        Specialized safety validation for herb data.
        
        Focuses on identifying potentially dangerous herbs, compounds,
        and safety concerns that require user attention or expert review.
        
        Args:
            herb: ParsedHerb object to validate for safety
            
        Returns:
            SafetyValidationResult with detailed safety assessment
        """
        result = SafetyValidationResult(is_safe=True, confidence_level="medium")
        
        # Check for dangerous plant names
        herb_name_lower = herb.name.lower()
        scientific_name_lower = herb.scientific_name.lower()
        
        for dangerous_plant in self.DANGEROUS_PLANTS:
            if dangerous_plant in herb_name_lower or dangerous_plant in scientific_name_lower:
                result.add_dangerous_compound(
                    dangerous_plant,
                    f"Potentially dangerous plant identified in name or scientific name"
                )
                result.confidence_level = "high"
        
        # Check description and uses for dangerous compounds
        combined_text = f"{herb.description} {herb.traditional_uses} {herb.current_evidence_summary}".lower()
        
        for compound in self.HIGH_RISK_COMPOUNDS:
            if compound in combined_text:
                result.add_safety_concern(
                    f"Contains reference to {compound} - requires careful dosing and expert guidance"
                )
        
        # Analyze contraindications and interactions
        if herb.contraindications:
            contraindication_warnings = self._analyze_contraindications(herb.contraindications)
            for warning in contraindication_warnings:
                result.add_safety_concern(warning)
        
        if herb.interactions:
            interaction_warnings = self._analyze_interactions(herb.interactions)
            for warning in interaction_warnings:
                result.add_safety_concern(warning)
        
        # Check toxicity notes for severity indicators
        if herb.toxicity_notes:
            toxicity_level = self._assess_toxicity_level(herb.toxicity_notes)
            if toxicity_level == "high":
                result.requires_expert_review = True
                result.add_safety_concern("High toxicity risk identified - expert review required")
            elif toxicity_level == "moderate":
                result.add_safety_concern("Moderate toxicity risk - use with caution")
        
        # Validate required safety information
        if herb.has_safety_concerns() and not herb.contraindications.strip():
            result.add_safety_concern("Herb has safety concerns but missing contraindications")
        
        # Check for incomplete safety information
        if (any(keyword in combined_text for keyword in ["toxic", "poison", "dangerous", "death"]) 
            and not herb.toxicity_notes.strip()):
            result.add_safety_concern("References to toxicity found but no toxicity notes provided")
        
        return result
    
    def check_for_dangerous_content(self, text: str) -> List[str]:
        """
        Scan text content for dangerous instructions or substances.
        
        Args:
            text: Text content to analyze
            
        Returns:
            List of safety warnings for dangerous content found
        """
        warnings = []
        text_lower = text.lower()
        
        # Dangerous instruction patterns
        dangerous_patterns = [
            (r'inject|injection|intravenous|iv\s', "Injection methods are dangerous for home remedies"),
            (r'large doses?|overdose|massive amount', "References to large doses may be dangerous"),
            (r'children under|infant|baby|pregnancy', "Special populations require expert guidance"),
            (r'substitute.*medication|replace.*prescription', "Should never replace prescribed medications"),
            (r'medical emergency|heart attack|stroke', "Medical emergencies require professional treatment"),
        ]
        
        for pattern, warning in dangerous_patterns:
            if re.search(pattern, text_lower):
                warnings.append(warning)
        
        # Check for dangerous plant references
        for dangerous_plant in self.DANGEROUS_PLANTS:
            if dangerous_plant in text_lower:
                warnings.append(f"References potentially dangerous plant: {dangerous_plant}")
        
        return warnings
    
    def _check_recipe_for_dangerous_content(self, recipe: ParsedRecipe) -> List[str]:
        """Check recipe content for dangerous instructions or ingredients."""
        warnings = []
        
        # Check all text fields
        text_fields = [
            recipe.description, recipe.instructions, recipe.benefits,
            recipe.safety_summary, recipe.contraindications, recipe.interactions
        ]
        
        for field_text in text_fields:
            if field_text:
                field_warnings = self.check_for_dangerous_content(field_text)
                warnings.extend(field_warnings)
        
        # Check ingredients for dangerous substances
        for ingredient in recipe.ingredients:
            ingredient_warnings = self.check_for_dangerous_content(ingredient)
            warnings.extend(ingredient_warnings)
        
        return warnings
    
    def _check_for_critical_safety_issues(self, recipe: ParsedRecipe) -> List[str]:
        """Identify critical safety issues that prevent processing."""
        critical_issues = []
        
        # Check for explicitly dangerous instructions
        dangerous_instructions = [
            "inject", "intravenous", "iv drip", "surgical", "incision",
            "replace medication", "stop taking prescription"
        ]
        
        combined_text = f"{recipe.instructions} {recipe.description}".lower()
        
        for dangerous_instruction in dangerous_instructions:
            if dangerous_instruction in combined_text:
                critical_issues.append(
                    f"Contains dangerous instruction: {dangerous_instruction} - cannot process"
                )
        
        # Check for missing critical safety information
        if recipe.route == "oral" and not recipe.safety_summary.strip():
            critical_issues.append("Oral remedies require safety summary")
        
        return critical_issues
    
    def _analyze_contraindications(self, contraindications: str) -> List[str]:
        """Analyze contraindication text for safety concerns."""
        warnings = []
        text_lower = contraindications.lower()
        
        high_risk_indicators = [
            ("pregnancy", "Pregnancy contraindication requires special attention"),
            ("children", "Pediatric contraindication requires careful consideration"),
            ("liver", "Hepatic contraindication indicates potential toxicity"),
            ("kidney", "Renal contraindication indicates potential toxicity"),
            ("heart", "Cardiac contraindication requires medical supervision"),
        ]
        
        for indicator, warning in high_risk_indicators:
            if indicator in text_lower:
                warnings.append(warning)
        
        return warnings
    
    def _analyze_interactions(self, interactions: str) -> List[str]:
        """Analyze interaction text for drug interaction concerns."""
        warnings = []
        text_lower = interactions.lower()
        
        serious_interactions = [
            ("anticoagulant", "Blood thinning drug interactions can be dangerous"),
            ("antiplatelet", "Antiplatelet drug interactions increase bleeding risk"),
            ("diabetes", "Diabetes medication interactions affect blood sugar"),
            ("blood pressure", "Blood pressure medication interactions can be serious"),
            ("sedative", "Sedative interactions can cause dangerous drowsiness"),
            ("warfarin", "Warfarin interactions can be life-threatening"),
        ]
        
        for interaction_type, warning in serious_interactions:
            if interaction_type in text_lower:
                warnings.append(warning)
        
        return warnings
    
    def _assess_toxicity_level(self, toxicity_notes: str) -> str:
        """Assess the severity level of toxicity based on description."""
        text_lower = toxicity_notes.lower()
        
        # High toxicity indicators
        high_toxicity_indicators = [
            "fatal", "death", "lethal", "toxic", "poison", "dangerous",
            "severe", "hospitalization", "emergency", "liver damage"
        ]
        
        # Moderate toxicity indicators
        moderate_toxicity_indicators = [
            "nausea", "vomiting", "diarrhea", "skin irritation", "allergic",
            "sensitivity", "caution", "moderate"
        ]
        
        high_count = sum(1 for indicator in high_toxicity_indicators if indicator in text_lower)
        moderate_count = sum(1 for indicator in moderate_toxicity_indicators if indicator in text_lower)
        
        if high_count >= 2:
            return "high"
        elif high_count >= 1 or moderate_count >= 3:
            return "moderate"
        else:
            return "low"
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get statistics about validation operations."""
        if not self.validation_history:
            return {"total_validations": 0}
        
        total = len(self.validation_history)
        successful = sum(1 for v in self.validation_history if v["is_valid"])
        
        return {
            "total_validations": total,
            "successful_validations": successful,
            "failure_rate": (total - successful) / total if total > 0 else 0,
            "average_errors": sum(v["error_count"] for v in self.validation_history) / total,
            "safety_warnings": sum(v["safety_warnings"] for v in self.validation_history)
        }