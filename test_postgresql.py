#!/usr/bin/env python3
"""
Test PostgreSQL connection for Pans Cookbook.

Run this script to verify your database connection before starting the app.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
load_dotenv()

def test_postgresql_connection():
    """Test PostgreSQL connection"""
    print("[TEST] Testing PostgreSQL Connection...")
    print(f"   Environment: {os.getenv('DATABASE_TYPE', 'Not set')}")
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("[ERROR] DATABASE_URL not found in environment")
        print("   Please set DATABASE_URL in your .env file")
        return False
    
    # Mask password in display
    display_url = database_url.replace(database_url.split('@')[0].split(':')[-1], '[PASSWORD]') if '@' in database_url else database_url
    print(f"   URL: {display_url}")
    
    try:
        from services.postgresql_service import PostgreSQLService
        
        print("[CONNECT] Attempting connection...")
        db = PostgreSQLService(database_url)
        
        print("[SUCCESS] Connection successful!")
        print("[STATS] Getting database statistics...")
        
        stats = db.get_database_stats()
        print(f"   Ingredients: {stats.get('ingredients', 0)}")
        print(f"   Recipes: {stats.get('recipes', 0)}")
        print(f"   Pantry Items: {stats.get('user_pantry', 0)}")
        print(f"   Collections: {stats.get('collections', 0)}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        print("\n[TIPS] Troubleshooting tips:")
        print("   1. Check your DATABASE_URL in .env file")
        print("   2. Verify Supabase project is running")
        print("   3. Confirm password is correct")
        print("   4. Check internet connection")
        return False

if __name__ == "__main__":
    success = test_postgresql_connection()
    print("\n" + "="*50)
    if success:
        print("[READY] Ready to run Pans Cookbook with PostgreSQL!")
        print("   Run: streamlit run main.py")
    else:
        print("[FIX] Please fix database connection before continuing")
    print("="*50)