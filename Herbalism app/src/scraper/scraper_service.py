"""
Orchestration service that coordinates all scraping operations.

This service acts as the main coordinator for the complete scraping workflow,
from URL fetching through AI parsing to database storage. It integrates all
other services while ensuring comprehensive error aggregation and transparent
failure reporting with no error masking.
"""
import logging
import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin
import time
from typing import List, Dict, Any, Optional, Tuple

from .models import ScrapingResult, ParsedRecipe, ParsedHerb
from .ai_parsing_service import AIParsingService
from .database_service import DatabaseService
from .validation_service import ValidationService


class ScraperService:
    """
    Main orchestration service for complete scraping workflows.
    
    Coordinates URL fetching, AI parsing, validation, and database storage
    with comprehensive error aggregation. Ensures all component errors are
    captured and exposed to users with full context for debugging.
    """
    
    # Configuration constants
    USER_AGENT = "HerbalAlchemyRecipeBot/1.0"
    REQUEST_TIMEOUT = 10
    ROBOTS_DELAY = 1  # Respectful delay for robots.txt checking
    
    def __init__(self, lm_studio_url: str = "http://localhost:1234/v1"):
        """
        Initialize scraper service with all component services.
        
        Args:
            lm_studio_url: LM Studio server URL for AI parsing
        """
        self.ai_service = AIParsingService(base_url=lm_studio_url)
        self.db_service = DatabaseService()
        self.validation_service = ValidationService()
        
        # Comprehensive operation tracking
        self.operation_history: List[Dict[str, Any]] = []
        
        # Configure logging for detailed debugging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def scrape_and_save_recipe(self, url: str) -> ScrapingResult:
        """
        Complete workflow: URL → scraping → parsing → validation → database.
        
        Orchestrates the entire process from URL fetching through database
        storage with comprehensive error tracking and aggregation. All
        failures are captured with full context.
        
        Args:
            url: URL of recipe page to scrape
            
        Returns:
            ScrapingResult with detailed operation feedback
        """
        result = ScrapingResult(success=False)
        result.debug_info["source_url"] = url
        result.debug_info["operation_type"] = "full_scrape"
        
        self.logger.info(f"Starting complete scrape workflow for: {url}")
        
        try:
            # Step 1: Check robots.txt and fetch content
            page_text, main_content_found = self._fetch_page_content(url, result)
            if not page_text:
                self.logger.error(f"Failed to fetch content from {url}")
                return result
            
            result.debug_info["content_length"] = len(page_text)
            result.debug_info["main_content_found"] = main_content_found
            
            # Step 2: Parse recipe with AI
            parsing_result = self.ai_service.parse_recipe(page_text, url)
            result.debug_info["ai_parsing"] = {
                "success": parsing_result.success,
                "errors": parsing_result.parsing_errors,
                "json_repairs": parsing_result.json_repair_attempts,
                "raw_response_length": len(parsing_result.raw_response)
            }
            
            if not parsing_result.success:
                result.add_error("AI parsing failed", {
                    "parsing_errors": parsing_result.parsing_errors,
                    "raw_response": parsing_result.raw_response
                })
                return result
            
            # Convert to ParsedRecipe object
            recipe = self.ai_service._convert_to_parsed_recipe(parsing_result.parsed_data, parsing_result)
            if not recipe:
                result.add_error("Failed to convert parsed data to recipe object")
                return result
            
            # Step 3: Validate recipe data
            validation_result = self.validation_service.validate_recipe_data(recipe)
            result.debug_info["validation"] = {
                "is_valid": validation_result.is_valid,
                "field_errors": validation_result.field_errors,
                "safety_warnings": validation_result.safety_warnings,
                "critical_issues": validation_result.critical_issues
            }
            
            # Add validation warnings to result
            for warning in validation_result.safety_warnings:
                result.add_warning(f"Safety validation: {warning}")
            
            # Stop if critical validation issues
            if validation_result.critical_issues:
                for issue in validation_result.critical_issues:
                    result.add_error(f"Critical validation failure: {issue}")
                return result
            
            # Step 4: Process unknown herbs
            new_herbs = []
            if recipe.unknown_herbs:
                herbs_result = self._process_unknown_herbs(recipe.unknown_herbs, result)
                new_herbs = herbs_result
            
            result.debug_info["herb_processing"] = {
                "unknown_herbs_count": len(recipe.unknown_herbs),
                "new_herbs_created": len(new_herbs)
            }
            
            # Step 5: Save to database
            db_result = self.db_service.save_recipe_with_herbs(recipe, new_herbs)
            result.debug_info["database"] = {
                "success": db_result.success,
                "errors": db_result.errors,
                "affected_rows": db_result.affected_rows,
                "constraint_violations": db_result.constraint_violations
            }
            
            if not db_result.success:
                for error in db_result.errors:
                    result.add_error(f"Database error: {error}")
                if db_result.sql_error:
                    result.debug_info["sql_error"] = db_result.sql_error
                return result
            
            # Success!
            result.success = True
            result.recipe_id = db_result.new_record_id
            result.new_herbs_added = [herb.name for herb in new_herbs]
            
            self.logger.info(f"Successfully scraped and saved recipe '{recipe.name}' with ID {result.recipe_id}")
            
        except Exception as e:
            result.add_error(f"Unexpected error in scraping workflow: {str(e)}")
            self.logger.error(f"Scraping workflow failed: {e}", exc_info=True)
        
        # Log operation for statistics
        self._log_operation("full_scrape", url, result)
        
        return result
    
    def parse_and_save_recipe(self, text: str, source_description: str = "manual_input") -> ScrapingResult:
        """
        Parse recipe from provided text and save to database.
        
        Handles cases where users provide recipe text directly rather than
        URLs, with the same comprehensive validation and error handling.
        
        Args:
            text: Recipe text content to parse
            source_description: Description of text source for logging
            
        Returns:
            ScrapingResult with detailed operation feedback
        """
        result = ScrapingResult(success=False)
        result.debug_info["source_description"] = source_description
        result.debug_info["operation_type"] = "text_parse"
        result.debug_info["text_length"] = len(text)
        
        self.logger.info(f"Starting text parsing workflow for: {source_description}")
        
        try:
            # Step 1: Parse with AI
            parsing_result = self.ai_service.parse_recipe(text, source_description)
            result.debug_info["ai_parsing"] = {
                "success": parsing_result.success,
                "errors": parsing_result.parsing_errors,
                "json_repairs": parsing_result.json_repair_attempts
            }
            
            if not parsing_result.success:
                result.add_error("AI parsing failed", {
                    "parsing_errors": parsing_result.parsing_errors,
                    "raw_response": parsing_result.raw_response
                })
                return result
            
            # Convert to recipe object
            recipe = self.ai_service._convert_to_parsed_recipe(parsing_result.parsed_data, parsing_result)
            if not recipe:
                result.add_error("Failed to convert parsed data to recipe object")
                return result
            
            # Step 2: Validation (same as URL scraping)
            validation_result = self.validation_service.validate_recipe_data(recipe)
            
            # Add validation feedback to result
            for warning in validation_result.safety_warnings:
                result.add_warning(f"Safety validation: {warning}")
            
            if validation_result.critical_issues:
                for issue in validation_result.critical_issues:
                    result.add_error(f"Critical validation failure: {issue}")
                return result
            
            # Step 3: Process herbs and save (same logic as URL scraping)
            new_herbs = []
            if recipe.unknown_herbs:
                herbs_result = self._process_unknown_herbs(recipe.unknown_herbs, result)
                new_herbs = herbs_result
            
            db_result = self.db_service.save_recipe_with_herbs(recipe, new_herbs)
            
            if not db_result.success:
                for error in db_result.errors:
                    result.add_error(f"Database error: {error}")
                return result
            
            # Success
            result.success = True
            result.recipe_id = db_result.new_record_id
            result.new_herbs_added = [herb.name for herb in new_herbs]
            
            self.logger.info(f"Successfully parsed and saved recipe '{recipe.name}' from text input")
            
        except Exception as e:
            result.add_error(f"Unexpected error in text parsing workflow: {str(e)}")
            self.logger.error(f"Text parsing workflow failed: {e}", exc_info=True)
        
        self._log_operation("text_parse", source_description, result)
        return result
    
    def extract_and_validate_herb(self, herb_name: str, context: str = "") -> Tuple[Optional[ParsedHerb], List[str]]:
        """
        Extract herb information and perform safety validation.
        
        Used for processing unknown herbs discovered during recipe parsing.
        Returns both the herb data and any validation warnings.
        
        Args:
            herb_name: Name of herb to extract information for
            context: Optional context from recipe
            
        Returns:
            Tuple of (ParsedHerb object or None, list of validation warnings)
        """
        warnings = []
        
        try:
            # Extract herb information with AI
            parsing_result = self.ai_service.extract_herb_info(herb_name, context)
            
            if not parsing_result.success:
                warnings.append(f"AI extraction failed for '{herb_name}': {'; '.join(parsing_result.parsing_errors)}")
                return None, warnings
            
            # Convert to herb object
            herb = self.ai_service._convert_to_parsed_herb(parsing_result.parsed_data, parsing_result)
            if not herb:
                warnings.append(f"Failed to convert parsed data to herb object for '{herb_name}'")
                return None, warnings
            
            # Safety validation
            safety_result = self.validation_service.validate_herb_safety(herb)
            
            # Add safety warnings
            if not safety_result.is_safe:
                for compound_warning in safety_result.dangerous_compounds:
                    warnings.append(f"DANGER - {compound_warning}")
            
            for concern in safety_result.safety_concerns:
                warnings.append(f"Safety concern: {concern}")
            
            if safety_result.requires_expert_review:
                warnings.append(f"Herb '{herb_name}' requires expert review before use")
            
            self.logger.info(f"Successfully extracted and validated herb '{herb_name}'")
            return herb, warnings
            
        except Exception as e:
            warning = f"Unexpected error extracting herb '{herb_name}': {str(e)}"
            warnings.append(warning)
            self.logger.error(warning, exc_info=True)
            return None, warnings
    
    def _fetch_page_content(self, url: str, result: ScrapingResult) -> Tuple[Optional[str], bool]:
        """
        Fetch webpage content with robots.txt checking and content extraction.
        
        Implements the same content fetching logic as the existing scraper_ui.py
        while providing enhanced error reporting and debugging information.
        """
        try:
            # Check robots.txt first
            if not self._can_fetch(url):
                result.add_error("Scraping disallowed by robots.txt")
                return None, False
            
            # Fetch page content
            headers = {'User-Agent': self.USER_AGENT}
            response = requests.get(url, headers=headers, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # Parse and extract main content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find main content area (same selectors as scraper_ui.py)
            main_content = None
            selectors = [
                'main', 'article', '[role="main"]', '#main-content', 
                '#content', '.main-content', '.content', '#main', '.main'
            ]
            
            for selector in selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            # Extract text with structure preservation
            if main_content:
                page_text = main_content.get_text(separator=' \n ', strip=True)
                return page_text, True
            else:
                # Fallback to body content
                page_text = (soup.body.get_text(separator=' \n ', strip=True) 
                           if soup.body else soup.get_text(separator=' \n ', strip=True))
                result.add_warning("Could not identify main content area, using full page text")
                return page_text, False
                
        except requests.RequestException as e:
            result.add_error(f"HTTP request failed: {str(e)}")
            self.logger.error(f"Failed to fetch {url}: {e}")
            return None, False
        except Exception as e:
            result.add_error(f"Content extraction failed: {str(e)}")
            self.logger.error(f"Content extraction error for {url}: {e}")
            return None, False
    
    def _can_fetch(self, url: str) -> bool:
        """
        Check if URL can be fetched according to robots.txt.
        
        Uses the same robots.txt checking logic as scraper_ui.py with
        enhanced error handling and logging.
        """
        try:
            base_url = requests.utils.urlparse(url)._replace(
                path="", params="", query="", fragment=""
            ).geturl()
            robots_url = urljoin(base_url, "robots.txt")

            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            time.sleep(self.ROBOTS_DELAY)  # Be respectful
            
            can_fetch = rp.can_fetch(self.USER_AGENT, url)
            self.logger.info(f"Robots.txt check for {url}: {'allowed' if can_fetch else 'disallowed'}")
            return can_fetch
            
        except Exception as e:
            self.logger.warning(f"Could not parse robots.txt for {url}: {e}")
            return False  # Conservative approach - assume not allowed
    
    def _process_unknown_herbs(self, herb_names: List[str], result: ScrapingResult) -> List[ParsedHerb]:
        """
        Process unknown herbs by extracting information and validating safety.
        
        Creates new herb entries for herbs not found in the database,
        with comprehensive safety validation and user warnings.
        """
        new_herbs = []
        
        for herb_name in herb_names:
            self.logger.info(f"Processing unknown herb: {herb_name}")
            
            # Check if herb already exists in database
            existing_herbs = self.db_service.get_herbs_by_names([herb_name])
            if existing_herbs.get(herb_name):
                self.logger.info(f"Herb '{herb_name}' already exists in database")
                continue
            
            # Extract herb information
            herb, warnings = self.extract_and_validate_herb(herb_name)
            
            if herb:
                new_herbs.append(herb)
                # Add any safety warnings to main result
                for warning in warnings:
                    result.add_warning(f"Herb '{herb_name}': {warning}")
            else:
                result.add_warning(f"Could not extract information for herb '{herb_name}'")
                # Add warnings from failed extraction
                for warning in warnings:
                    result.add_warning(warning)
        
        return new_herbs
    
    def _log_operation(self, operation_type: str, source: str, result: ScrapingResult):
        """Log operation details for statistics and debugging."""
        self.operation_history.append({
            "timestamp": result.timestamp,
            "operation_type": operation_type,
            "source": source,
            "success": result.success,
            "errors": len(result.errors),
            "warnings": len(result.warnings),
            "recipe_id": result.recipe_id,
            "new_herbs": len(result.new_herbs_added)
        })
        
        # Keep history to reasonable size
        if len(self.operation_history) > 1000:
            self.operation_history = self.operation_history[-500:]
    
    def get_operation_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about scraping operations."""
        if not self.operation_history:
            return {"total_operations": 0}
        
        total = len(self.operation_history)
        successful = sum(1 for op in self.operation_history if op["success"])
        
        # Component statistics
        ai_stats = self.ai_service.get_parsing_statistics()
        validation_stats = self.validation_service.get_validation_statistics()
        
        return {
            "total_operations": total,
            "successful_operations": successful,
            "success_rate": successful / total if total > 0 else 0,
            "total_recipes_created": sum(1 for op in self.operation_history if op["recipe_id"]),
            "total_herbs_created": sum(op.get("new_herbs", 0) for op in self.operation_history),
            "average_errors_per_operation": sum(op["errors"] for op in self.operation_history) / total,
            "average_warnings_per_operation": sum(op["warnings"] for op in self.operation_history) / total,
            "ai_parsing_stats": ai_stats,
            "validation_stats": validation_stats,
            "operation_types": {
                "full_scrape": sum(1 for op in self.operation_history if op["operation_type"] == "full_scrape"),
                "text_parse": sum(1 for op in self.operation_history if op["operation_type"] == "text_parse")
            }
        }
    
    def get_recent_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent operation details for debugging."""
        return self.operation_history[-limit:] if self.operation_history else []