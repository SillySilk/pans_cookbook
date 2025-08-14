"""
Database configuration for Pans Cookbook application.

Enhanced SQLite configuration with proper threading support.
"""

import os
import streamlit as st
from typing import Dict, Any


class DatabaseConfig:
    """Enhanced SQLite database configuration manager"""
    
    @staticmethod
    def get_database_config() -> Dict[str, Any]:
        """Get database configuration"""
        db_type = os.getenv('DATABASE_TYPE', 'sqlite').lower()
        
        if db_type == 'sqlite':
            return {
                'type': 'sqlite',
                'path': DatabaseConfig._get_sqlite_path(),
                'description': 'Enhanced SQLite Database with WAL mode'
            }
        else:
            # Fallback to SQLite if other types fail
            return {
                'type': 'sqlite',
                'path': DatabaseConfig._get_sqlite_path(),
                'description': 'Enhanced SQLite Database (fallback)'
            }
    
    @staticmethod
    def _get_sqlite_path() -> str:
        """Get SQLite database path"""
        # Try environment variable first
        db_path = os.getenv('DATABASE_PATH')
        if db_path:
            return db_path
        
        # Try Streamlit secrets
        try:
            if hasattr(st, 'secrets') and 'DATABASE_PATH' in st.secrets:
                return st.secrets['DATABASE_PATH']
        except:
            pass
        
        # Default path - use root directory
        return 'pans_cookbook.db'
    

def get_database_service():
    """Get enhanced SQLite database service"""
    config = DatabaseConfig.get_database_config()
    
    if config['type'] == 'sqlite':
        from services.sqlite_service_v2 import get_enhanced_sqlite_service
        return get_enhanced_sqlite_service(config['path'])
    else:
        # This shouldn't happen with current config, but just in case
        from services.sqlite_service_v2 import get_enhanced_sqlite_service
        return get_enhanced_sqlite_service()


def get_database_info() -> Dict[str, Any]:
    """Get database configuration info"""
    config = DatabaseConfig.get_database_config()
    
    return {
        'type': config['type'],
        'description': config['description'],
        'path': config.get('path', 'Unknown'),
        'location': 'Local file' if config['type'] == 'sqlite' else 'Remote'
    }