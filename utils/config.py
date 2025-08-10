"""
Configuration management for Pans Cookbook application.

Handles environment variables, database settings, and application configuration.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Application configuration settings"""
    
    # Database settings
    database_path: str = "pans_cookbook.db"
    database_backup_enabled: bool = True
    database_backup_interval_hours: int = 24
    
    # Authentication settings
    session_duration_hours: int = 24
    password_min_length: int = 8
    max_login_attempts: int = 5
    
    # Web scraping settings
    scraping_enabled: bool = True
    scraping_delay_seconds: int = 5
    scraping_timeout_seconds: int = 30
    max_concurrent_scrapes: int = 3
    
    # AI integration settings
    ai_enabled: bool = True
    ai_timeout_seconds: int = 30
    supported_ai_services: list = None
    
    # Streamlit settings
    streamlit_port: int = 8501
    streamlit_host: str = "localhost"
    debug_mode: bool = False
    
    # File storage
    upload_directory: str = "uploads"
    max_upload_size_mb: int = 10
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "pans_cookbook.log"
    
    def __post_init__(self):
        """Initialize default values that need processing"""
        if self.supported_ai_services is None:
            self.supported_ai_services = ["openai", "anthropic", "ollama"]
    
    @classmethod
    def from_environment(cls) -> 'Config':
        """Create configuration from environment variables"""
        return cls(
            # Database
            database_path=os.getenv("PANS_DB_PATH", "pans_cookbook.db"),
            database_backup_enabled=os.getenv("PANS_DB_BACKUP_ENABLED", "true").lower() == "true",
            database_backup_interval_hours=int(os.getenv("PANS_DB_BACKUP_INTERVAL", "24")),
            
            # Authentication
            session_duration_hours=int(os.getenv("PANS_SESSION_DURATION", "24")),
            password_min_length=int(os.getenv("PANS_PASSWORD_MIN_LENGTH", "8")),
            max_login_attempts=int(os.getenv("PANS_MAX_LOGIN_ATTEMPTS", "5")),
            
            # Scraping
            scraping_enabled=os.getenv("PANS_SCRAPING_ENABLED", "true").lower() == "true",
            scraping_delay_seconds=int(os.getenv("PANS_SCRAPING_DELAY", "5")),
            scraping_timeout_seconds=int(os.getenv("PANS_SCRAPING_TIMEOUT", "30")),
            max_concurrent_scrapes=int(os.getenv("PANS_MAX_CONCURRENT_SCRAPES", "3")),
            
            # AI
            ai_enabled=os.getenv("PANS_AI_ENABLED", "true").lower() == "true",
            ai_timeout_seconds=int(os.getenv("PANS_AI_TIMEOUT", "30")),
            
            # Streamlit
            streamlit_port=int(os.getenv("PANS_PORT", "8501")),
            streamlit_host=os.getenv("PANS_HOST", "localhost"),
            debug_mode=os.getenv("PANS_DEBUG", "false").lower() == "true",
            
            # File storage
            upload_directory=os.getenv("PANS_UPLOAD_DIR", "uploads"),
            max_upload_size_mb=int(os.getenv("PANS_MAX_UPLOAD_MB", "10")),
            
            # Logging
            log_level=os.getenv("PANS_LOG_LEVEL", "INFO"),
            log_file=os.getenv("PANS_LOG_FILE", "pans_cookbook.log")
        )
    
    def ensure_directories(self):
        """Create necessary directories"""
        directories = [
            self.upload_directory,
            Path(self.log_file).parent,
            Path(self.database_path).parent
        ]
        
        for directory in directories:
            if directory and directory != Path("."):
                Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get_database_url(self) -> str:
        """Get SQLite database URL"""
        return f"sqlite:///{self.database_path}"
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.debug_mode and os.getenv("PANS_ENVIRONMENT", "development") == "production"


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = Config.from_environment()
        _config.ensure_directories()
    return _config


def reload_config():
    """Reload configuration from environment"""
    global _config
    _config = None
    return get_config()