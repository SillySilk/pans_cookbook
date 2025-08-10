#!/usr/bin/env python3
"""
SQLite database management for the herbalism app
Compatible with Streamlit Cloud deployment
"""
import sqlite3
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from typing import List, Set
import streamlit as st

# Database file path
DB_PATH = "herbalism.db"

@dataclass
class Herb:
    id: int
    name: str
    description: str
    symbol: str
    scientific_name: str = ""
    traditional_uses: str = ""
    craft_uses: str = ""
    current_evidence_summary: str = ""
    contraindications: str = ""
    interactions: str = ""
    toxicity_notes: str = ""

@dataclass
class Recipe:
    id: int
    name: str
    description: str
    instructions: str
    benefits: str
    category: str
    required_herb_ids: Set[int]
    route: str = ""
    safety_summary: str = ""
    contraindications: str = ""
    interactions: str = ""
    pediatric_note: str = ""
    pregnancy_note: str = ""
    sanitation_level: str = ""
    storage_instructions: str = ""
    shelf_life_days: int = 0
    batch_size_value: float = 0.0
    batch_size_unit: str = ""

def create_database():
    """Create the SQLite database with proper schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create herbs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS herbs (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            symbol TEXT DEFAULT '🌿',
            scientific_name TEXT DEFAULT '',
            traditional_uses TEXT DEFAULT '',
            craft_uses TEXT DEFAULT '',
            current_evidence_summary TEXT DEFAULT '',
            contraindications TEXT DEFAULT '',
            interactions TEXT DEFAULT '',
            toxicity_notes TEXT DEFAULT ''
        )
    ''')
    
    # Create recipes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            instructions TEXT,
            benefits TEXT,
            category TEXT,
            route TEXT DEFAULT '',
            safety_summary TEXT DEFAULT '',
            contraindications TEXT DEFAULT '',
            interactions TEXT DEFAULT '',
            pediatric_note TEXT DEFAULT '',
            pregnancy_note TEXT DEFAULT '',
            sanitation_level TEXT DEFAULT '',
            storage_instructions TEXT DEFAULT '',
            shelf_life_days INTEGER DEFAULT 0,
            batch_size_value REAL DEFAULT 0.0,
            batch_size_unit TEXT DEFAULT ''
        )
    ''')
    
    # Create recipe_herbs junction table for many-to-many relationship
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipe_herbs (
            recipe_id INTEGER,
            herb_id INTEGER,
            PRIMARY KEY (recipe_id, herb_id),
            FOREIGN KEY (recipe_id) REFERENCES recipes (id),
            FOREIGN KEY (herb_id) REFERENCES herbs (id)
        )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_herbs_name ON herbs(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipes_name ON recipes(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipes_category ON recipes(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipe_herbs_recipe ON recipe_herbs(recipe_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipe_herbs_herb ON recipe_herbs(herb_id)')
    
    conn.commit()
    conn.close()

def migrate_from_csv():
    """Migrate existing CSV data to SQLite"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Migrate herbs
        if Path("herbs.csv").exists():
            herbs_df = pd.read_csv("herbs.csv")
            print(f"Migrating {len(herbs_df)} herbs...")
            
            for _, row in herbs_df.iterrows():
                cursor.execute('''
                    INSERT OR REPLACE INTO herbs 
                    (id, name, description, symbol, scientific_name, traditional_uses, craft_uses,
                     current_evidence_summary, contraindications, interactions, toxicity_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    int(row['id']), row['name'], row.get('description', ''),
                    row.get('symbol', '🌿'), row.get('scientific_name', ''),
                    row.get('traditional_uses', ''), row.get('craft_uses', ''),
                    row.get('current_evidence_summary', ''),
                    row.get('contraindications', ''), row.get('interactions', ''),
                    row.get('toxicity_notes', '')
                ))
        
        # Migrate recipes
        if Path("recipes.csv").exists():
            recipes_df = pd.read_csv("recipes.csv")
            print(f"Migrating {len(recipes_df)} recipes...")
            
            for _, row in recipes_df.iterrows():
                # Insert recipe
                cursor.execute('''
                    INSERT OR REPLACE INTO recipes 
                    (id, name, description, instructions, benefits, category, route,
                     safety_summary, contraindications, interactions, pediatric_note,
                     pregnancy_note, sanitation_level, storage_instructions,
                     shelf_life_days, batch_size_value, batch_size_unit)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    int(row['id']), row['name'], row.get('description', ''),
                    row.get('instructions', '').replace('\\n', '\n'), row.get('benefits', ''),
                    row.get('category', ''), row.get('route', ''),
                    row.get('safety_summary', ''), row.get('contraindications', ''),
                    row.get('interactions', ''), row.get('pediatric_note', ''),
                    row.get('pregnancy_note', ''), row.get('sanitation_level', ''),
                    row.get('storage_instructions', ''), 
                    int(row.get('shelf_life_days', 0)) if pd.notna(row.get('shelf_life_days')) else 0,
                    float(row.get('batch_size_value', 0.0)) if pd.notna(row.get('batch_size_value')) else 0.0,
                    row.get('batch_size_unit', '')
                ))
                
                # Insert recipe-herb relationships
                recipe_id = int(row['id'])
                if pd.notna(row.get('required_herb_ids', '')):
                    herb_ids = str(row['required_herb_ids']).split(';')
                    for herb_id_str in herb_ids:
                        if herb_id_str.strip().isdigit():
                            herb_id = int(herb_id_str.strip())
                            cursor.execute('''
                                INSERT OR IGNORE INTO recipe_herbs (recipe_id, herb_id)
                                VALUES (?, ?)
                            ''', (recipe_id, herb_id))
        
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()

@st.cache_data
def load_herbs_from_db() -> List[Herb]:
    """Load herbs from SQLite database"""
    if not Path(DB_PATH).exists():
        return []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM herbs ORDER BY name')
        herbs = []
        for row in cursor.fetchall():
            herbs.append(Herb(
                id=row[0], name=row[1], description=row[2], symbol=row[3],
                scientific_name=row[4], traditional_uses=row[5], craft_uses=row[6],
                current_evidence_summary=row[7], contraindications=row[8],
                interactions=row[9], toxicity_notes=row[10]
            ))
        return herbs
    finally:
        conn.close()

@st.cache_data
def load_recipes_from_db() -> List[Recipe]:
    """Load recipes from SQLite database"""
    if not Path(DB_PATH).exists():
        return []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get all recipes
        cursor.execute('SELECT * FROM recipes ORDER BY name')
        recipes = []
        
        for row in cursor.fetchall():
            recipe_id = row[0]
            
            # Get required herbs for this recipe
            cursor.execute('''
                SELECT herb_id FROM recipe_herbs WHERE recipe_id = ?
            ''', (recipe_id,))
            herb_ids = {herb_row[0] for herb_row in cursor.fetchall()}
            
            recipes.append(Recipe(
                id=recipe_id, name=row[1], description=row[2], instructions=row[3],
                benefits=row[4], category=row[5], required_herb_ids=herb_ids,
                route=row[6], safety_summary=row[7], contraindications=row[8],
                interactions=row[9], pediatric_note=row[10], pregnancy_note=row[11],
                sanitation_level=row[12], storage_instructions=row[13],
                shelf_life_days=row[14], batch_size_value=row[15], batch_size_unit=row[16]
            ))
        
        return recipes
    finally:
        conn.close()

def update_recipe(recipe: Recipe):
    """Update an existing recipe in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Update the main recipe details
        cursor.execute("""
            UPDATE recipes
            SET name = ?, description = ?, instructions = ?, benefits = ?, category = ?,
                route = ?, safety_summary = ?, contraindications = ?, interactions = ?,
                pediatric_note = ?, pregnancy_note = ?, sanitation_level = ?,
                storage_instructions = ?, shelf_life_days = ?, batch_size_value = ?,
                batch_size_unit = ?
            WHERE id = ?
        """, (
            recipe.name, recipe.description, recipe.instructions, recipe.benefits,
            recipe.category, recipe.route, recipe.safety_summary,
            recipe.contraindications, recipe.interactions, recipe.pediatric_note,
            recipe.pregnancy_note, recipe.sanitation_level,
            recipe.storage_instructions, recipe.shelf_life_days,
            recipe.batch_size_value, recipe.batch_size_unit, recipe.id
        ))

        # Update the recipe-herb relationships
        # First, delete all existing relationships for this recipe
        cursor.execute("DELETE FROM recipe_herbs WHERE recipe_id = ?", (recipe.id,))
        # Then, insert the new relationships
        if recipe.required_herb_ids:
            for herb_id in recipe.required_herb_ids:
                cursor.execute("INSERT INTO recipe_herbs (recipe_id, herb_id) VALUES (?, ?)", (recipe.id, herb_id))

        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error updating recipe: {e}")
        raise
    finally:
        conn.close()

def delete_recipe(recipe_id: int):
    """Delete a recipe and all its relationships from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")
        # Delete recipe-herb relationships
        cursor.execute("DELETE FROM recipe_herbs WHERE recipe_id = ?", (recipe_id,))
        # Delete the recipe
        cursor.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error deleting recipe: {e}")
        raise
    finally:
        conn.close()

def get_database_stats():
    """Get database statistics for debugging"""
    if not Path(DB_PATH).exists():
        return {"herbs": 0, "recipes": 0, "db_size": 0}
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT COUNT(*) FROM herbs')
        herb_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM recipes')
        recipe_count = cursor.fetchone()[0]
        
        db_size = Path(DB_PATH).stat().st_size
        
        return {
            "herbs": herb_count,
            "recipes": recipe_count,
            "db_size": db_size,
            "db_size_mb": round(db_size / 1024 / 1024, 2)
        }
    finally:
        conn.close()

def initialize_database():
    """Initialize database - call this once to set up everything"""
    print("Creating database schema...")
    create_database()
    
    print("Migrating CSV data...")
    migrate_from_csv()
    
    print("Database initialization complete!")
    stats = get_database_stats()
    print(f"Database contains: {stats['herbs']} herbs, {stats['recipes']} recipes")
    print(f"Database size: {stats['db_size_mb']} MB")

if __name__ == "__main__":
    initialize_database()