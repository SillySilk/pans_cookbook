# Database Migration Plan for Pans Cookbook

## Current Database Issues

**Problem:** We're using SQLite with multiple database files and threading issues:
- `pans_cookbook.db` (19 ingredients)
- `pans_cookbook_local.db` (unknown state)
- In-memory databases for Streamlit Cloud
- Thread-safety issues causing data loss
- Temporary files that don't persist

## Recommended Database Solutions

### Option 1: PostgreSQL (Recommended for Production)

**Pros:**
- Robust, ACID-compliant
- Excellent Streamlit Cloud support
- Built-in JSON support
- Concurrent user support
- Persistent and reliable

**Setup:**
```bash
# For local development
pip install psycopg2-binary

# For Streamlit Cloud
# Add to requirements.txt:
psycopg2-binary==2.9.7
```

**Connection String:**
```python
# Local PostgreSQL
DATABASE_URL = "postgresql://user:password@localhost:5432/pans_cookbook"

# Streamlit Cloud with Neon/Supabase
DATABASE_URL = st.secrets["DATABASE_URL"]
```

### Option 2: Supabase (Recommended for Streamlit Cloud)

**Pros:**
- PostgreSQL-based
- Free tier available
- Built-in auth and real-time features
- Excellent Streamlit integration
- Web dashboard for data management

**Setup:**
```bash
pip install supabase
```

**Integration:**
```python
from supabase import create_client

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_ANON_KEY"]
)
```

### Option 3: Neon (PostgreSQL as a Service)

**Pros:**
- Serverless PostgreSQL
- Free tier with 512MB storage
- Perfect for Streamlit Cloud
- Auto-scaling

**Setup:**
```python
import psycopg2
DATABASE_URL = st.secrets["NEON_DATABASE_URL"]
```

### Option 4: Streamlit Cloud + SQLite (Temporary Fix)

**Pros:**
- Minimal changes needed
- Works with current code

**Cons:**
- Data doesn't persist between deployments
- Thread-safety issues remain

## Migration Implementation

### Phase 1: Database Abstraction Layer

Create a database adapter that can work with both SQLite and PostgreSQL:

```python
# services/database_adapter.py
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

class DatabaseAdapter(ABC):
    @abstractmethod
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        pass
    
    @abstractmethod
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        pass
    
    @abstractmethod
    def get_connection(self):
        pass

class SQLiteAdapter(DatabaseAdapter):
    # Current SQLite implementation
    pass

class PostgreSQLAdapter(DatabaseAdapter):
    # New PostgreSQL implementation
    pass
```

### Phase 2: Environment-Based Configuration

```python
# config/database_config.py
import os
import streamlit as st

def get_database_config():
    if os.getenv('STREAMLIT_CLOUD'):
        # Use PostgreSQL on Streamlit Cloud
        return {
            'type': 'postgresql',
            'url': st.secrets["DATABASE_URL"]
        }
    else:
        # Use SQLite locally
        return {
            'type': 'sqlite',
            'path': 'pans_cookbook_local.db'
        }
```

### Phase 3: Data Migration Script

```python
# migration/migrate_to_postgresql.py
def migrate_sqlite_to_postgresql():
    # 1. Export all data from SQLite
    sqlite_data = export_sqlite_data()
    
    # 2. Create PostgreSQL schema
    create_postgresql_schema()
    
    # 3. Import data to PostgreSQL
    import_data_to_postgresql(sqlite_data)
    
    # 4. Verify migration
    verify_migration()
```

## Immediate Fix for Current Issues

### Step 1: Consolidate Database Files

```python
# Fix in main.py
def get_db_path():
    """Always use the same database file"""
    return "pans_cookbook_unified.db"  # Single source of truth
```

### Step 2: Add Database Debugging

```python
# services/database_debug.py
def debug_database_state(db_service):
    """Debug current database state"""
    stats = db_service.get_database_stats()
    st.write(f"Database path: {db_service.db_path}")
    st.write(f"File exists: {Path(db_service.db_path).exists()}")
    st.write(f"Ingredients: {stats.get('ingredients', 0)}")
    st.write(f"Recipes: {stats.get('recipes', 0)}")
    
    # Show recent ingredients
    ingredients = db_service.get_all_ingredients()
    if ingredients:
        st.write("Recent ingredients:")
        for ing in ingredients[-10:]:
            st.write(f"- {ing.name} (ID: {ing.id})")
```

### Step 3: Fix Threading Issues

```python
# services/database_service.py
class DatabaseService:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection_pool = {}  # Thread-safe connection pool
        self._lock = threading.Lock()
    
    def get_connection(self):
        thread_id = threading.get_ident()
        
        with self._lock:
            if thread_id not in self._connection_pool:
                self._connection_pool[thread_id] = sqlite3.connect(
                    self.db_path, 
                    check_same_thread=False
                )
            return self._connection_pool[thread_id]
```

## Recommended Action Plan

### Immediate (Today):
1. **Fix database path consistency** - Use single database file
2. **Add database debugging** - See what's actually in the database
3. **Test ingredient import again** - With debug output

### Short-term (This Week):
1. **Set up Supabase account** - Free PostgreSQL hosting
2. **Create database abstraction layer** - Prepare for migration
3. **Implement PostgreSQL adapter** - Support both databases

### Long-term (Next Week):
1. **Migrate to Supabase/PostgreSQL** - Full production setup
2. **Add data backup/restore** - Prevent data loss
3. **Implement proper error handling** - Robust database operations

## Cost Comparison

| Solution | Free Tier | Paid Plans | Best For |
|----------|-----------|------------|----------|
| Supabase | 500MB, 2 projects | $25/mo unlimited | Full-stack apps |
| Neon | 512MB | $19/mo 10GB | PostgreSQL focus |
| PlanetScale | 1GB | $29/mo 10GB | MySQL alternative |
| Local PostgreSQL | Free | Infrastructure costs | Development |

## Recommendation

**Start with Supabase** because:
1. ✅ PostgreSQL-based (robust and reliable)
2. ✅ Excellent Streamlit integration
3. ✅ Free tier sufficient for development
4. ✅ Web dashboard for data management
5. ✅ Built-in authentication (future feature)
6. ✅ Real-time subscriptions (future feature)

Would you like me to implement the immediate fixes first, or jump straight to setting up Supabase?