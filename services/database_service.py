"""
Database service for Pans Cookbook application.

Handles all database operations including initialization, user management,
and recipe data operations. Adapted from Herbalism app database patterns
with enhancements for multi-user web deployment.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple, Any
from contextlib import contextmanager
from datetime import datetime, timedelta

from models import (
    Recipe, Ingredient, RecipeIngredient, User, UserPreferences, 
    Collection, UserSession, NutritionData
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Centralized database service for all SQLite operations.
    Follows patterns from Herbalism app with multi-user enhancements.
    """
    
    def __init__(self, db_path: str = "pans_cookbook.db"):
        self.db_path = db_path
        # Look for schema file relative to the project root
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        self.schema_path = project_root / "database_schema.sql"
        # Keep persistent connection for in-memory databases
        self._persistent_conn = None
        if db_path == ":memory:":
            self._persistent_conn = sqlite3.connect(db_path)
            self._persistent_conn.row_factory = sqlite3.Row
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Initialize database if it doesn't exist"""
        db_file = Path(self.db_path)
        if not db_file.exists():
            logger.info(f"Creating new database: {self.db_path}")
            self.initialize_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections with proper cleanup"""
        if self._persistent_conn:
            # Use persistent connection for in-memory databases
            try:
                yield self._persistent_conn
            except Exception as e:
                self._persistent_conn.rollback()
                logger.error(f"Database error: {e}")
                raise
        else:
            # Use regular connection for file databases
            conn = None
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row  # Enable dict-like access
                yield conn
            except Exception as e:
                if conn:
                    conn.rollback()
                logger.error(f"Database error: {e}")
                raise
            finally:
                if conn:
                    conn.close()
    
    def initialize_database(self):
        """Initialize database with schema from SQL file"""
        try:
            with self.get_connection() as conn:
                # Load and execute schema
                schema_file = Path(self.schema_path)
                if schema_file.exists():
                    with open(schema_file, 'r', encoding='utf-8') as f:
                        schema_sql = f.read()
                    
                    # Execute schema in chunks (split by ; and filter empty)
                    statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                    
                    for statement in statements:
                        conn.execute(statement)
                    
                    conn.commit()
                    logger.info("Database initialized successfully")
                else:
                    logger.error(f"Schema file not found: {schema_file}")
                    raise FileNotFoundError(f"Database schema file not found: {schema_file}")
                    
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics (similar to Herbalism app)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Count records in each table
            tables = ['users', 'recipes', 'ingredients', 'collections', 'recipe_ingredients']
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            
            # Database file size
            if self.db_path != ":memory:":
                db_size_bytes = Path(self.db_path).stat().st_size
                stats['db_size_mb'] = round(db_size_bytes / (1024 * 1024), 2)
            else:
                stats['db_size_mb'] = 0.0  # In-memory database
            
            return stats

    # User Management Methods
    
    def create_user(self, email: str, password_hash: str, username: str = "", 
                   first_name: str = "", last_name: str = "") -> Optional[User]:
        """Create a new user account"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if email already exists
                cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                if cursor.fetchone():
                    logger.warning(f"User creation failed - email already exists: {email}")
                    return None
                
                # Create user
                cursor.execute("""
                    INSERT INTO users (email, password_hash, username, first_name, last_name, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (email, password_hash, username, first_name, last_name, datetime.now()))
                
                user_id = cursor.lastrowid
                
                # Create default favorites collection
                cursor.execute("""
                    INSERT INTO collections (name, description, user_id, is_favorite, created_at)
                    VALUES ('My Favorites', 'Default favorites collection', ?, 1, ?)
                """, (user_id, datetime.now()))
                
                conn.commit()
                
                # Return created user
                return self.get_user_by_id(user_id)
                
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (email,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_user(row)
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_user(row)
            return None
    
    def update_user_preferences(self, user_id: int, preferences: UserPreferences) -> bool:
        """Update user preferences"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET preferences = ? WHERE id = ?
                """, (preferences.to_json(), user_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to update user preferences: {e}")
            return False
    
    def store_api_key(self, user_id: int, service: str, encrypted_key: str) -> bool:
        """Store encrypted API key for a user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current api_keys
                cursor.execute("SELECT api_keys FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                if not row:
                    return False
                
                # Parse existing api_keys JSON
                try:
                    api_keys = json.loads(row[0]) if row[0] else {}
                except json.JSONDecodeError:
                    api_keys = {}
                
                # Update with new key
                api_keys[service] = encrypted_key
                
                # Save back to database
                cursor.execute("""
                    UPDATE users SET api_keys = ? WHERE id = ?
                """, (json.dumps(api_keys), user_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to store API key: {e}")
            return False
    
    def update_last_login(self, user_id: int) -> bool:
        """Update user's last login timestamp and increment login count"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET last_login = ?, login_count = login_count + 1 
                    WHERE id = ?
                """, (datetime.now(), user_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to update last login: {e}")
            return False
    
    # Session Management Methods
    
    def create_session(self, user_id: int, session_token: str, expires_at: datetime,
                      ip_address: str = "", user_agent: str = "") -> bool:
        """Create a new user session"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, session_token, expires_at, ip_address, user_agent))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return False
    
    def get_session(self, session_token: str) -> Optional[UserSession]:
        """Get session by token"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, u.email, u.username 
                FROM user_sessions s 
                JOIN users u ON s.user_id = u.id 
                WHERE s.session_token = ? AND (s.expires_at IS NULL OR s.expires_at > ?)
            """, (session_token, datetime.now()))
            
            row = cursor.fetchone()
            if row:
                return UserSession(
                    user_id=row['user_id'],
                    email=row['email'],
                    username=row['username'] or '',
                    session_token=row['session_token'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                    last_activity=datetime.fromisoformat(row['last_activity']),
                    ip_address=row['ip_address'],
                    user_agent=row['user_agent']
                )
            return None
    
    def update_session_activity(self, session_token: str) -> bool:
        """Update session last activity timestamp"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_sessions SET last_activity = ? WHERE session_token = ?
                """, (datetime.now(), session_token))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")
            return False
    
    def delete_session(self, session_token: str) -> bool:
        """Delete a session (logout)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM user_sessions WHERE session_token = ?", (session_token,))
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM user_sessions 
                    WHERE expires_at IS NOT NULL AND expires_at < ?
                """, (datetime.now(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} expired sessions")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    # Recipe Management Methods
    
    def create_recipe(self, recipe_data: Dict[str, Any], user_id: int) -> Optional[Recipe]:
        """Create a new recipe with ingredients"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert recipe
                cursor.execute("""
                    INSERT INTO recipes (
                        name, description, instructions, prep_time_minutes, cook_time_minutes,
                        servings, difficulty_level, cuisine_type, meal_category, dietary_tags,
                        nutritional_info, created_by, source_url, is_public
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    recipe_data['name'],
                    recipe_data.get('description', ''),
                    recipe_data['instructions'],
                    recipe_data.get('prep_time_minutes', 0),
                    recipe_data.get('cook_time_minutes', 0),
                    recipe_data.get('servings', 1),
                    recipe_data.get('difficulty_level', 'medium'),
                    recipe_data.get('cuisine_type', ''),
                    recipe_data.get('meal_category', ''),
                    ','.join(recipe_data.get('dietary_tags', [])),
                    json.dumps(recipe_data.get('nutritional_info', {})),
                    user_id,
                    recipe_data.get('source_url', ''),
                    recipe_data.get('is_public', True)
                ))
                
                recipe_id = cursor.lastrowid
                
                # Insert recipe ingredients
                ingredients = recipe_data.get('ingredients', [])
                for i, ingredient_data in enumerate(ingredients):
                    cursor.execute("""
                        INSERT INTO recipe_ingredients (
                            recipe_id, ingredient_id, quantity, unit, preparation_note, ingredient_order
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        recipe_id,
                        ingredient_data['ingredient_id'],
                        ingredient_data['quantity'],
                        ingredient_data['unit'],
                        ingredient_data.get('preparation_note', ''),
                        i + 1
                    ))
                
                conn.commit()
                return self.get_recipe_by_id(recipe_id)
                
        except Exception as e:
            logger.error(f"Failed to create recipe: {e}")
            return None
    
    def get_recipe_by_id(self, recipe_id: int, include_ingredients: bool = True) -> Optional[Recipe]:
        """Get recipe by ID with optional ingredient details"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get recipe data
            cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            recipe = self._row_to_recipe(row)
            
            if include_ingredients:
                # Get recipe ingredients
                cursor.execute("""
                    SELECT ri.*, i.name as ingredient_name
                    FROM recipe_ingredients ri
                    JOIN ingredients i ON ri.ingredient_id = i.id
                    WHERE ri.recipe_id = ?
                    ORDER BY ri.ingredient_order
                """, (recipe_id,))
                
                ingredient_rows = cursor.fetchall()
                recipe.ingredients = [self._row_to_recipe_ingredient(row) for row in ingredient_rows]
                recipe.required_ingredient_ids = {row['ingredient_id'] for row in ingredient_rows}
            
            return recipe
    
    def get_recipes_by_ingredients(self, ingredient_ids: List[int], user_id: int = None, 
                                 exact_match: bool = False) -> List[Recipe]:
        """
        Get recipes that can be made with given ingredients.
        Implements AND logic filtering as per requirements.
        """
        if not ingredient_ids:
            return []
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build query for ingredient filtering
            ingredient_placeholders = ','.join(['?'] * len(ingredient_ids))
            
            if exact_match:
                # Recipes that use ONLY these ingredients
                query = f"""
                    SELECT DISTINCT r.*
                    FROM recipes r
                    WHERE r.is_public = 1 OR r.created_by = ?
                    AND r.id IN (
                        SELECT ri.recipe_id
                        FROM recipe_ingredients ri
                        WHERE ri.ingredient_id IN ({ingredient_placeholders})
                        GROUP BY ri.recipe_id
                        HAVING COUNT(DISTINCT ri.ingredient_id) = (
                            SELECT COUNT(*) FROM recipe_ingredients WHERE recipe_id = ri.recipe_id
                        )
                        AND COUNT(DISTINCT ri.ingredient_id) = ?
                    )
                    ORDER BY r.rating DESC, r.name ASC
                """
                params = [user_id or 0] + ingredient_ids + [len(ingredient_ids)]
            else:
                # Recipes that can be made with these ingredients (may use subset)
                query = f"""
                    SELECT DISTINCT r.*
                    FROM recipes r
                    JOIN recipe_ingredients ri ON r.id = ri.recipe_id
                    WHERE (r.is_public = 1 OR r.created_by = ?)
                    AND r.id NOT IN (
                        SELECT DISTINCT ri2.recipe_id
                        FROM recipe_ingredients ri2
                        WHERE ri2.ingredient_id NOT IN ({ingredient_placeholders})
                    )
                    ORDER BY r.rating DESC, r.name ASC
                """
                params = [user_id or 0] + ingredient_ids
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            recipes = []
            for row in rows:
                recipe = self._row_to_recipe(row)
                # Load ingredient IDs for filtering logic
                recipe.required_ingredient_ids = self._get_recipe_ingredient_ids(recipe.id, conn)
                recipes.append(recipe)
            
            return recipes
    
    def search_recipes(self, query: str, user_id: int = None, filters: Dict[str, Any] = None) -> List[Recipe]:
        """
        Search recipes with fuzzy matching on names and descriptions.
        Supports additional filters for cuisine, difficulty, etc.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Base query with fuzzy search
            base_query = """
                SELECT DISTINCT r.*
                FROM recipes r
                WHERE (r.is_public = 1 OR r.created_by = ?)
                AND (
                    r.name LIKE ? 
                    OR r.description LIKE ?
                    OR r.cuisine_type LIKE ?
                    OR r.meal_category LIKE ?
                )
            """
            
            # Parameters for base query
            search_term = f"%{query}%"
            params = [user_id or 0, search_term, search_term, search_term, search_term]
            
            # Add filters
            if filters:
                if filters.get('cuisine_type'):
                    base_query += " AND r.cuisine_type = ?"
                    params.append(filters['cuisine_type'])
                
                if filters.get('difficulty_level'):
                    base_query += " AND r.difficulty_level = ?"
                    params.append(filters['difficulty_level'])
                
                if filters.get('meal_category'):
                    base_query += " AND r.meal_category = ?"
                    params.append(filters['meal_category'])
                
                if filters.get('max_cook_time'):
                    base_query += " AND (r.prep_time_minutes + r.cook_time_minutes) <= ?"
                    params.append(filters['max_cook_time'])
                
                if filters.get('dietary_tags'):
                    # Filter by dietary tags (inclusive)
                    dietary_conditions = []
                    for tag in filters['dietary_tags']:
                        dietary_conditions.append("r.dietary_tags LIKE ?")
                        params.append(f"%{tag}%")
                    if dietary_conditions:
                        base_query += " AND (" + " OR ".join(dietary_conditions) + ")"
            
            base_query += " ORDER BY r.rating DESC, r.name ASC LIMIT 100"
            
            cursor.execute(base_query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_recipe(row) for row in rows]
    
    def get_all_recipes(self, user_id: int = None, limit: int = 100, offset: int = 0) -> List[Recipe]:
        """Get all accessible recipes for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM recipes
                WHERE is_public = 1 OR created_by = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (user_id or 0, limit, offset))
            
            rows = cursor.fetchall()
            return [self._row_to_recipe(row) for row in rows]
    
    def update_recipe(self, recipe_id: int, recipe_data: Dict[str, Any], user_id: int) -> bool:
        """Update an existing recipe (only by creator)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check ownership
                cursor.execute("SELECT created_by FROM recipes WHERE id = ?", (recipe_id,))
                row = cursor.fetchone()
                if not row or row[0] != user_id:
                    logger.warning(f"User {user_id} attempted to update recipe {recipe_id} without permission")
                    return False
                
                # Update recipe
                cursor.execute("""
                    UPDATE recipes SET
                        name = ?, description = ?, instructions = ?,
                        prep_time_minutes = ?, cook_time_minutes = ?, servings = ?,
                        difficulty_level = ?, cuisine_type = ?, meal_category = ?,
                        dietary_tags = ?, nutritional_info = ?, updated_at = ?
                    WHERE id = ?
                """, (
                    recipe_data['name'],
                    recipe_data.get('description', ''),
                    recipe_data['instructions'],
                    recipe_data.get('prep_time_minutes', 0),
                    recipe_data.get('cook_time_minutes', 0),
                    recipe_data.get('servings', 1),
                    recipe_data.get('difficulty_level', 'medium'),
                    recipe_data.get('cuisine_type', ''),
                    recipe_data.get('meal_category', ''),
                    ','.join(recipe_data.get('dietary_tags', [])),
                    json.dumps(recipe_data.get('nutritional_info', {})),
                    datetime.now(),
                    recipe_id
                ))
                
                # Update ingredients if provided
                if 'ingredients' in recipe_data:
                    # Delete existing ingredients
                    cursor.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
                    
                    # Insert new ingredients
                    for i, ingredient_data in enumerate(recipe_data['ingredients']):
                        cursor.execute("""
                            INSERT INTO recipe_ingredients (
                                recipe_id, ingredient_id, quantity, unit, preparation_note, ingredient_order
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            recipe_id,
                            ingredient_data['ingredient_id'],
                            ingredient_data['quantity'],
                            ingredient_data['unit'],
                            ingredient_data.get('preparation_note', ''),
                            i + 1
                        ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to update recipe: {e}")
            return False
    
    def delete_recipe(self, recipe_id: int, user_id: int) -> bool:
        """Delete a recipe (only by creator)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check ownership
                cursor.execute("SELECT created_by FROM recipes WHERE id = ?", (recipe_id,))
                row = cursor.fetchone()
                if not row or row[0] != user_id:
                    logger.warning(f"User {user_id} attempted to delete recipe {recipe_id} without permission")
                    return False
                
                # Delete recipe (cascade will handle ingredients and collections)
                cursor.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to delete recipe: {e}")
            return False
    
    # Ingredient Management Methods
    
    def get_all_ingredients(self) -> List[Ingredient]:
        """Get all ingredients from database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ingredients ORDER BY name")
            rows = cursor.fetchall()
            return [self._row_to_ingredient(row) for row in rows]
    
    def get_ingredient_by_id(self, ingredient_id: int) -> Optional[Ingredient]:
        """Get ingredient by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ingredients WHERE id = ?", (ingredient_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_ingredient(row)
            return None
    
    def search_ingredients(self, query: str) -> List[Ingredient]:
        """Search ingredients by name"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM ingredients 
                WHERE name LIKE ? OR category LIKE ?
                ORDER BY 
                    CASE WHEN name LIKE ? THEN 1 ELSE 2 END,
                    name
                LIMIT 20
            """, (f"%{query}%", f"%{query}%", f"{query}%"))
            
            rows = cursor.fetchall()
            return [self._row_to_ingredient(row) for row in rows]
    
    def create_ingredient(self, name: str, category: str = "", **kwargs) -> Optional[Ingredient]:
        """Create a new ingredient"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
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
    
    # Helper Methods
    
    def _get_recipe_ingredient_ids(self, recipe_id: int, conn) -> Set[int]:
        """Get set of ingredient IDs for a recipe"""
        cursor = conn.cursor()
        cursor.execute("SELECT ingredient_id FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
        return {row[0] for row in cursor.fetchall()}
    
    def _row_to_recipe(self, row) -> Recipe:
        """Convert database row to Recipe object"""
        # Parse JSON fields safely
        try:
            nutritional_info = NutritionData(**json.loads(row['nutritional_info'])) if row['nutritional_info'] else None
        except (json.JSONDecodeError, TypeError):
            nutritional_info = None
        
        dietary_tags = [tag.strip() for tag in row['dietary_tags'].split(',') if tag.strip()] if row['dietary_tags'] else []
        
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
            dietary_tags=dietary_tags,
            nutritional_info=nutritional_info,
            created_by=row['created_by'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            source_url=row['source_url'],
            is_public=bool(row['is_public']),
            rating=row['rating'],
            rating_count=row['rating_count']
        )
    
    def _row_to_ingredient(self, row) -> Ingredient:
        """Convert database row to Ingredient object"""
        try:
            nutritional_data = NutritionData(**json.loads(row['nutritional_data'])) if row['nutritional_data'] else None
        except (json.JSONDecodeError, TypeError):
            nutritional_data = None
        
        common_substitutes = [sub.strip() for sub in row['common_substitutes'].split(',') if sub.strip()] if row['common_substitutes'] else []
        
        return Ingredient(
            id=row['id'],
            name=row['name'],
            category=row['category'],
            common_substitutes=common_substitutes,
            storage_tips=row['storage_tips'],
            nutritional_data=nutritional_data,
            created_at=datetime.fromisoformat(row['created_at'])
        )
    
    def _row_to_recipe_ingredient(self, row) -> RecipeIngredient:
        """Convert database row to RecipeIngredient object"""
        return RecipeIngredient(
            recipe_id=row['recipe_id'],
            ingredient_id=row['ingredient_id'],
            quantity=row['quantity'],
            unit=row['unit'],
            preparation_note=row['preparation_note'],
            ingredient_order=row['ingredient_order']
        )
    
    # Helper Methods
    
    def _row_to_user(self, row) -> User:
        """Convert database row to User object"""
        # Parse JSON fields safely
        try:
            api_keys = json.loads(row['api_keys']) if row['api_keys'] else {}
        except json.JSONDecodeError:
            api_keys = {}
        
        try:
            preferences = UserPreferences.from_json(row['preferences']) if row['preferences'] else UserPreferences()
        except:
            preferences = UserPreferences()
        
        return User(
            id=row['id'],
            email=row['email'],
            password_hash=row['password_hash'],
            username=row['username'] or '',
            first_name=row['first_name'] or '',
            last_name=row['last_name'] or '',
            is_active=bool(row['is_active']),
            is_verified=bool(row['is_verified']),
            api_keys=api_keys,
            preferences=preferences,
            created_at=datetime.fromisoformat(row['created_at']),
            last_login=datetime.fromisoformat(row['last_login']),
            login_count=row['login_count']
        )


# Global database service instance
_database_service: Optional[DatabaseService] = None


def get_database_service(db_path: str = "pans_cookbook.db") -> DatabaseService:
    """Get singleton database service instance"""
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService(db_path)
    return _database_service


def initialize_database_for_testing(db_path: str = ":memory:") -> DatabaseService:
    """Create database service for testing with in-memory database"""
    return DatabaseService(db_path)