"""
Data models and result classes for the enhanced scraper system.

This module defines the core data structures used throughout the scraping workflow,
including parsed recipe and herb data, operation results, and validation outcomes.
All models align with the existing database schema and provide comprehensive
error tracking for transparent failure handling.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from datetime import datetime


@dataclass
class ParsedRecipe:
    """
    Represents a recipe parsed from scraped content.
    
    All fields map directly to the Recipe model in database.py to ensure
    seamless database integration. Fields that cannot be confidently
    determined should be left as empty strings rather than guessed values.
    """
    name: str
    description: str
    instructions: str
    benefits: str
    category: str
    route: str
    safety_summary: str
    contraindications: str
    interactions: str
    pediatric_note: str
    pregnancy_note: str
    sanitation_level: str
    storage_instructions: str
    shelf_life_days: int
    batch_size_value: float
    batch_size_unit: str
    ingredients: List[str] = field(default_factory=list)
    unknown_herbs: List[str] = field(default_factory=list)
    
    def get_required_herb_names(self) -> List[str]:
        """Extract herb names from ingredients list"""
        # This will be enhanced to intelligently parse ingredient text
        return [ing.strip() for ing in self.ingredients if ing.strip()]


@dataclass
class ParsedHerb:
    """
    Represents an herb with comprehensive information extracted via AI.
    
    Maps to the Herb model in database.py with all fields populated
    through intelligent parsing. Safety-related fields (contraindications,
    interactions, toxicity_notes) must never be minimized or guessed.
    """
    name: str
    description: str
    scientific_name: str
    traditional_uses: str
    craft_uses: str
    current_evidence_summary: str
    contraindications: str
    interactions: str
    toxicity_notes: str
    symbol: str = "🌿"
    
    def has_safety_concerns(self) -> bool:
        """Check if herb has any documented safety concerns"""
        return bool(self.contraindications.strip() or 
                   self.interactions.strip() or 
                   self.toxicity_notes.strip())


@dataclass
class ScrapingResult:
    """
    Comprehensive result of a scraping operation.
    
    Provides transparent reporting of all outcomes including successes,
    failures, and debugging information. Critical for ensuring no errors
    are masked by fallback behaviors.
    """
    success: bool
    recipe_id: Optional[int] = None
    new_herbs_added: List[int] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    debug_info: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def add_error(self, error: str, context: Optional[Dict[str, Any]] = None):
        """Add an error with optional context for debugging"""
        self.errors.append(error)
        if context:
            self.debug_info[f"error_{len(self.errors)}"] = context
    
    def add_warning(self, warning: str, context: Optional[Dict[str, Any]] = None):
        """Add a warning with optional context"""
        self.warnings.append(warning)
        if context:
            self.debug_info[f"warning_{len(self.warnings)}"] = context
    
    def has_errors(self) -> bool:
        """Check if operation had any errors"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if operation had any warnings"""
        return len(self.warnings) > 0


@dataclass
class ValidationResult:
    """
    Result of data validation operations.
    
    Provides detailed field-level validation feedback and safety assessments.
    Never silently passes invalid data - all issues are explicitly reported.
    """
    is_valid: bool
    field_errors: Dict[str, List[str]] = field(default_factory=dict)
    safety_warnings: List[str] = field(default_factory=list)
    critical_issues: List[str] = field(default_factory=list)
    
    def add_field_error(self, field_name: str, error: str):
        """Add a field-specific validation error"""
        if field_name not in self.field_errors:
            self.field_errors[field_name] = []
        self.field_errors[field_name].append(error)
        self.is_valid = False
    
    def add_safety_warning(self, warning: str):
        """Add a safety-related warning"""
        self.safety_warnings.append(warning)
    
    def add_critical_issue(self, issue: str):
        """Add a critical issue that prevents processing"""
        self.critical_issues.append(issue)
        self.is_valid = False
    
    def get_all_errors(self) -> List[str]:
        """Get all errors as a flat list"""
        all_errors = []
        for field, errors in self.field_errors.items():
            for error in errors:
                all_errors.append(f"{field}: {error}")
        all_errors.extend(self.critical_issues)
        return all_errors


@dataclass
class SafetyValidationResult:
    """
    Specialized validation result for herb safety assessment.
    
    Focuses on identifying potentially dangerous content, contraindications,
    and interactions that require user attention before database storage.
    """
    is_safe: bool
    dangerous_compounds: List[str] = field(default_factory=list)
    safety_concerns: List[str] = field(default_factory=list)
    requires_expert_review: bool = False
    confidence_level: str = "unknown"  # low, medium, high
    
    def add_dangerous_compound(self, compound: str, concern: str):
        """Add a potentially dangerous compound with explanation"""
        self.dangerous_compounds.append(f"{compound}: {concern}")
        self.is_safe = False
        self.requires_expert_review = True
    
    def add_safety_concern(self, concern: str):
        """Add a general safety concern"""
        self.safety_concerns.append(concern)


@dataclass
class DatabaseResult:
    """
    Result of database operations with detailed error tracking.
    
    Captures transaction success/failure, constraint violations, and
    provides context for debugging database-related issues.
    """
    success: bool
    affected_rows: int = 0
    new_record_id: Optional[int] = None
    errors: List[str] = field(default_factory=list)
    sql_error: Optional[str] = None
    constraint_violations: List[str] = field(default_factory=list)
    
    def add_error(self, error: str, sql_error: Optional[str] = None):
        """Add a database error with optional SQL context"""
        self.errors.append(error)
        if sql_error:
            self.sql_error = sql_error
        self.success = False
    
    def add_constraint_violation(self, violation: str):
        """Add a database constraint violation"""
        self.constraint_violations.append(violation)
        self.success = False


@dataclass
class HerbMatchResult:
    """
    Result of herb matching operations for deduplication.
    
    Handles fuzzy matching, scientific name conflicts, and provides
    user-actionable recommendations for resolving herb duplicates.
    """
    exact_match: Optional[int] = None  # herb_id of exact match
    similar_matches: List[Dict[str, Any]] = field(default_factory=list)
    scientific_name_conflicts: List[Dict[str, Any]] = field(default_factory=list)
    recommended_action: str = "create_new"  # create_new, use_existing, user_review
    confidence_score: float = 0.0
    
    def add_similar_match(self, herb_id: int, name: str, similarity: float, reason: str):
        """Add a similar herb match with confidence score"""
        self.similar_matches.append({
            "herb_id": herb_id,
            "name": name,
            "similarity": similarity,
            "reason": reason
        })
    
    def add_scientific_name_conflict(self, herb_id: int, name: str, scientific_name: str):
        """Add a scientific name conflict that needs resolution"""
        self.scientific_name_conflicts.append({
            "herb_id": herb_id,
            "name": name,
            "scientific_name": scientific_name
        })
        self.recommended_action = "user_review"
    
    def has_conflicts(self) -> bool:
        """Check if there are any matching conflicts requiring user input"""
        return (len(self.similar_matches) > 0 or 
                len(self.scientific_name_conflicts) > 0 or
                self.recommended_action == "user_review")


@dataclass
class AIParsingResult:
    """
    Result of AI-powered parsing operations.
    
    Captures both successful parsing and detailed failure information
    for debugging AI response issues. Never masks parsing failures.
    """
    success: bool
    parsed_data: Optional[Dict[str, Any]] = None
    raw_response: str = ""
    parsing_errors: List[str] = field(default_factory=list)
    json_repair_attempts: int = 0
    confidence_indicators: Dict[str, Any] = field(default_factory=dict)
    
    def add_parsing_error(self, error: str):
        """Add a parsing error with context"""
        self.parsing_errors.append(error)
        self.success = False
    
    def set_raw_response(self, response: str):
        """Store the raw AI response for debugging"""
        self.raw_response = response
    
    def increment_repair_attempts(self):
        """Track JSON repair attempts"""
        self.json_repair_attempts += 1
    
    def add_confidence_indicator(self, indicator: str, value: Any):
        """Add confidence indicators for parsing quality"""
        self.confidence_indicators[indicator] = value