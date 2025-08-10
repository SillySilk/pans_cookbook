"""
Database service for scraper operations with transaction safety and error handling.

This service leverages the existing database.py infrastructure to ensure full
compatibility with the Streamlit app while providing enhanced transaction
management and comprehensive error reporting for scraper operations.
"""
import sqlite3
import logging
from typing import List, Optional, Set, Dict, Any
from pathlib import Path

# Import existing database infrastructure for compatibility
from database import DB_PATH, Herb, Recipe, create_database
from .models import (
    ParsedRecipe, ParsedHerb, DatabaseResult, HerbMatchResult, ScrapingResult
)
from .data_sanitizer import DataSanitizer


class DatabaseService:
    """
    Database service for scraper operations with transaction safety.
    
    Leverages existing database.py infrastructure to ensure Streamlit compatibility
    while providing enhanced error handling and transaction management for
    scraping operations. All database errors are exposed with full context.
    """
    
    def __init__(self):
        """Initialize database service with existing infrastructure."""
        self.db_path = DB_PATH  # Use same path as main app
        self.connection_pool = {}  # Simple connection pooling
        
        # Ensure database exists using existing function
        if not Path(self.db_path).exists():
            create_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Get database connection with proper error handling.
        
        Uses the same database file as the main Streamlit app to ensure
        complete compatibility and data consistency.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")  # Enforce constraints
            return conn
        except sqlite3.Error as e:
            logging.error(f"Database connection failed: {e}")
            raise
    
    def save_recipe_with_herbs(self, recipe: ParsedRecipe, herbs: List[ParsedHerb]) -> DatabaseResult:
        """
        Save recipe with associated herbs in a transaction-safe manner.
        
        Creates new herb entries for unknown herbs and establishes proper
        relationships. All operations are wrapped in a transaction with
        comprehensive rollback on any failure.
        
        Args:
            recipe: ParsedRecipe object with complete recipe data
            herbs: List of ParsedHerb objects for new herbs to create
            
        Returns:
            DatabaseResult with detailed operation feedback
        """
        result = DatabaseResult(success=False)
        conn = None
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Start transaction
            cursor.execute("BEGIN TRANSACTION")
            
            # Insert recipe first
            recipe_id = self._insert_recipe(cursor, recipe, result)
            if not recipe_id:
                conn.rollback()
                return result
            
            result.new_record_id = recipe_id
            result.affected_rows += 1
            
            # Process herbs and create herb-recipe relationships
            herb_ids = []
            
            # Create new herbs that don't exist
            for herb in herbs:
                herb_id = self._create_herb_if_not_exists(cursor, herb, result)
                if herb_id:
                    herb_ids.append(herb_id)
                else:
                    # If herb creation failed, rollback everything
                    conn.rollback()
                    result.add_error(f"Failed to create herb: {herb.name}")
                    return result
            
            # Map ingredient names to existing herbs
            existing_herb_ids = self._find_herbs_by_ingredients(cursor, recipe.ingredients)
            herb_ids.extend(existing_herb_ids)
            
            # Create recipe-herb relationships
            for herb_id in herb_ids:
                try:
                    cursor.execute('''
                        INSERT INTO recipe_herbs (recipe_id, herb_id)
                        VALUES (?, ?)
                    ''', (recipe_id, herb_id))
                    result.affected_rows += 1
                except sqlite3.IntegrityError as e:
                    # Skip duplicate relationships but log them
                    logging.warning(f"Duplicate recipe-herb relationship: recipe_id={recipe_id}, herb_id={herb_id}")
            
            # Commit transaction
            conn.commit()
            result.success = True
            
            logging.info(f"Successfully saved recipe '{recipe.name}' with {len(herb_ids)} herbs")
            
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            result.add_error(f"Database operation failed: {str(e)}", str(e))
            logging.error(f"Recipe save failed: {e}")
            
        except Exception as e:
            if conn:
                conn.rollback()
            result.add_error(f"Unexpected error during recipe save: {str(e)}")
            logging.error(f"Unexpected error: {e}")
            
        finally:
            if conn:
                conn.close()
        
        return result
    
    def find_similar_herbs(self, herb_name: str, scientific_name: str = "") -> HerbMatchResult:
        """
        Find similar herbs to avoid duplicates and resolve conflicts.
        
        Uses fuzzy matching on names and exact matching on scientific names
        to identify potential duplicates. Provides detailed matching information
        for user decision-making.
        
        Args:
            herb_name: Common name of herb to match
            scientific_name: Scientific name for exact matching
            
        Returns:
            HerbMatchResult with matching information and recommendations
        """
        result = HerbMatchResult()
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Exact name match
            cursor.execute('SELECT id, name, scientific_name FROM herbs WHERE LOWER(name) = LOWER(?)', (herb_name,))
            exact_match = cursor.fetchone()
            if exact_match:
                result.exact_match = exact_match[0]
                result.recommended_action = "use_existing"
                result.confidence_score = 1.0
                return result
            
            # Scientific name conflicts
            if scientific_name:
                cursor.execute('''
                    SELECT id, name, scientific_name FROM herbs 
                    WHERE LOWER(scientific_name) = LOWER(?) AND scientific_name != ""
                ''', (scientific_name,))
                
                scientific_matches = cursor.fetchall()
                for match in scientific_matches:
                    result.add_scientific_name_conflict(match[0], match[1], match[2])
            
            # Fuzzy name matching
            cursor.execute('SELECT id, name, scientific_name FROM herbs')
            all_herbs = cursor.fetchall()
            
            herb_name_lower = herb_name.lower()
            for herb_id, name, sci_name in all_herbs:
                similarity = self._calculate_name_similarity(herb_name_lower, name.lower())
                if similarity > 0.7:  # 70% similarity threshold
                    reason = f"Name similarity: {similarity:.2f}"
                    result.add_similar_match(herb_id, name, similarity, reason)
            
            # Set recommendations based on matches
            if result.has_conflicts():
                result.recommended_action = "user_review"
            elif result.similar_matches:
                result.recommended_action = "user_review" 
                result.confidence_score = max(match["similarity"] for match in result.similar_matches)
            else:
                result.recommended_action = "create_new"
                result.confidence_score = 0.0
            
        except sqlite3.Error as e:
            logging.error(f"Herb matching failed: {e}")
            result.recommended_action = "create_new"  # Safe fallback
            
        finally:
            if conn:
                conn.close()
        
        return result
    
    def create_herb_if_not_exists(self, herb_data: ParsedHerb) -> Optional[int]:
        """
        Create a new herb entry if it doesn't already exist.
        
        Performs duplicate checking before creation and returns the herb ID
        whether it's newly created or already exists.
        
        Args:
            herb_data: ParsedHerb object with complete herb information
            
        Returns:
            Herb ID if successful, None if failed
        """
        try:
            # Check if herb already exists
            match_result = self.find_similar_herbs(herb_data.name, herb_data.scientific_name)
            
            if match_result.exact_match:
                logging.info(f"Herb '{herb_data.name}' already exists with ID {match_result.exact_match}")
                return match_result.exact_match
            
            if match_result.has_conflicts():
                logging.warning(f"Herb '{herb_data.name}' has conflicts - manual resolution required")
                return None
            
            # Create new herb
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO herbs (name, description, symbol, scientific_name, 
                                     traditional_uses, craft_uses, current_evidence_summary,
                                     contraindications, interactions, toxicity_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    herb_data.name, herb_data.description, herb_data.symbol,
                    herb_data.scientific_name, herb_data.traditional_uses,
                    herb_data.craft_uses, herb_data.current_evidence_summary,
                    herb_data.contraindications, herb_data.interactions,
                    herb_data.toxicity_notes
                ))
                
                herb_id = cursor.lastrowid
                conn.commit()
                
                logging.info(f"Created new herb '{herb_data.name}' with ID {herb_id}")
                return herb_id
                
            except sqlite3.IntegrityError as e:
                conn.rollback()
                logging.error(f"Herb creation constraint violation: {e}")
                return None
                
        except sqlite3.Error as e:
            logging.error(f"Herb creation failed: {e}")
            return None
            
        finally:
            if conn:
                conn.close()
    
    def get_herbs_by_names(self, herb_names: List[str]) -> Dict[str, Optional[Herb]]:
        """
        Get existing herbs by their names.
        
        Returns a dictionary mapping herb names to Herb objects, with None
        for herbs that don't exist in the database.
        
        Args:
            herb_names: List of herb names to look up
            
        Returns:
            Dictionary mapping herb names to Herb objects or None
        """
        results = {name: None for name in herb_names}
        
        if not herb_names:
            return results
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Use parameterized query for multiple names
            placeholders = ','.join(['?' for _ in herb_names])
            cursor.execute(f'''
                SELECT id, name, description, symbol, scientific_name, traditional_uses,
                       craft_uses, current_evidence_summary, contraindications, 
                       interactions, toxicity_notes
                FROM herbs 
                WHERE LOWER(name) IN ({placeholders})
            ''', [name.lower() for name in herb_names])
            
            for row in cursor.fetchall():
                herb = Herb(
                    id=row[0], name=row[1], description=row[2], symbol=row[3],
                    scientific_name=row[4], traditional_uses=row[5], craft_uses=row[6],
                    current_evidence_summary=row[7], contraindications=row[8],
                    interactions=row[9], toxicity_notes=row[10]
                )
                
                # Find the original name that matched (case-insensitive)
                for original_name in herb_names:
                    if original_name.lower() == herb.name.lower():
                        results[original_name] = herb
                        break
                        
        except sqlite3.Error as e:
            logging.error(f"Herb lookup failed: {e}")
            
        finally:
            if conn:
                conn.close()
        
        return results
    
    def _insert_recipe(self, cursor: sqlite3.Cursor, recipe: ParsedRecipe, result: DatabaseResult) -> Optional[int]:
        """Insert recipe into database with sanitization and return the new recipe ID."""
        try:
            # Sanitize recipe data before insertion
            recipe_dict = {
                'name': recipe.name,
                'description': recipe.description,
                'instructions': recipe.instructions,
                'benefits': recipe.benefits,
                'category': recipe.category,
                'route': recipe.route,
                'safety_summary': recipe.safety_summary,
                'contraindications': recipe.contraindications,
                'interactions': recipe.interactions,
                'pediatric_note': recipe.pediatric_note,
                'pregnancy_note': recipe.pregnancy_note,
                'sanitation_level': recipe.sanitation_level,
                'storage_instructions': recipe.storage_instructions,
                'batch_size_unit': recipe.batch_size_unit
            }
            sanitized_data = DataSanitizer.sanitize_recipe_data(recipe_dict)
            
            # Validate sanitized data
            is_valid, errors = DataSanitizer.validate_sanitized_data(sanitized_data, ['name'])
            if not is_valid:
                result.add_error("Recipe validation failed", str(errors))
                return None
            cursor.execute('''
                INSERT INTO recipes (name, description, instructions, benefits, category, route,
                                   safety_summary, contraindications, interactions, pediatric_note,
                                   pregnancy_note, sanitation_level, storage_instructions,
                                   shelf_life_days, batch_size_value, batch_size_unit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sanitized_data.get('name'), sanitized_data.get('description'), 
                sanitized_data.get('instructions'), sanitized_data.get('benefits'),
                sanitized_data.get('category'), sanitized_data.get('route'), 
                sanitized_data.get('safety_summary'), sanitized_data.get('contraindications'),
                sanitized_data.get('interactions'), sanitized_data.get('pediatric_note'), 
                sanitized_data.get('pregnancy_note'), sanitized_data.get('sanitation_level'), 
                sanitized_data.get('storage_instructions'), recipe.shelf_life_days,
                recipe.batch_size_value, sanitized_data.get('batch_size_unit')
            ))
            
            return cursor.lastrowid
            
        except sqlite3.IntegrityError as e:
            result.add_constraint_violation(f"Recipe constraint violation: {e}")
            logging.error(f"Recipe insert constraint violation: {e}")
            return None
            
        except sqlite3.Error as e:
            result.add_error(f"Recipe insert failed: {e}", str(e))
            logging.error(f"Recipe insert error: {e}")
            return None
    
    def _create_herb_if_not_exists(self, cursor: sqlite3.Cursor, herb: ParsedHerb, result: DatabaseResult) -> Optional[int]:
        """Create herb if it doesn't exist and return herb ID."""
        # Check if herb already exists
        cursor.execute('SELECT id FROM herbs WHERE LOWER(name) = LOWER(?)', (herb.name,))
        existing = cursor.fetchone()
        if existing:
            return existing[0]
        
        try:
            cursor.execute('''
                INSERT INTO herbs (name, description, symbol, scientific_name, 
                                 traditional_uses, craft_uses, current_evidence_summary,
                                 contraindications, interactions, toxicity_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                herb.name, herb.description, herb.symbol, herb.scientific_name,
                herb.traditional_uses, herb.craft_uses, herb.current_evidence_summary,
                herb.contraindications, herb.interactions, herb.toxicity_notes
            ))
            
            herb_id = cursor.lastrowid
            result.affected_rows += 1
            logging.info(f"Created new herb '{herb.name}' with ID {herb_id}")
            return herb_id
            
        except sqlite3.IntegrityError as e:
            result.add_constraint_violation(f"Herb constraint violation: {e}")
            logging.error(f"Herb creation constraint violation: {e}")
            return None
            
        except sqlite3.Error as e:
            result.add_error(f"Herb creation failed: {e}", str(e))
            logging.error(f"Herb creation error: {e}")
            return None
    
    def _find_herbs_by_ingredients(self, cursor: sqlite3.Cursor, ingredients: List[str]) -> List[int]:
        """Find existing herb IDs that match ingredient names."""
        herb_ids = []
        
        if not ingredients:
            return herb_ids
        
        try:
            for ingredient in ingredients:
                # Try exact match first
                cursor.execute('SELECT id FROM herbs WHERE LOWER(name) = LOWER(?)', (ingredient.strip(),))
                match = cursor.fetchone()
                if match:
                    herb_ids.append(match[0])
                    continue
                
                # Try partial matching for complex ingredient descriptions
                cursor.execute('SELECT id, name FROM herbs')
                all_herbs = cursor.fetchall()
                
                ingredient_lower = ingredient.lower().strip()
                for herb_id, herb_name in all_herbs:
                    if herb_name.lower() in ingredient_lower or ingredient_lower in herb_name.lower():
                        herb_ids.append(herb_id)
                        break
                        
        except sqlite3.Error as e:
            logging.error(f"Ingredient-herb matching failed: {e}")
        
        return list(set(herb_ids))  # Remove duplicates
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two herb names using simple algorithm."""
        if name1 == name2:
            return 1.0
        
        # Simple similarity: longer common substring ratio
        common = 0
        min_len = min(len(name1), len(name2))
        
        for i in range(min_len):
            if name1[i] == name2[i]:
                common += 1
            else:
                break
        
        # Also check if one name is contained in the other
        if name1 in name2 or name2 in name1:
            return 0.8
        
        return common / max(len(name1), len(name2)) if max(len(name1), len(name2)) > 0 else 0.0