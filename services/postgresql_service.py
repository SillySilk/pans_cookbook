"""
PostgreSQL database service for Pans Cookbook application.

Provides robust, cloud-ready database operations with Supabase integration.
Replaces SQLite for production deployment and consistent local development.
"""

import psycopg2
import psycopg2.extras
import json
import logging
import os
from typing import List, Optional, Dict, Set, Tuple, Any
from contextlib import contextmanager
from datetime import datetime
import streamlit as st

from models import (
    Recipe, Ingredient, RecipeIngredient, User, UserPreferences, 
    Collection, UserSession, NutritionData
)

logger = logging.getLogger(__name__)


class PostgreSQLService:
    """
    PostgreSQL database service with Supabase integration.
    Provides consistent, reliable database operations for all application components.
    """
    
    def __init__(self, database_url: str = None):
        """Initialize PostgreSQL service with connection URL"""
        self.database_url = database_url or self._get_database_url()
        self.connection_ok = False
        try:
            self._test_connection()
            self._ensure_schema_exists()
            self.connection_ok = True
            logger.info("PostgreSQL service initialized successfully")
        except Exception as e:
            logger.error(f"PostgreSQL initialization failed: {e}")
            logger.warning("App will start but database features may not work")
            # Don't re-raise - let app start for debugging
    
    def _get_database_url(self) -> str:
        """Get database URL from environment or Streamlit secrets"""
        # Try Streamlit secrets first (for Streamlit Cloud)
        try:
            if hasattr(st, 'secrets') and 'DATABASE_URL' in st.secrets:
                return st.secrets['DATABASE_URL']
        except:
            pass
        
        # Try environment variable
        url = os.getenv('DATABASE_URL')
        if url:
            return url
        
        # Fallback to local PostgreSQL
        return "postgresql://postgres:password@localhost:5432/pans_cookbook"
    
    def _test_connection(self):
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result[0] == 1:
                    logger.info("PostgreSQL connection successful")
                else:
                    raise Exception("Connection test failed")
        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            raise Exception(f"Cannot connect to PostgreSQL database: {e}")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup"""
        conn = None
        try:
            conn = psycopg2.connect(
                self.database_url,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _ensure_schema_exists(self):
        """Create database schema if it doesn't exist"""
        schema_sql = """
        -- Users table
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            username TEXT UNIQUE,
            first_name TEXT DEFAULT '',
            last_name TEXT DEFAULT '',
            is_active BOOLEAN DEFAULT true,
            is_verified BOOLEAN DEFAULT false,
            api_keys JSONB DEFAULT '{}',
            preferences JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            login_count INTEGER DEFAULT 0
        );

        -- Ingredients table
        CREATE TABLE IF NOT EXISTS ingredients (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            category TEXT DEFAULT '',
            common_substitutes TEXT DEFAULT '',
            storage_tips TEXT DEFAULT '',
            nutritional_data JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Recipes table
        CREATE TABLE IF NOT EXISTS recipes (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            instructions TEXT NOT NULL,
            prep_time_minutes INTEGER DEFAULT 0,
            cook_time_minutes INTEGER DEFAULT 0,
            servings INTEGER DEFAULT 1,
            difficulty_level TEXT DEFAULT 'medium',
            cuisine_type TEXT DEFAULT '',
            meal_category TEXT DEFAULT '',
            dietary_tags TEXT DEFAULT '',
            nutritional_info JSONB DEFAULT '{}',
            created_by INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_url TEXT DEFAULT '',
            confidence_score REAL DEFAULT 1.0
        );

        -- Recipe ingredients junction table
        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            id SERIAL PRIMARY KEY,
            recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE,
            ingredient_id INTEGER REFERENCES ingredients(id) ON DELETE CASCADE,
            quantity REAL DEFAULT 1.0,
            unit TEXT DEFAULT '',
            preparation_note TEXT DEFAULT '',
            ingredient_order INTEGER DEFAULT 0,
            is_optional BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(recipe_id, ingredient_id)
        );

        -- Collections table
        CREATE TABLE IF NOT EXISTS collections (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            is_favorite BOOLEAN DEFAULT false,
            is_public BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Collection recipes junction table
        CREATE TABLE IF NOT EXISTS collection_recipes (
            id SERIAL PRIMARY KEY,
            collection_id INTEGER REFERENCES collections(id) ON DELETE CASCADE,
            recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(collection_id, recipe_id)
        );

        -- User pantry table
        CREATE TABLE IF NOT EXISTS user_pantry (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            ingredient_id INTEGER REFERENCES ingredients(id) ON DELETE CASCADE,
            quantity_available REAL DEFAULT 0,
            unit TEXT DEFAULT '',
            is_available BOOLEAN DEFAULT true,
            expiration_date DATE,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, ingredient_id)
        );

        -- User sessions table
        CREATE TABLE IF NOT EXISTS user_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            session_token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_recipes_created_by ON recipes (created_by);
        CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_id ON recipe_ingredients (recipe_id);
        CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_ingredient_id ON recipe_ingredients (ingredient_id);
        CREATE INDEX IF NOT EXISTS idx_collections_user_id ON collections (user_id);
        CREATE INDEX IF NOT EXISTS idx_user_pantry_user_id ON user_pantry (user_id);
        CREATE INDEX IF NOT EXISTS idx_user_pantry_available ON user_pantry (is_available);

        -- Default admin user
        INSERT INTO users (email, password_hash, username, first_name, is_verified) 
        VALUES ('admin@panscookbook.local', 'placeholder_hash', 'admin', 'Administrator', true)
        ON CONFLICT (email) DO NOTHING;

        -- Default user collection
        INSERT INTO collections (name, description, user_id, is_favorite)
        SELECT 'My Favorites', 'Default favorites collection', u.id, true
        FROM users u WHERE u.username = 'admin'
        ON CONFLICT DO NOTHING;
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(schema_sql)
                conn.commit()
                logger.info("PostgreSQL schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL schema: {e}")
            raise
    
    # Ingredient Methods
    def get_all_ingredients(self) -> List[Ingredient]:
        """Get all ingredients from database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM ingredients ORDER BY name")
                rows = cursor.fetchall()
                return [self._row_to_ingredient(row) for row in rows]
        except Exception as e:
            logger.error(f"Error loading ingredients: {e}")
            return []
    
    def create_ingredient(self, name: str, category: str = "", **kwargs) -> Optional[Ingredient]:
        """Create a new ingredient"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if ingredient already exists
                cursor.execute("SELECT id FROM ingredients WHERE name = %s", (name,))
                existing = cursor.fetchone()
                if existing:
                    return self.get_ingredient_by_id(existing['id'])
                
                cursor.execute("""
                    INSERT INTO ingredients (name, category, common_substitutes, storage_tips, nutritional_data)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id
                """, (
                    name,
                    category,
                    ','.join(kwargs.get('common_substitutes', [])),
                    kwargs.get('storage_tips', ''),
                    json.dumps(kwargs.get('nutritional_data', {}))
                ))
                
                ingredient_id = cursor.fetchone()['id']
                conn.commit()
                
                return self.get_ingredient_by_id(ingredient_id)
                
        except Exception as e:
            logger.error(f"Failed to create ingredient: {e}")
            return None
    
    def get_ingredient_by_id(self, ingredient_id: int) -> Optional[Ingredient]:
        """Get ingredient by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM ingredients WHERE id = %s", (ingredient_id,))
                row = cursor.fetchone()
                return self._row_to_ingredient(row) if row else None
        except Exception as e:
            logger.error(f"Error loading ingredient {ingredient_id}: {e}")
            return None
    
    def search_ingredients(self, query: str) -> List[Ingredient]:
        """Search ingredients by name"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM ingredients WHERE name ILIKE %s ORDER BY name",
                    (f"%{query}%",)
                )
                rows = cursor.fetchall()
                return [self._row_to_ingredient(row) for row in rows]
        except Exception as e:
            logger.error(f"Error searching ingredients: {e}")
            return []
    
    # Recipe Methods
    def get_all_recipes(self, user_id: int = None, limit: int = None) -> List[Recipe]:
        """Get all recipes"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                sql = "SELECT * FROM recipes ORDER BY created_at DESC"
                params = []
                
                if limit:
                    sql += " LIMIT %s"
                    params.append(limit)
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                recipes = []
                for row in rows:
                    recipe = self._row_to_recipe(row)
                    recipe.required_ingredient_ids = self._get_recipe_ingredient_ids(recipe.id, conn)
                    recipes.append(recipe)
                
                return recipes
        except Exception as e:
            logger.error(f"Error loading recipes: {e}")
            return []
    
    def create_recipe(self, title: str, description: str = "", instructions: str = "", 
                     prep_time_minutes: int = 0, cook_time_minutes: int = 0, 
                     servings: int = 1, difficulty_level: str = "medium",
                     cuisine_type: str = "", meal_category: str = "", 
                     dietary_tags: str = "", created_by: int = 0, **kwargs) -> Optional[Recipe]:
        """Create a new recipe"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO recipes (
                        name, description, instructions, prep_time_minutes, cook_time_minutes,
                        servings, difficulty_level, cuisine_type, meal_category, dietary_tags,
                        nutritional_info, created_by, source_url, confidence_score
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    title, description, instructions, prep_time_minutes, cook_time_minutes,
                    servings, difficulty_level, cuisine_type, meal_category, dietary_tags,
                    json.dumps(kwargs.get('nutritional_info', {})), created_by,
                    kwargs.get('source_url', ''), kwargs.get('confidence_score', 1.0)
                ))
                
                recipe_id = cursor.fetchone()['id']
                conn.commit()
                
                return self.get_recipe_by_id(recipe_id)
                
        except Exception as e:
            logger.error(f"Failed to create recipe: {e}")
            return None
    
    def get_recipe_by_id(self, recipe_id: int, include_ingredients: bool = True) -> Optional[Recipe]:
        """Get recipe by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                recipe = self._row_to_recipe(row)
                if include_ingredients:
                    recipe.required_ingredient_ids = self._get_recipe_ingredient_ids(recipe.id, conn)
                
                return recipe
        except Exception as e:
            logger.error(f"Error loading recipe {recipe_id}: {e}")
            return None
    
    # Database Statistics
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Count ingredients
                cursor.execute("SELECT COUNT(*) FROM ingredients")
                stats['ingredients'] = cursor.fetchone()[0]
                
                # Count recipes
                cursor.execute("SELECT COUNT(*) FROM recipes")
                stats['recipes'] = cursor.fetchone()[0]
                
                # Count pantry items
                cursor.execute("SELECT COUNT(*) FROM user_pantry WHERE is_available = true")
                stats['user_pantry'] = cursor.fetchone()[0]
                
                # Count collections
                cursor.execute("SELECT COUNT(*) FROM collections")
                stats['collections'] = cursor.fetchone()[0]
                
                return stats
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    # Helper Methods
    def _row_to_ingredient(self, row) -> Ingredient:
        """Convert database row to Ingredient object"""
        if not row:
            return None
        
        return Ingredient(
            id=row['id'],
            name=row['name'],
            category=row['category'],
            common_names=[row['name']],  # Simple implementation
            nutritional_info=json.loads(row['nutritional_data']) if row['nutritional_data'] else {}
        )
    
    def _row_to_recipe(self, row) -> Recipe:
        """Convert database row to Recipe object"""
        if not row:
            return None
        
        return Recipe(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            instructions=row['instructions'],
            prep_time_minutes=row['prep_time_minutes'],
            cook_time_minutes=row['cook_time_minutes'],
            servings=row['servings'],
            difficulty_level=row['difficulty_level'],
            cuisine_type=row['cuisine_type'],
            meal_category=row['meal_category'],
            dietary_tags=row['dietary_tags'].split(',') if row['dietary_tags'] else [],
            nutritional_info=json.loads(row['nutritional_info']) if row['nutritional_info'] else {},
            created_by=row['created_by'],
            source_url=row['source_url'],
            confidence_score=row['confidence_score']
        )
    
    def _get_recipe_ingredient_ids(self, recipe_id: int, conn) -> Set[int]:
        """Get set of ingredient IDs for a recipe"""
        cursor = conn.cursor()
        cursor.execute("SELECT ingredient_id FROM recipe_ingredients WHERE recipe_id = %s", (recipe_id,))
        return {row['ingredient_id'] for row in cursor.fetchall()}
    
    # Pantry Management Methods (for pantry service compatibility)
    def get_user_pantry(self, user_id: int):
        """Get user's pantry items (basic implementation)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT up.*, i.name as ingredient_name 
                    FROM user_pantry up
                    JOIN ingredients i ON up.ingredient_id = i.id
                    WHERE up.user_id = %s AND up.is_available = true
                """, (user_id,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting user pantry: {e}")
            return []
    
    def update_pantry_item(self, user_id: int, ingredient_id: int, is_available: bool, quantity: str = None):
        """Update or insert pantry item"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_pantry (user_id, ingredient_id, is_available, quantity_available, unit)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, ingredient_id) 
                    DO UPDATE SET 
                        is_available = EXCLUDED.is_available,
                        quantity_available = EXCLUDED.quantity_available,
                        last_updated = CURRENT_TIMESTAMP
                """, (user_id, ingredient_id, is_available, 1.0 if is_available else 0.0, quantity or ''))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating pantry item: {e}")
            return False


# Factory function for dependency injection
def get_postgresql_service(database_url: str = None) -> PostgreSQLService:
    """Get PostgreSQL service instance"""
    return PostgreSQLService(database_url)