#!/usr/bin/env python3
"""
Direct SQLite database inspection tool for Pans Cookbook.
Shows exactly what's in the database without going through the service layer.
"""

import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def inspect_database():
    """Directly inspect the SQLite database"""
    
    # Get database path
    db_path = os.getenv('DATABASE_PATH', 'database/pans_cookbook.db')
    db_path = str(Path(db_path).resolve())
    
    print(f"[INSPECT] Inspecting database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Database file does not exist: {db_path}")
        return
    
    file_size = os.path.getsize(db_path)
    print(f"[FILE] Database file size: {file_size} bytes")
    
    try:
        # Connect directly to SQLite
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("\n[TABLES] Database Tables:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table['name']
            if table_name.startswith('sqlite_'):
                continue
                
            print(f"\n[TABLE] {table_name}")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   [ROWS] {count}")
            
            # Show table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print("   [COLUMNS]:")
            for col in columns:
                print(f"      - {col['name']} ({col['type']})")
            
            # Show sample data for small tables
            if count > 0 and count <= 10:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                rows = cursor.fetchall()
                print("   [SAMPLE DATA]:")
                for row in rows:
                    row_dict = dict(row)
                    print(f"      {row_dict}")
            elif count > 0:
                # For larger tables, just show first few
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                rows = cursor.fetchall()
                print("   [SAMPLE DATA] (first 3 rows):")
                for row in rows:
                    row_dict = dict(row)
                    print(f"      {row_dict}")
        
        # Special focus on ingredients table
        print("\n[INGREDIENTS] DETAILED ANALYSIS:")
        cursor.execute("SELECT COUNT(*) FROM ingredients")
        ing_count = cursor.fetchone()[0]
        print(f"   Total ingredients: {ing_count}")
        
        if ing_count > 0:
            # Show all ingredients
            cursor.execute("SELECT id, name, category FROM ingredients ORDER BY id")
            ingredients = cursor.fetchall()
            print("   All ingredients:")
            for ing in ingredients:
                print(f"      ID: {ing['id']}, Name: '{ing['name']}', Category: '{ing['category']}'")
        
        # Check user_pantry table
        print("\n[PANTRY] ANALYSIS:")
        cursor.execute("SELECT COUNT(*) FROM user_pantry")
        pantry_count = cursor.fetchone()[0]
        print(f"   Total pantry items: {pantry_count}")
        
        if pantry_count > 0:
            cursor.execute("""
                SELECT up.*, i.name as ingredient_name 
                FROM user_pantry up 
                LEFT JOIN ingredients i ON up.ingredient_id = i.id 
                ORDER BY up.id
            """)
            pantry_items = cursor.fetchall()
            print("   All pantry items:")
            for item in pantry_items:
                print(f"      ID: {item['id']}, Ingredient: '{item['ingredient_name']}', Available: {item['is_available']}")
        
        conn.close()
        print("\n[SUCCESS] Database inspection complete!")
        
    except Exception as e:
        print(f"[ERROR] Error inspecting database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_database()