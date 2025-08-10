"""
AI parsing service with enhanced LM Studio integration for recipe and herb extraction.

This service leverages the existing LM Studio client setup from scraper_ui.py
while providing comprehensive error handling, JSON repair capabilities, and
structured prompts for both recipe parsing and herb information extraction.
All AI failures are logged with complete context for debugging.
"""
import json
import re
import logging
from typing import Dict, Any, Optional, List
from openai import OpenAI

from .models import ParsedRecipe, ParsedHerb, AIParsingResult
from .data_sanitizer import DataSanitizer


class AIParsingService:
    """
    AI-powered parsing service for recipe and herb extraction.
    
    Integrates with LM Studio using the existing OpenAI client configuration
    while providing enhanced error handling, JSON repair, and detailed
    logging of all AI interactions. Never masks parsing failures.
    """
    
    def __init__(self, base_url: str = "http://localhost:1234/v1", api_key: str = "not-needed"):
        """
        Initialize AI parsing service with LM Studio configuration.
        
        Uses the same client setup as the existing scraper_ui.py to ensure
        compatibility with the user's LM Studio installation.
        
        Args:
            base_url: LM Studio server URL
            api_key: API key (not needed for local LM Studio)
        """
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.max_context_chars = 14000  # Safe limit for most local models
        self.parsing_history: List[Dict[str, Any]] = []
    
    def parse_recipe(self, text: str, source_url: str = "") -> AIParsingResult:
        """
        Parse recipe information from scraped text content.
        
        Uses enhanced prompts with strict validation rules and comprehensive
        field mapping to extract complete recipe data. All parsing failures
        are captured with full context for debugging.
        
        Args:
            text: Raw scraped text content
            source_url: Optional source URL for context
            
        Returns:
            AIParsingResult with parsed data or detailed error information
        """
        result = AIParsingResult(success=False)
        
        # Truncate text if too long for model context
        if len(text) > self.max_context_chars:
            logging.warning(f"Text truncated from {len(text)} to {self.max_context_chars} chars")
            text = text[:self.max_context_chars]
            result.add_confidence_indicator("text_truncated", True)
        
        # Wrap text with clear boundaries
        wrapped_text = f"---BEGIN RECIPE TEXT---\n{text}\n---END RECIPE TEXT---"
        result.set_raw_response(wrapped_text[:500] + "..." if len(wrapped_text) > 500 else wrapped_text)
        
        try:
            # Get AI response using enhanced recipe parsing prompt
            completion = self.client.chat.completions.create(
                model="local-model",
                messages=[
                    {"role": "system", "content": self._get_recipe_parsing_prompt()},
                    {"role": "user", "content": wrapped_text}
                ],
                temperature=0.3,  # Lower temperature for more consistent parsing
            )
            
            response_text = completion.choices[0].message.content
            result.set_raw_response(response_text)
            
            # Parse and repair JSON response
            parsed_data = self._parse_and_repair_json(response_text, result)
            if parsed_data:
                # Validate parsed data structure
                recipe = self._convert_to_parsed_recipe(parsed_data, result)
                if recipe:
                    result.parsed_data = parsed_data
                    result.success = True
                    result.add_confidence_indicator("field_completeness", self._assess_field_completeness(parsed_data))
                    
        except Exception as e:
            result.add_parsing_error(f"AI parsing request failed: {str(e)}")
            logging.error(f"Recipe parsing failed: {e}")
        
        # Log parsing attempt for debugging
        self.parsing_history.append({
            "type": "recipe",
            "source_url": source_url,
            "success": result.success,
            "text_length": len(text),
            "errors": len(result.parsing_errors),
            "json_repairs": result.json_repair_attempts
        })
        
        return result
    
    def extract_herb_info(self, herb_name: str, context: str = "") -> AIParsingResult:
        """
        Extract comprehensive herb information using AI.
        
        Uses specialized prompts to gather detailed herb information including
        safety data, traditional uses, and modern evidence. All extraction
        attempts are logged with full context.
        
        Args:
            herb_name: Name of herb to extract information for
            context: Optional context from recipe or other source
            
        Returns:
            AIParsingResult with extracted herb data or error details
        """
        result = AIParsingResult(success=False)
        
        prompt_text = f"Extract comprehensive information for herb: {herb_name}"
        if context:
            prompt_text += f"\n\nContext: {context[:1000]}"  # Limit context length
        
        try:
            completion = self.client.chat.completions.create(
                model="local-model",
                messages=[
                    {"role": "system", "content": self._get_herb_extraction_prompt()},
                    {"role": "user", "content": prompt_text}
                ],
                temperature=0.4,
            )
            
            response_text = completion.choices[0].message.content
            result.set_raw_response(response_text)
            
            # Parse and validate herb data
            parsed_data = self._parse_and_repair_json(response_text, result)
            if parsed_data:
                herb = self._convert_to_parsed_herb(parsed_data, result)
                if herb:
                    result.parsed_data = parsed_data
                    result.success = True
                    result.add_confidence_indicator("safety_info_present", bool(
                        parsed_data.get("contraindications") or 
                        parsed_data.get("interactions") or 
                        parsed_data.get("toxicity_notes")
                    ))
                    
        except Exception as e:
            result.add_parsing_error(f"Herb extraction failed: {str(e)}")
            logging.error(f"Herb extraction failed for '{herb_name}': {e}")
        
        # Log extraction attempt
        self.parsing_history.append({
            "type": "herb",
            "herb_name": herb_name,
            "success": result.success,
            "has_context": bool(context),
            "errors": len(result.parsing_errors),
            "json_repairs": result.json_repair_attempts
        })
        
        return result
    
    def validate_parsed_data(self, data: Dict[str, Any], data_type: str = "recipe") -> AIParsingResult:
        """
        Validate parsed data structure and completeness.
        
        Performs comprehensive validation of AI-parsed data to ensure
        all required fields are present and properly formatted.
        
        Args:
            data: Parsed data dictionary
            data_type: Type of data ("recipe" or "herb")
            
        Returns:
            AIParsingResult with validation results
        """
        result = AIParsingResult(success=True, parsed_data=data)
        
        if data_type == "recipe":
            required_fields = ["name", "description", "instructions", "benefits", "category"]
            for field in required_fields:
                if not data.get(field, "").strip():
                    result.add_parsing_error(f"Missing required field: {field}")
            
            # Validate ingredients list
            if not isinstance(data.get("ingredients", []), list):
                result.add_parsing_error("Ingredients must be a list")
            
            # Check numeric fields
            try:
                int(data.get("shelf_life_days", 0))
                float(data.get("batch_size_value", 0))
            except (ValueError, TypeError):
                result.add_parsing_error("Invalid numeric field values")
                
        elif data_type == "herb":
            required_fields = ["name", "description"]
            for field in required_fields:
                if not data.get(field, "").strip():
                    result.add_parsing_error(f"Missing required field: {field}")
        
        result.add_confidence_indicator("validation_passed", result.success)
        return result
    
    def _get_recipe_parsing_prompt(self) -> str:
        """Get the enhanced recipe parsing prompt with strict validation."""
        return """
You are an expert Herbal Recipe Parser. Extract recipe information with STRICT field mapping and comprehensive error checking.

CRITICAL RULES:
- Return ONLY valid JSON - no commentary, no markdown formatting
- Use double quotes for all keys and strings
- If you cannot confidently determine a field value, use empty string "" rather than guessing
- Never invent safety information - only extract what is explicitly stated
- Preserve original formatting in instructions using \\n for line breaks
- All numeric fields must be actual numbers, not strings

Required JSON structure with ALL fields:
{
  "name": "exact recipe name",
  "description": "brief description", 
  "instructions": "step by step with \\n separators",
  "benefits": "health/therapeutic benefits",
  "category": "Remedy|Salve|Balm|Shampoo|Tea|Tincture|Syrup|Poultice|Compress|Rinse",
  "route": "topical|oral|otic|inhaled|rinse|compress",
  "safety_summary": "general safety notes if present",
  "contraindications": "when NOT to use - only if explicitly stated",
  "interactions": "drug/supplement interactions - only if explicitly stated",
  "pediatric_note": "children-specific guidance if present", 
  "pregnancy_note": "pregnancy-specific guidance if present",
  "sanitation_level": "sterile|clean|basic - only if mentioned",
  "storage_instructions": "how to store finished product",
  "shelf_life_days": 0,
  "batch_size_value": 0.0,
  "batch_size_unit": "ml|oz|cups|servings|drops",
  "ingredients": ["ingredient 1", "ingredient 2"],
  "unknown_herbs": ["herbs not commonly known"]
}

SAFETY VALIDATION:
- Never minimize or omit safety warnings
- Flag any potentially dangerous instructions
- Mark uncertain information with qualifying language
- Include dosage warnings if present
- Preserve all contraindication details

FIELD EXTRACTION RULES:
- name: Extract the main recipe title
- category: Match to one of the specified categories or use "Remedy" as default
- route: How the remedy is administered/used
- instructions: Merge all procedural steps, preserve order and timing
- ingredients: List each ingredient as separate string
- unknown_herbs: Only herbs that seem unusual or not commonly known
- shelf_life_days: Convert time periods to days (e.g., "2 weeks" = 14)
- batch_size: Extract yield information if mentioned

QUALITY CHECKS:
- Instructions should have at least 2-3 steps for most recipes
- Ingredients list should not be empty
- Safety information should only include what's explicitly stated
- Never fabricate contraindications or interactions
"""
    
    def _get_herb_extraction_prompt(self) -> str:
        """Get the specialized herb information extraction prompt."""
        return """
You are an expert herbalist knowledge extractor. Provide comprehensive, accurate information about herbs with strict safety focus.

CRITICAL SAFETY RULES:
- Only include well-documented, verifiable information
- Never minimize safety concerns or contraindications
- Mark uncertain or controversial information clearly
- Use empty strings for unverified information
- Focus on traditional AND modern scientific evidence

Required JSON structure:
{
  "name": "common name of herb",
  "description": "physical description and growing characteristics",
  "scientific_name": "Latin binomial name if known", 
  "traditional_uses": "historical and folk medicine applications",
  "craft_uses": "cosmetic, soap, potpourri, craft applications",
  "current_evidence_summary": "modern research findings and clinical studies",
  "contraindications": "specific conditions when herb should be avoided",
  "interactions": "known drug or supplement interactions", 
  "toxicity_notes": "safety concerns, dosage limits, adverse effects"
}

INFORMATION QUALITY STANDARDS:
- All safety information must be based on documented sources
- Traditional uses should reflect historical applications
- Current evidence should reference real research when possible
- Never downplay or omit known risks
- Include both topical and internal use considerations
- Mention special populations (pregnancy, children, elderly) when relevant

EXTRACTION APPROACH:
- Provide detailed but concise information
- Focus on practical, actionable information
- Include preparation and dosage considerations in appropriate fields
- Distinguish between traditional beliefs and scientific evidence
- Be conservative with safety assessments

QUALITY VERIFICATION:
- Scientific name should follow proper botanical nomenclature
- Safety information should be comprehensive and conservative
- Traditional uses should be historically accurate
- Evidence summary should distinguish between preliminary and established research
"""
    
    def _parse_and_repair_json(self, response_text: str, result: AIParsingResult) -> Optional[Dict[str, Any]]:
        """
        Parse JSON response with comprehensive repair attempts.
        
        Uses the existing JSON repair logic from scraper_ui.py while
        adding additional repair strategies and detailed error logging.
        """
        # Clean response text
        cleaned = response_text.strip().replace("```json", "").replace("```", "")
        
        try:
            # Try direct parsing first
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Attempt repair using existing logic
            result.increment_repair_attempts()
            
        try:
            # Use the existing repair function from scraper_ui.py
            repaired_json = self._repair_and_extract_json(cleaned)
            result.increment_repair_attempts()
            return json.loads(repaired_json)
        except (ValueError, json.JSONDecodeError) as e:
            result.add_parsing_error(f"JSON repair failed: {str(e)}")
            
        # Additional repair attempts
        try:
            # Try extracting just the JSON object
            json_match = re.search(r'\{.*\}', cleaned, flags=re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                result.increment_repair_attempts()
                return json.loads(json_text)
        except json.JSONDecodeError:
            pass
        
        # Final attempt: fix common issues
        try:
            # Fix trailing commas and quotes
            fixed = re.sub(r',\s*([}\]])', r'\1', cleaned)
            fixed = re.sub(r'([,{]\s*)\'([^\']*?)\'\s*:', r'\1"\2":', fixed)
            result.increment_repair_attempts()
            return json.loads(fixed)
        except json.JSONDecodeError as e:
            result.add_parsing_error(f"All JSON repair attempts failed: {str(e)}")
        
        return None
    
    def _repair_and_extract_json(self, s: str) -> str:
        """
        Repair and extract JSON using the existing logic from scraper_ui.py.
        
        This maintains compatibility with the existing repair strategies
        while being integrated into the new service architecture.
        """
        # Grab the first {...} block
        m = re.search(r'\{.*\}', s, flags=re.S)
        if not m:
            raise ValueError("No JSON object found")
        j = m.group(0)

        # Normalize smart quotes
        j = j.replace('"','"').replace('"','"').replace("'","'").replace("'","'")

        # Remove accidental trailing commas before } or ]
        j = re.sub(r',\s*([\}\]])', r'\1', j)

        # Enforce double quotes on keys and string values where single quotes slipped in
        j = re.sub(r'([,{]\s*)\'([^\'"]+?)\'\s*:', r'\1"\2":', j)
        j = re.sub(r':\s*\'([^\']*)\'', r': "\1"', j)

        # Ensure "instructions" is a single string with escaped newlines
        def esc_newlines(match):
            inner = match.group(1)
            inner = inner.replace('\\', '\\\\').replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\\n')
            return f'"instructions":"{inner}"'
        j = re.sub(r'"instructions"\s*:\s*"([\s\S]*?)"', esc_newlines, j)

        return j
    
    def _convert_to_parsed_recipe(self, data: Dict[str, Any], result: AIParsingResult) -> Optional[ParsedRecipe]:
        """Convert parsed JSON data to ParsedRecipe object with validation and sanitization."""
        try:
            # Sanitize all recipe data before creating object
            sanitized_data = DataSanitizer.sanitize_recipe_data(data)
            
            recipe = ParsedRecipe(
                name=sanitized_data.get("name", ""),
                description=sanitized_data.get("description", ""),
                instructions=sanitized_data.get("instructions", ""),
                benefits=sanitized_data.get("benefits", ""),
                category=sanitized_data.get("category", ""),
                route=sanitized_data.get("route", ""),
                safety_summary=sanitized_data.get("safety_summary", ""),
                contraindications=sanitized_data.get("contraindications", ""),
                interactions=sanitized_data.get("interactions", ""),
                pediatric_note=sanitized_data.get("pediatric_note", ""),
                pregnancy_note=sanitized_data.get("pregnancy_note", ""),
                sanitation_level=sanitized_data.get("sanitation_level", ""),
                storage_instructions=sanitized_data.get("storage_instructions", ""),
                shelf_life_days=int(data.get("shelf_life_days", 0)),
                batch_size_value=float(data.get("batch_size_value", 0.0)),
                batch_size_unit=sanitized_data.get("batch_size_unit", ""),
                ingredients=data.get("ingredients", []),
                unknown_herbs=data.get("unknown_herbs", [])
            )
            return recipe
        except (ValueError, TypeError) as e:
            result.add_parsing_error(f"Failed to convert to ParsedRecipe: {str(e)}")
            return None
    
    def _convert_to_parsed_herb(self, data: Dict[str, Any], result: AIParsingResult) -> Optional[ParsedHerb]:
        """Convert parsed JSON data to ParsedHerb object with validation and sanitization."""
        try:
            # Sanitize all herb data before creating object
            sanitized_data = DataSanitizer.sanitize_herb_data(data)
            
            herb = ParsedHerb(
                name=sanitized_data.get("name", ""),
                description=sanitized_data.get("description", ""),
                scientific_name=sanitized_data.get("scientific_name", ""),
                traditional_uses=sanitized_data.get("traditional_uses", ""),
                craft_uses=sanitized_data.get("craft_uses", ""),
                current_evidence_summary=sanitized_data.get("current_evidence_summary", ""),
                contraindications=sanitized_data.get("contraindications", ""),
                interactions=sanitized_data.get("interactions", ""),
                toxicity_notes=sanitized_data.get("toxicity_notes", ""),
                symbol=sanitized_data.get("symbol", "🌿")
            )
            return herb
        except (ValueError, TypeError) as e:
            result.add_parsing_error(f"Failed to convert to ParsedHerb: {str(e)}")
            return None
    
    def _assess_field_completeness(self, data: Dict[str, Any]) -> float:
        """Assess what percentage of fields have meaningful content."""
        total_fields = len(data)
        filled_fields = sum(1 for value in data.values() 
                           if isinstance(value, str) and value.strip() or
                           isinstance(value, (int, float)) and value != 0 or
                           isinstance(value, list) and len(value) > 0)
        
        return filled_fields / total_fields if total_fields > 0 else 0.0
    
    def get_parsing_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about parsing operations."""
        if not self.parsing_history:
            return {"total_operations": 0}
        
        total = len(self.parsing_history)
        successful = sum(1 for op in self.parsing_history if op["success"])
        recipe_ops = [op for op in self.parsing_history if op["type"] == "recipe"]
        herb_ops = [op for op in self.parsing_history if op["type"] == "herb"]
        
        return {
            "total_operations": total,
            "successful_operations": successful,
            "success_rate": successful / total if total > 0 else 0,
            "recipe_operations": len(recipe_ops),
            "herb_operations": len(herb_ops),
            "average_json_repairs": sum(op.get("json_repairs", 0) for op in self.parsing_history) / total,
            "operations_with_errors": sum(1 for op in self.parsing_history if op.get("errors", 0) > 0)
        }