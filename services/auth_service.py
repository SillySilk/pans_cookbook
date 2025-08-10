"""
Authentication service for Pans Cookbook application.

Handles user authentication, password hashing, session management,
and API key encryption. Built for secure multi-user web deployment.
"""

import hashlib
import secrets
import base64
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import bcrypt

from models import User, UserSession
from .database_service import DatabaseService, get_database_service

logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication service handling all security operations.
    Provides secure password hashing, session management, and API key encryption.
    """
    
    def __init__(self, database_service: Optional[DatabaseService] = None):
        self.db = database_service or get_database_service()
        self._encryption_key = None
    
    # Password Management
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    # User Registration and Authentication
    
    def register_user(self, email: str, password: str, username: str = "", 
                     first_name: str = "", last_name: str = "") -> Optional[User]:
        """Register a new user with password hashing"""
        try:
            # Validate email format (basic check)
            if '@' not in email or len(email) < 5:
                logger.warning("Invalid email format provided")
                return None
            
            # Validate password strength
            if not self._is_password_strong(password):
                logger.warning("Password does not meet strength requirements")
                return None
            
            # Hash password
            password_hash = self.hash_password(password)
            
            # Create user in database
            user = self.db.create_user(
                email=email.lower().strip(),
                password_hash=password_hash,
                username=username.strip(),
                first_name=first_name.strip(),
                last_name=last_name.strip()
            )
            
            if user:
                logger.info(f"User registered successfully: {email}")
            else:
                logger.warning(f"User registration failed: {email}")
            
            return user
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return None
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        try:
            # Get user from database
            user = self.db.get_user_by_email(email.lower().strip())
            if not user:
                logger.warning(f"Authentication failed - user not found: {email}")
                return None
            
            # Verify password
            if not self.verify_password(password, user.password_hash):
                logger.warning(f"Authentication failed - invalid password: {email}")
                return None
            
            # Update last login
            self.db.update_last_login(user.id)
            
            logger.info(f"User authenticated successfully: {email}")
            return user
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    # Session Management
    
    def create_session(self, user: User, ip_address: str = "", user_agent: str = "",
                      session_duration_hours: int = 24) -> Optional[str]:
        """Create a new user session"""
        try:
            # Generate secure session token
            session_token = self._generate_session_token()
            
            # Calculate expiration
            expires_at = datetime.now() + timedelta(hours=session_duration_hours)
            
            # Store session in database
            if self.db.create_session(
                user_id=user.id,
                session_token=session_token,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            ):
                logger.info(f"Session created for user: {user.email}")
                return session_token
            else:
                logger.error(f"Failed to store session for user: {user.email}")
                return None
                
        except Exception as e:
            logger.error(f"Session creation error: {e}")
            return None
    
    def validate_session(self, session_token: str) -> Optional[UserSession]:
        """Validate session token and return session info"""
        try:
            session = self.db.get_session(session_token)
            
            if session and not session.is_expired():
                # Update last activity
                self.db.update_session_activity(session_token)
                return session
            else:
                if session:
                    logger.info(f"Expired session removed: {session.email}")
                    self.db.delete_session(session_token)
                return None
                
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return None
    
    def logout_user(self, session_token: str) -> bool:
        """Logout user by deleting session"""
        try:
            success = self.db.delete_session(session_token)
            if success:
                logger.info("User logged out successfully")
            return success
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False
    
    # API Key Management
    
    def encrypt_api_key(self, api_key: str, user_password: str) -> str:
        """Encrypt API key using user password-derived key"""
        try:
            # Derive encryption key from user password
            encryption_key = self._derive_key_from_password(user_password)
            
            # Create Fernet cipher
            fernet = Fernet(encryption_key)
            
            # Encrypt API key
            encrypted_key = fernet.encrypt(api_key.encode('utf-8'))
            
            return base64.b64encode(encrypted_key).decode('utf-8')
            
        except Exception as e:
            logger.error(f"API key encryption error: {e}")
            raise
    
    def decrypt_api_key(self, encrypted_api_key: str, user_password: str) -> Optional[str]:
        """Decrypt API key using user password-derived key"""
        try:
            # Derive encryption key from user password
            encryption_key = self._derive_key_from_password(user_password)
            
            # Create Fernet cipher
            fernet = Fernet(encryption_key)
            
            # Decode and decrypt API key
            encrypted_data = base64.b64decode(encrypted_api_key.encode('utf-8'))
            decrypted_key = fernet.decrypt(encrypted_data)
            
            return decrypted_key.decode('utf-8')
            
        except Exception as e:
            logger.error(f"API key decryption error: {e}")
            return None
    
    def store_user_api_key(self, user_id: int, service: str, api_key: str, 
                          user_password: str) -> bool:
        """Store encrypted API key for user"""
        try:
            encrypted_key = self.encrypt_api_key(api_key, user_password)
            return self.db.store_api_key(user_id, service, encrypted_key)
            
        except Exception as e:
            logger.error(f"Failed to store API key: {e}")
            return False
    
    # Utility Methods
    
    def _is_password_strong(self, password: str) -> bool:
        """Check if password meets strength requirements"""
        if len(password) < 8:
            return False
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        return has_upper and has_lower and has_digit
    
    def _generate_session_token(self) -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(32)
    
    def _derive_key_from_password(self, password: str) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        # Use a fixed salt for consistency (in production, store per-user salts)
        salt = b"pans_cookbook_salt_2024"  # Should be random per user in production
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
        return key
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        return self.db.cleanup_expired_sessions()
    
    def get_password_strength_feedback(self, password: str) -> List[str]:
        """Get password strength feedback for UI"""
        feedback = []
        
        if len(password) < 8:
            feedback.append("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in password):
            feedback.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            feedback.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            feedback.append("Password must contain at least one number")
        
        if not feedback:
            feedback.append("Password strength: Good")
        
        return feedback