#!/usr/bin/env python3
"""
Fix database data integrity issues
"""
import sqlite3
import pandas as pd

def fix_database_data():
    """Fix any data integrity issues in the database"""
    
    # First, let's recreate the database from scratch with clean CSV data
    conn = sqlite3.connect('herbalism.db')
    cursor = conn.cursor()
    
    # Drop and recreate tables
    cursor.execute('DROP TABLE IF EXISTS recipe_herbs')
    cursor.execute('DROP TABLE IF EXISTS recipes')
    cursor.execute('DROP TABLE IF EXISTS herbs')
    
    # Recreate tables
    cursor.execute('''
        CREATE TABLE herbs (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            symbol TEXT DEFAULT '🌿',
            scientific_name TEXT DEFAULT '',
            traditional_uses TEXT DEFAULT '',
            current_evidence_summary TEXT DEFAULT '',
            contraindications TEXT DEFAULT '',
            interactions TEXT DEFAULT '',
            toxicity_notes TEXT DEFAULT ''
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE recipes (
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
    
    cursor.execute('''
        CREATE TABLE recipe_herbs (
            recipe_id INTEGER,
            herb_id INTEGER,
            PRIMARY KEY (recipe_id, herb_id),
            FOREIGN KEY (recipe_id) REFERENCES recipes (id),
            FOREIGN KEY (herb_id) REFERENCES herbs (id)
        )
    ''')
    
    # Now carefully load CSV data with validation
    df = pd.read_csv('herbs.csv')
    print(f"Loading {len(df)} herbs from CSV...")
    
    herbs_added = 0
    for _, row in df.iterrows():
        try:
            # Validate that name looks like a proper herb name (not a description)
            name = str(row['name']).strip()
            description = str(row['description']).strip() if pd.notna(row['description']) else ''
            
            # Skip if name looks like a description (contains botanical details)
            if any(word in name.lower() for word in ['annual', 'perennial', 'biennial', 'ft tall', 'evergreen', 'deciduous']):
                print(f"Skipping ID {row['id']}: Name appears to be description: '{name[:50]}...'")
                continue
            
            # Skip very short names (likely data errors)
            if len(name) < 2:
                print(f"Skipping ID {row['id']}: Name too short: '{name}'")
                continue
            
            cursor.execute('''
                INSERT INTO herbs 
                (id, name, description, symbol, scientific_name, traditional_uses, 
                 current_evidence_summary, contraindications, interactions, toxicity_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                int(row['id']), name, description,
                str(row.get('symbol', '🌿')), str(row.get('scientific_name', '')),
                str(row.get('traditional_uses', '')), str(row.get('current_evidence_summary', '')),
                str(row.get('contraindications', '')), str(row.get('interactions', '')),
                str(row.get('toxicity_notes', ''))
            ))
            herbs_added += 1
            
        except Exception as e:
            print(f"Error adding herb ID {row.get('id', 'unknown')}: {e}")
            continue
    
    # Load recipes if they exist
    if pd.io.common.file_exists('recipes.csv'):
        recipes_df = pd.read_csv('recipes.csv')
        print(f"Loading {len(recipes_df)} recipes from CSV...")
        
        for _, row in recipes_df.iterrows():
            try:
                cursor.execute('''
                    INSERT INTO recipes 
                    (id, name, description, instructions, benefits, category, route,
                     safety_summary, contraindications, interactions, pediatric_note,
                     pregnancy_note, sanitation_level, storage_instructions,
                     shelf_life_days, batch_size_value, batch_size_unit)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    int(row['id']), str(row['name']), str(row.get('description', '')),
                    str(row.get('instructions', '')).replace('\\n', '\n'), 
                    str(row.get('benefits', '')), str(row.get('category', '')), 
                    str(row.get('route', '')), str(row.get('safety_summary', '')), 
                    str(row.get('contraindications', '')), str(row.get('interactions', '')), 
                    str(row.get('pediatric_note', '')), str(row.get('pregnancy_note', '')), 
                    str(row.get('sanitation_level', '')), str(row.get('storage_instructions', '')),
                    int(row.get('shelf_life_days', 0)) if pd.notna(row.get('shelf_life_days')) else 0,
                    float(row.get('batch_size_value', 0.0)) if pd.notna(row.get('batch_size_value')) else 0.0,
                    str(row.get('batch_size_unit', ''))
                ))
                
                # Add recipe-herb relationships
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
                            
            except Exception as e:
                print(f"Error adding recipe ID {row.get('id', 'unknown')}: {e}")
                continue
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_herbs_name ON herbs(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipes_name ON recipes(name)')
    
    conn.commit()
    conn.close()
    
    print(f"Database rebuilt successfully! Added {herbs_added} clean herb records.")
    
    # Verify the fix
    conn = sqlite3.connect('herbalism.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM herbs')
    herb_count = cursor.fetchone()[0]
    cursor.execute('SELECT id, name FROM herbs ORDER BY name LIMIT 10')
    sample_herbs = cursor.fetchall()
    conn.close()
    
    print(f"Verification: Database now contains {herb_count} herbs")
    print("Sample herbs:")
    for herb_id, name in sample_herbs:
        print(f"  {herb_id}: {name}")

if __name__ == "__main__":
    fix_database_data()