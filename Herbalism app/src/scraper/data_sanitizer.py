"""
Data sanitization utilities for cleaning text fields and preventing JavaScript rendering issues.
"""

import re
import unicodedata
from typing import Optional, Union


class DataSanitizer:
    """Handles sanitization of text data to prevent rendering issues and ensure data consistency."""
    
    # Characters that can cause JavaScript/HTML rendering issues
    PROBLEMATIC_CHARS = {
        '(': ' - ',      # Replace parentheses with dashes
        ')': '',
        '[': ' - ',      # Replace brackets with dashes  
        ']': '',
        '{': ' - ',      # Replace braces with dashes
        '}': '',
        '<': '',         # Remove angle brackets (HTML tags)
        '>': '',
        '&': 'and',      # Replace ampersand
        '"': "'",        # Replace double quotes with single
        '`': "'",        # Replace backticks with single quotes
        '\\': ' ',       # Replace backslashes with spaces
        '\r\n': '\n',    # Normalize line endings
        '\r': '\n',
    }
    
    # Unicode categories to remove (control characters, etc.)
    REMOVE_UNICODE_CATEGORIES = {'Cc', 'Cf', 'Co', 'Cn'}
    
    @classmethod
    def sanitize_text(cls, text: Optional[str]) -> Optional[str]:
        """
        Sanitize text by removing problematic characters and normalizing content.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text or None if input was None/empty
        """
        if not text or not isinstance(text, str):
            return text
            
        # Step 1: Replace problematic characters
        sanitized = text
        for char, replacement in cls.PROBLEMATIC_CHARS.items():
            sanitized = sanitized.replace(char, replacement)
        
        # Step 2: Remove Unicode control characters
        sanitized = ''.join(
            char for char in sanitized 
            if unicodedata.category(char) not in cls.REMOVE_UNICODE_CATEGORIES
        )
        
        # Step 3: Normalize Unicode to decomposed form and remove combining characters
        sanitized = unicodedata.normalize('NFD', sanitized)
        sanitized = ''.join(
            char for char in sanitized 
            if not unicodedata.combining(char)
        )
        
        # Step 4: Remove extra whitespace and clean up spacing
        sanitized = re.sub(r'[ \t]+', ' ', sanitized)  # Collapse spaces and tabs, preserve newlines
        sanitized = re.sub(r'\n\s*\n', '\n\n', sanitized)  # Multiple newlines to double
        sanitized = sanitized.strip()
        
        # Step 5: Remove any remaining problematic patterns
        sanitized = re.sub(r'[^\w\s\-.,!?;:\'/\n]', '', sanitized)
        
        return sanitized if sanitized else None
    
    @classmethod
    def sanitize_recipe_data(cls, recipe_data: dict) -> dict:
        """
        Sanitize all text fields in a recipe data dictionary.
        
        Args:
            recipe_data: Dictionary containing recipe fields
            
        Returns:
            Dictionary with sanitized text fields
        """
        text_fields = [
            'name', 'description', 'instructions', 'benefits',
            'safety_summary', 'contraindications', 'interactions',
            'storage_instructions', 'route', 'category',
            'sanitation_level', 'batch_size_unit',
            'pediatric_note', 'pregnancy_note'
        ]
        
        sanitized_data = recipe_data.copy()
        
        for field in text_fields:
            if field in sanitized_data:
                sanitized_data[field] = cls.sanitize_text(sanitized_data[field])
        
        return sanitized_data
    
    @classmethod
    def sanitize_herb_data(cls, herb_data: dict) -> dict:
        """
        Sanitize all text fields in an herb data dictionary.
        
        Args:
            herb_data: Dictionary containing herb fields
            
        Returns:
            Dictionary with sanitized text fields
        """
        text_fields = [
            'name', 'scientific_name', 'description',
            'traditional_uses', 'craft_uses', 'current_evidence_summary',
            'contraindications', 'interactions', 'toxicity_notes',
            'symbol'  # Special handling needed for symbols
        ]
        
        sanitized_data = herb_data.copy()
        
        for field in text_fields:
            if field in sanitized_data:
                if field == 'symbol':
                    # Special handling for herb symbols - keep emojis but sanitize others
                    sanitized_data[field] = cls.sanitize_herb_symbol(sanitized_data[field])
                else:
                    sanitized_data[field] = cls.sanitize_text(sanitized_data[field])
        
        return sanitized_data
    
    @classmethod
    def sanitize_herb_symbol(cls, symbol: Optional[str]) -> Optional[str]:
        """
        Sanitize herb symbol, preserving emojis but removing problematic characters.
        
        Args:
            symbol: Symbol to sanitize
            
        Returns:
            Sanitized symbol or default plant emoji
        """
        if not symbol or not isinstance(symbol, str):
            return "🌿"  # Default plant emoji
        
        # Remove whitespace and control characters
        sanitized = symbol.strip()
        sanitized = ''.join(
            char for char in sanitized 
            if unicodedata.category(char) not in cls.REMOVE_UNICODE_CATEGORIES
        )
        
        # If empty after sanitization, use default
        if not sanitized:
            return "🌿"
            
        # Take only first character if multiple
        return sanitized[0] if sanitized else "🌿"
    
    @classmethod
    def validate_sanitized_data(cls, data: dict, required_fields: list = None) -> tuple[bool, list]:
        """
        Validate that sanitized data meets requirements.
        
        Args:
            data: Data to validate
            required_fields: List of required field names
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if required_fields:
            for field in required_fields:
                if field not in data or not data[field]:
                    errors.append(f"Required field '{field}' is missing or empty")
        
        # Check for remaining problematic characters
        for key, value in data.items():
            if isinstance(value, str):
                if any(char in value for char in ['<', '>', '`', '{', '}']):
                    errors.append(f"Field '{key}' contains problematic characters")
                
                # Check for excessive length
                if len(value) > 10000:  # Reasonable limit
                    errors.append(f"Field '{key}' exceeds maximum length")
        
        return len(errors) == 0, errors

def clean_existing_database():
    """
    Clean existing database entries by applying sanitization to all text fields.
    This function should be run as a one-time cleanup operation.
    """
    import sqlite3
    from pathlib import Path
    
    db_path = Path("herbalism.db")
    if not db_path.exists():
        print("Database not found")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Clean recipes table
        cursor.execute("SELECT * FROM recipes")
        recipes = cursor.fetchall()
        
        # Get column names for recipes
        recipe_columns = [description[0] for description in cursor.description]
        
        print(f"Cleaning {len(recipes)} recipes...")
        for recipe in recipes:
            recipe_dict = dict(zip(recipe_columns, recipe))
            sanitized = DataSanitizer.sanitize_recipe_data(recipe_dict)
            
            # Update the record
            update_fields = []
            update_values = []
            for field in ['name', 'description', 'instructions', 'benefits', 
                         'safety_summary', 'contraindications', 'interactions',
                         'storage_instructions', 'route', 'category', 'sanitation_level',
                         'batch_size_unit', 'pediatric_note', 'pregnancy_note']:
                if field in sanitized and sanitized[field] != recipe_dict.get(field):
                    update_fields.append(f"{field} = ?")
                    update_values.append(sanitized[field])
            
            if update_fields:
                update_values.append(recipe_dict['id'])
                cursor.execute(
                    f"UPDATE recipes SET {', '.join(update_fields)} WHERE id = ?",
                    update_values
                )
                print(f"Updated recipe ID {recipe_dict['id']}: {recipe_dict['name']}")
        
        # Clean herbs table
        cursor.execute("SELECT * FROM herbs")
        herbs = cursor.fetchall() 
        
        # Get column names for herbs
        herb_columns = [description[0] for description in cursor.description]
        
        print(f"Cleaning {len(herbs)} herbs...")
        for herb in herbs:
            herb_dict = dict(zip(herb_columns, herb))
            sanitized = DataSanitizer.sanitize_herb_data(herb_dict)
            
            # Update the record
            update_fields = []
            update_values = []
            for field in ['name', 'scientific_name', 'description', 'traditional_uses',
                         'craft_uses', 'current_evidence_summary', 'contraindications',
                         'interactions', 'toxicity_notes', 'symbol']:
                if field in sanitized and sanitized[field] != herb_dict.get(field):
                    update_fields.append(f"{field} = ?")
                    update_values.append(sanitized[field])
            
            if update_fields:
                update_values.append(herb_dict['id'])
                cursor.execute(
                    f"UPDATE herbs SET {', '.join(update_fields)} WHERE id = ?",
                    update_values
                )
                print(f"Updated herb ID {herb_dict['id']}: {herb_dict['name']}")
        
        conn.commit()
        print("Database cleaning completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during database cleaning: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    # Run database cleaning when script is executed directly
    clean_existing_database()