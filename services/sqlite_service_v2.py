"""
Enhanced SQLite database service with proper threading and WAL mode support.
Addresses previous SQLite threading issues with better connection management.
"""

import sqlite3
import threading
import json
import logging
import os
from typing import List, Optional, Dict, Set, Any
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime

from models import (
    Recipe, Ingredient, RecipeIngredient, User, UserPreferences, 
    Collection, UserSession, NutritionData
)

logger = logging.getLogger(__name__)


class EnhancedSQLiteService:
    """
    Enhanced SQLite database service with proper threading support.
    Uses WAL mode and connection pooling to handle concurrent access properly.
    """
    
    _lock = threading.Lock()
    _connections = threading.local()
    
    def __init__(self, db_path: str = None):
        """Initialize SQLite service with threading support"""
        self.db_path = db_path or self._get_database_path()
        self._ensure_database_directory()
        self._initialize_connection()
        self._ensure_schema_exists()
    
    def _get_database_path(self) -> str:
        """Get database path from environment or default"""
        db_path = os.getenv('DATABASE_PATH', 'database/pans_cookbook.db')
        return str(Path(db_path).resolve())
    
    def _ensure_database_directory(self):
        """Ensure database directory exists"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def _initialize_connection(self):
        """Initialize connection with proper SQLite settings"""
        try:
            # Test connection and setup
            with self.get_connection() as conn:
                # Enable WAL mode for better concurrent access
                conn.execute("PRAGMA journal_mode=WAL")
                
                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys=ON")
                
                # Set reasonable timeout
                conn.execute("PRAGMA busy_timeout=10000")
                
                # Performance optimizations
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                conn.execute("PRAGMA temp_store=MEMORY")
                
            logger.info(f"SQLite service initialized successfully: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite service: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get thread-safe database connection"""
        # Use thread-local storage for connections
        if not hasattr(self._connections, 'conn'):
            self._connections.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,  # Allow cross-thread usage
                timeout=30.0,  # 30 second timeout
                isolation_level=None  # Autocommit mode
            )
            self._connections.conn.row_factory = sqlite3.Row
        
        try:
            yield self._connections.conn
        except Exception as e:
            # Rollback on error
            try:
                self._connections.conn.rollback()
            except:
                pass
            logger.error(f"Database operation failed: {e}")
            raise
    
    def _ensure_schema_exists(self):
        """Create database schema if it doesn't exist and migrate existing tables"""
        schema_sql = """
        -- Users table
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            username TEXT UNIQUE,
            first_name TEXT DEFAULT '',
            last_name TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            is_verified INTEGER DEFAULT 0,
            api_keys TEXT DEFAULT '{}',
            preferences TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            login_count INTEGER DEFAULT 0
        );

        -- Ingredients table
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT DEFAULT '',
            common_substitutes TEXT DEFAULT '',
            storage_tips TEXT DEFAULT '',
            nutritional_data TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Recipes table (simplified for single-household use)
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            instructions TEXT NOT NULL,
            prep_time_minutes INTEGER DEFAULT 0,
            cook_time_minutes INTEGER DEFAULT 0,
            servings INTEGER DEFAULT 1,
            nutritional_info TEXT DEFAULT '{}',
            source_url TEXT DEFAULT '',
            image_path TEXT DEFAULT ''
        );

        -- Recipe ingredients junction table
        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE,
            ingredient_id INTEGER REFERENCES ingredients(id) ON DELETE CASCADE,
            quantity REAL DEFAULT 1.0,
            unit TEXT DEFAULT '',
            preparation_note TEXT DEFAULT '',
            ingredient_order INTEGER DEFAULT 0,
            is_optional INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(recipe_id, ingredient_id)
        );

        -- Collections table
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            is_favorite INTEGER DEFAULT 0,
            is_public INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Collection recipes junction table
        CREATE TABLE IF NOT EXISTS collection_recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_id INTEGER REFERENCES collections(id) ON DELETE CASCADE,
            recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(collection_id, recipe_id)
        );

        -- User pantry table
        CREATE TABLE IF NOT EXISTS user_pantry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            ingredient_id INTEGER REFERENCES ingredients(id) ON DELETE CASCADE,
            quantity_available REAL DEFAULT 0,
            unit TEXT DEFAULT '',
            is_available INTEGER DEFAULT 1,
            expiration_date DATE,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, ingredient_id)
        );

        -- User sessions table
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            session_token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_id ON recipe_ingredients (recipe_id);
        CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_ingredient_id ON recipe_ingredients (ingredient_id);
        CREATE INDEX IF NOT EXISTS idx_collections_user_id ON collections (user_id);
        CREATE INDEX IF NOT EXISTS idx_user_pantry_user_id ON user_pantry (user_id);
        CREATE INDEX IF NOT EXISTS idx_user_pantry_available ON user_pantry (is_available);

        -- Default admin user
        INSERT OR IGNORE INTO users (email, password_hash, username, first_name, is_verified) 
        VALUES ('admin@panscookbook.local', 'placeholder_hash', 'admin', 'Administrator', 1);

        -- Default user collection
        INSERT OR IGNORE INTO collections (name, description, user_id, is_favorite)
        SELECT 'My Favorites', 'Default favorites collection', u.id, 1
        FROM users u WHERE u.username = 'admin' AND NOT EXISTS (
            SELECT 1 FROM collections WHERE name = 'My Favorites' AND user_id = u.id
        );
        """
        
        try:
            with self.get_connection() as conn:
                conn.executescript(schema_sql)
                conn.commit()
                logger.info("SQLite schema initialized successfully")
                
                # Migrate existing recipes table if needed
                self._migrate_recipes_table(conn)
                
        except Exception as e:
            logger.error(f"Failed to initialize SQLite schema: {e}")
            raise
    
    def _migrate_recipes_table(self, conn):
        """Migrate existing recipes table to remove unused columns and add image_path"""
        try:
            # Check current table structure
            cursor = conn.execute("PRAGMA table_info(recipes)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Define columns that should be removed
            columns_to_remove = {'difficulty_level', 'meal_category', 'dietary_tags', 
                               'is_public', 'rating', 'rating_count', 'confidence_score',
                               'created_by', 'created_at', 'updated_at', 'cuisine_type'}
            
            existing_old_columns = set(columns) & columns_to_remove
            missing_image_path = 'image_path' not in columns
            
            if existing_old_columns or missing_image_path:
                logger.info(f"Migrating recipes table - removing columns: {existing_old_columns}")
                
                # SQLite doesn't support DROP COLUMN, so we need to recreate the table
                # 1. Create new table with correct schema including image_path
                conn.execute("""
                    CREATE TABLE recipes_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        instructions TEXT NOT NULL,
                        prep_time_minutes INTEGER DEFAULT 0,
                        cook_time_minutes INTEGER DEFAULT 0,
                        servings INTEGER DEFAULT 1,
                        nutritional_info TEXT DEFAULT '{}',
                        source_url TEXT DEFAULT '',
                        image_path TEXT DEFAULT ''
                    )
                """)
                
                # 2. Copy data from old table to new table
                # Check if image_path exists in current table
                if 'image_path' in columns:
                    # Old table has image_path, copy it
                    conn.execute("""
                        INSERT INTO recipes_new 
                        (id, name, description, instructions, prep_time_minutes, cook_time_minutes,
                         servings, nutritional_info, source_url, image_path)
                        SELECT id, name, description, instructions, prep_time_minutes, cook_time_minutes,
                               servings, 
                               COALESCE(nutritional_info, '{}'),
                               COALESCE(source_url, ''),
                               COALESCE(image_path, '')
                        FROM recipes
                    """)
                else:
                    # Old table doesn't have image_path, set default empty
                    conn.execute("""
                        INSERT INTO recipes_new 
                        (id, name, description, instructions, prep_time_minutes, cook_time_minutes,
                         servings, nutritional_info, source_url, image_path)
                        SELECT id, name, description, instructions, prep_time_minutes, cook_time_minutes,
                               servings, 
                               COALESCE(nutritional_info, '{}'),
                               COALESCE(source_url, ''),
                               ''
                        FROM recipes
                    """)
                
                # 3. Drop old table and rename new table
                conn.execute("DROP TABLE recipes")
                conn.execute("ALTER TABLE recipes_new RENAME TO recipes")
                
                # 4. Recreate index
                conn.execute("CREATE INDEX IF NOT EXISTS idx_recipes_cuisine ON recipes (cuisine_type)")
                
                conn.commit()
                logger.info("Successfully migrated recipes table to new schema")
            else:
                logger.info("Recipes table already has correct schema, no migration needed")
                
        except Exception as e:
            logger.error(f"Failed to migrate recipes table: {e}")
            # Don't raise - let the app continue with the existing schema
            pass
    
    # Ingredient Methods
    def get_all_ingredients(self) -> List[Ingredient]:
        """Get all ingredients from database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM ingredients ORDER BY name")
                rows = cursor.fetchall()
                return [self._row_to_ingredient(row) for row in rows]
        except Exception as e:
            logger.error(f"Error loading ingredients: {e}")
            return []
    
    def create_ingredient(self, name: str, category: str = "", **kwargs) -> Optional[Ingredient]:
        """Create a new ingredient"""
        try:
            with self.get_connection() as conn:
                # Check if ingredient already exists
                cursor = conn.execute("SELECT id FROM ingredients WHERE name = ?", (name,))
                existing = cursor.fetchone()
                if existing:
                    return self.get_ingredient_by_id(existing['id'])
                
                cursor = conn.execute("""
                    INSERT INTO ingredients (name, category, common_substitutes, storage_tips, nutritional_data)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    name,
                    category,
                    ','.join(kwargs.get('common_substitutes', [])),
                    kwargs.get('storage_tips', ''),
                    json.dumps(kwargs.get('nutritional_data', {}))
                ))
                
                ingredient_id = cursor.lastrowid
                conn.commit()
                
                return self.get_ingredient_by_id(ingredient_id)
                
        except Exception as e:
            logger.error(f"Failed to create ingredient: {e}")
            return None
    
    def get_ingredient_by_id(self, ingredient_id: int) -> Optional[Ingredient]:
        """Get ingredient by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM ingredients WHERE id = ?", (ingredient_id,))
                row = cursor.fetchone()
                return self._row_to_ingredient(row) if row else None
        except Exception as e:
            logger.error(f"Error loading ingredient {ingredient_id}: {e}")
            return None
    
    def search_ingredients(self, query: str) -> List[Ingredient]:
        """Search ingredients by name"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM ingredients WHERE name LIKE ? ORDER BY name",
                    (f"%{query}%",)
                )
                rows = cursor.fetchall()
                return [self._row_to_ingredient(row) for row in rows]
        except Exception as e:
            logger.error(f"Error searching ingredients: {e}")
            return []
    
    # Recipe Methods
    def get_all_recipes(self, user_id: int = None, limit: int = None) -> List[Recipe]:
        """Get all recipes (user_id ignored for single-household use)"""
        try:
            with self.get_connection() as conn:
                sql = "SELECT * FROM recipes ORDER BY id DESC"
                params = []
                
                if limit:
                    sql += " LIMIT ?"
                    params.append(limit)
                
                cursor = conn.execute(sql, params)
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
                     servings: int = 1, **kwargs) -> Optional[Recipe]:
        """Create a new recipe"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO recipes (
                        name, description, instructions, prep_time_minutes, cook_time_minutes,
                        servings, nutritional_info, source_url, image_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    title, description, instructions, prep_time_minutes, cook_time_minutes,
                    servings, json.dumps(kwargs.get('nutritional_info', {})), 
                    kwargs.get('source_url', ''), kwargs.get('image_path', '')
                ))
                
                recipe_id = cursor.lastrowid
                conn.commit()
                
                return self.get_recipe_by_id(recipe_id)
                
        except Exception as e:
            logger.error(f"Failed to create recipe: {e}")
            return None
    
    def get_recipe_by_id(self, recipe_id: int, include_ingredients: bool = True) -> Optional[Recipe]:
        """Get recipe by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
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
    
    def delete_recipe(self, recipe_id: int) -> bool:
        """Delete a recipe and its associated data"""
        try:
            with self.get_connection() as conn:
                # Delete recipe ingredients first (foreign key constraint)
                conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
                
                # Delete from collections if any
                conn.execute("DELETE FROM collection_recipes WHERE recipe_id = ?", (recipe_id,))
                
                # Delete the recipe itself
                cursor = conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Successfully deleted recipe {recipe_id}")
                    return True
                else:
                    logger.warning(f"Recipe {recipe_id} not found for deletion")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to delete recipe {recipe_id}: {e}")
            return False
    
    def update_recipe_image(self, recipe_id: int, image_path: str) -> bool:
        """Update recipe image path"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "UPDATE recipes SET image_path = ? WHERE id = ?", 
                    (image_path, recipe_id)
                )
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Successfully updated image for recipe {recipe_id}")
                    return True
                else:
                    logger.warning(f"Recipe {recipe_id} not found for image update")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to update recipe image {recipe_id}: {e}")
            return False
    
    # Database Statistics
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                stats = {}
                
                # Count ingredients
                cursor = conn.execute("SELECT COUNT(*) FROM ingredients")
                stats['ingredients'] = cursor.fetchone()[0]
                
                # Count recipes
                cursor = conn.execute("SELECT COUNT(*) FROM recipes")
                stats['recipes'] = cursor.fetchone()[0]
                
                # Count pantry items
                cursor = conn.execute("SELECT COUNT(*) FROM user_pantry WHERE is_available = 1")
                stats['user_pantry'] = cursor.fetchone()[0]
                
                # Count collections
                cursor = conn.execute("SELECT COUNT(*) FROM collections")
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
        
        # Parse common_substitutes from database
        common_substitutes = []
        if row['common_substitutes']:
            common_substitutes = row['common_substitutes'].split(',')
        
        return Ingredient(
            id=row['id'],
            name=row['name'],
            category=row['category'],
            common_substitutes=common_substitutes,
            storage_tips=row['storage_tips'] or '',
            nutritional_data=json.loads(row['nutritional_data']) if row['nutritional_data'] else {}
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
            nutritional_info=json.loads(row['nutritional_info']) if row['nutritional_info'] else {},
            source_url=row['source_url'],
            image_path=row['image_path'] if 'image_path' in row.keys() else ''
        )
    
    def _get_recipe_ingredient_ids(self, recipe_id: int, conn) -> Set[int]:
        """Get set of ingredient IDs for a recipe"""
        cursor = conn.execute("SELECT ingredient_id FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
        return {row['ingredient_id'] for row in cursor.fetchall()}
    
    def _row_to_recipe_ingredient(self, row):
        """Convert database row to RecipeIngredient object (for pantry service compatibility)"""
        if not row:
            return None
        
        from models.recipe_models import RecipeIngredient
        
        # Handle both dict-like and sqlite3.Row objects
        def safe_get(row, key, default=None):
            try:
                if hasattr(row, 'get'):
                    return row.get(key, default)
                else:
                    # For sqlite3.Row objects, access by column name
                    return row[key] if key in row.keys() else default
            except (KeyError, IndexError):
                return default
        
        return RecipeIngredient(
            recipe_id=safe_get(row, 'recipe_id'),
            ingredient_id=safe_get(row, 'ingredient_id'),
            quantity=safe_get(row, 'quantity', 1.0),
            unit=safe_get(row, 'unit', ''),
            preparation_note=safe_get(row, 'preparation_note', ''),
            ingredient_order=safe_get(row, 'ingredient_order', 0),
            is_optional=bool(safe_get(row, 'is_optional', 0))
        )
    
    # Pantry Management Methods (for pantry service compatibility)
    def get_user_pantry(self, user_id: int):
        """Get user's pantry items"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT up.*, i.name as ingredient_name 
                    FROM user_pantry up
                    JOIN ingredients i ON up.ingredient_id = i.id
                    WHERE up.user_id = ? AND up.is_available = 1
                """, (user_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting user pantry: {e}")
            return []
    
    def update_pantry_item(self, user_id: int, ingredient_id: int, is_available: bool, quantity: str = None):
        """Update or insert pantry item"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO user_pantry (user_id, ingredient_id, is_available, quantity_available, unit)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, ingredient_id, int(is_available), 1.0 if is_available else 0.0, quantity or ''))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating pantry item: {e}")
            return False
    
    def add_recipe_ingredient(self, recipe_id: int, ingredient_id: int, quantity: float = 1.0, 
                             unit: str = "", preparation_note: str = "", ingredient_order: int = 0, 
                             is_optional: bool = False) -> bool:
        """Add ingredient to recipe with quantity and preparation details"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT OR REPLACE INTO recipe_ingredients 
                    (recipe_id, ingredient_id, quantity, unit, preparation_note, ingredient_order, is_optional)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (recipe_id, ingredient_id, quantity, unit, preparation_note, ingredient_order, int(is_optional)))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Successfully added ingredient {ingredient_id} to recipe {recipe_id}")
                    return True
                else:
                    logger.warning(f"Failed to add ingredient {ingredient_id} to recipe {recipe_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error adding recipe ingredient: {e}")
            return False


# Factory function for dependency injection
def get_enhanced_sqlite_service(db_path: str = None) -> EnhancedSQLiteService:
    """Get enhanced SQLite service instance"""
    return EnhancedSQLiteService(db_path)