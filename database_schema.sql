-- Pans Cookbook Database Schema
-- SQLite database schema for recipe management application
-- Adapted from Herbalism app patterns with recipe-specific tables

-- Users table for authentication and preferences
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    username TEXT UNIQUE,
    first_name TEXT DEFAULT '',
    last_name TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    is_verified INTEGER DEFAULT 0,
    api_keys TEXT DEFAULT '{}',  -- JSON object of encrypted API keys
    preferences TEXT DEFAULT '{}',  -- JSON object of user preferences
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    login_count INTEGER DEFAULT 0
);

-- Ingredients table (similar to herbs in Herbalism app)
CREATE TABLE IF NOT EXISTS ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    category TEXT DEFAULT '',
    common_substitutes TEXT DEFAULT '',  -- comma-separated list
    storage_tips TEXT DEFAULT '',
    nutritional_data TEXT DEFAULT '{}',  -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Recipes table (similar to recipes in Herbalism app but expanded)
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    instructions TEXT NOT NULL,
    prep_time_minutes INTEGER DEFAULT 0,
    cook_time_minutes INTEGER DEFAULT 0,
    servings INTEGER DEFAULT 1,
    difficulty_level TEXT DEFAULT 'medium',  -- easy, medium, hard
    cuisine_type TEXT DEFAULT '',
    meal_category TEXT DEFAULT '',  -- breakfast, lunch, dinner, snack, dessert
    dietary_tags TEXT DEFAULT '',  -- comma-separated list
    nutritional_info TEXT DEFAULT '{}',  -- JSON object
    created_by INTEGER DEFAULT 0,  -- user_id
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_url TEXT DEFAULT '',
    is_public INTEGER DEFAULT 1,
    rating REAL DEFAULT NULL,
    rating_count INTEGER DEFAULT 0,
    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET DEFAULT
);

-- Recipe ingredients junction table (many-to-many relationship)
CREATE TABLE IF NOT EXISTS recipe_ingredients (
    recipe_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    preparation_note TEXT DEFAULT '',
    ingredient_order INTEGER DEFAULT 0,
    PRIMARY KEY (recipe_id, ingredient_id),
    FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients (id) ON DELETE CASCADE
);

-- Collections table for organizing recipes
CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    user_id INTEGER NOT NULL,
    tags TEXT DEFAULT '',  -- comma-separated list
    is_public INTEGER DEFAULT 0,
    is_favorite INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    share_token TEXT UNIQUE DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Collection recipes junction table (many-to-many relationship)  
CREATE TABLE IF NOT EXISTS collection_recipes (
    collection_id INTEGER NOT NULL,
    recipe_id INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (collection_id, recipe_id),
    FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE CASCADE
);

-- User sessions table for web authentication
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT DEFAULT '',
    user_agent TEXT DEFAULT '',
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Recipe ratings table for user ratings
CREATE TABLE IF NOT EXISTS recipe_ratings (
    user_id INTEGER NOT NULL,
    recipe_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, recipe_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE CASCADE
);

-- User pantry table for ingredient inventory management
CREATE TABLE IF NOT EXISTS user_pantry (
    user_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    is_available INTEGER DEFAULT 1,
    quantity_estimate TEXT DEFAULT NULL,  -- 'plenty', 'running low', 'just enough'
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT DEFAULT '',
    PRIMARY KEY (user_id, ingredient_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients (id) ON DELETE CASCADE
);

-- Scraping log table for tracking scraping operations
CREATE TABLE IF NOT EXISTS scraping_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    success INTEGER NOT NULL,
    recipe_id INTEGER DEFAULT NULL,
    error_message TEXT DEFAULT '',
    scraping_duration_seconds REAL DEFAULT 0,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE SET NULL
);

-- Indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_recipes_created_by ON recipes (created_by);
CREATE INDEX IF NOT EXISTS idx_recipes_cuisine ON recipes (cuisine_type);
CREATE INDEX IF NOT EXISTS idx_recipes_meal_category ON recipes (meal_category);
CREATE INDEX IF NOT EXISTS idx_recipes_difficulty ON recipes (difficulty_level);
CREATE INDEX IF NOT EXISTS idx_recipes_public ON recipes (is_public);
CREATE INDEX IF NOT EXISTS idx_recipes_rating ON recipes (rating);

CREATE INDEX IF NOT EXISTS idx_ingredients_name ON ingredients (name);
CREATE INDEX IF NOT EXISTS idx_ingredients_category ON ingredients (category);

CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe ON recipe_ingredients (recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_ingredient ON recipe_ingredients (ingredient_id);

CREATE INDEX IF NOT EXISTS idx_collections_user ON collections (user_id);
CREATE INDEX IF NOT EXISTS idx_collections_public ON collections (is_public);

CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions (session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions (expires_at);

CREATE INDEX IF NOT EXISTS idx_user_pantry_user ON user_pantry (user_id);
CREATE INDEX IF NOT EXISTS idx_user_pantry_ingredient ON user_pantry (ingredient_id);
CREATE INDEX IF NOT EXISTS idx_user_pantry_available ON user_pantry (is_available);

-- Sample data inserts (similar to Herbalism app CSV loading)

-- Default admin user
INSERT OR IGNORE INTO users (email, password_hash, username, first_name, is_verified) 
VALUES ('admin@panscookbook.local', 'placeholder_hash', 'admin', 'Administrator', 1);

-- DISABLED: Common ingredient auto-insertion removed per user request
-- Users should manually add ingredients via CSV import or pantry interface
-- INSERT OR IGNORE INTO ingredients (name, category) VALUES 
-- ('Salt', 'seasoning'),
-- ('Black Pepper', 'seasoning'), 
-- ('Olive Oil', 'oil'),
-- ('Butter', 'dairy'),
-- ('Garlic', 'vegetable'),
-- ('Onion', 'vegetable'),
-- ('All-Purpose Flour', 'grain'),
-- ('Sugar', 'sweetener'),
-- ('Eggs', 'protein'),
-- ('Chicken Breast', 'protein');

-- Default user collection
INSERT OR IGNORE INTO collections (name, description, user_id, is_favorite)
VALUES ('My Favorites', 'Default favorites collection', 1, 1);