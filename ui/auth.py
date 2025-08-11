"""
User authentication UI for Pans Cookbook application.

Provides user registration, login forms, session management, and user settings
with API key configuration. Leverages Streamlit session state patterns from Herbalism app.
"""

import streamlit as st
import re
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from models import User, UserPreferences, UserSession
from services import AuthService, get_database_service
from utils import get_logger

logger = get_logger(__name__)


class AuthenticationInterface:
    """
    User authentication and account management interface.
    
    Provides login/registration forms, session management, and user settings
    with secure API key configuration for optional AI features.
    """
    
    def __init__(self, auth_service: Optional[AuthService] = None):
        self.auth = auth_service or AuthService()
        
        # Session state keys
        self.USER_KEY = "authenticated_user"
        self.SESSION_KEY = "user_session"
        self.LOGIN_FORM_KEY = "show_login_form"
        
        # Available AI services for API key configuration
        self.AI_SERVICES = {
            "openai": {
                "name": "OpenAI (GPT)",
                "description": "For recipe suggestions and AI-powered features",
                "help": "Get your API key from https://platform.openai.com/api-keys"
            },
            "anthropic": {
                "name": "Anthropic (Claude)",
                "description": "For recipe analysis and cooking tips",
                "help": "Get your API key from https://console.anthropic.com/"
            }
        }
        
        # Inject custom CSS
        self._inject_custom_css()
    
    def render_auth_sidebar(self) -> Optional[User]:
        """
        Render authentication sidebar component.
        
        Returns:
            Currently authenticated user or None
        """
        current_user = self.get_current_user()
        
        if current_user:
            return self._render_authenticated_sidebar(current_user)
        else:
            return self._render_login_sidebar()
    
    def render_login_page(self) -> Optional[User]:
        """
        Render full login/registration page.
        
        Returns:
            User if login/registration successful, None otherwise
        """
        st.title("🔐 Welcome to Pans Cookbook")
        st.markdown("*Your personal recipe management system*")
        
        # Check if user is already logged in
        current_user = self.get_current_user()
        if current_user:
            st.success(f"✅ Welcome back, {current_user.get_display_name()}!")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("📚 Go to Recipe Browser"):
                    st.switch_page("recipe_browser")
            with col2:
                if st.button("🚪 Logout"):
                    self.logout()
                    st.rerun()
            
            return current_user
        
        # Show login/registration tabs
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Create Account"])
        
        with tab1:
            user = self._render_login_form()
            if user:
                return user
        
        with tab2:
            user = self._render_registration_form()
            if user:
                return user
        
        return None
    
    def render_user_settings(self, user: User) -> bool:
        """
        Render user settings page.
        
        Args:
            user: Current authenticated user
            
        Returns:
            True if settings were saved
        """
        st.header(f"⚙️ Settings for {user.get_display_name()}")
        
        # Settings tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "👤 Profile", "🍽️ Preferences", "🤖 AI Settings", "🔒 Security"
        ])
        
        settings_saved = False
        
        with tab1:
            if self._render_profile_settings(user):
                settings_saved = True
        
        with tab2:
            if self._render_preference_settings(user):
                settings_saved = True
        
        with tab3:
            if self._render_api_key_settings(user):
                settings_saved = True
        
        with tab4:
            if self._render_security_settings(user):
                settings_saved = True
        
        return settings_saved
    
    def get_current_user(self) -> Optional[User]:
        """Get currently authenticated user from session state"""
        if self.USER_KEY in st.session_state:
            # Verify session is still valid
            user_session = st.session_state.get(self.SESSION_KEY)
            if user_session and not user_session.is_expired():
                user_session.refresh_activity()
                return st.session_state[self.USER_KEY]
            else:
                # Session expired, clear it
                self.logout()
        
        return None
    
    def logout(self):
        """Logout current user and clear session"""
        if self.SESSION_KEY in st.session_state:
            session = st.session_state[self.SESSION_KEY]
            self.auth.logout_user(session.session_token)
        
        # Clear session state
        st.session_state.pop(self.USER_KEY, None)
        st.session_state.pop(self.SESSION_KEY, None)
        
        logger.info("User logged out")
    
    def require_auth(self) -> Optional[User]:
        """Require authentication, redirect to login if not authenticated"""
        user = self.get_current_user()
        if not user:
            st.warning("🔒 Please log in to access this feature.")
            if st.button("🔑 Go to Login"):
                st.switch_page("login")
            st.stop()
        return user
    
    def _render_authenticated_sidebar(self, user: User) -> User:
        """Render sidebar for authenticated user"""
        st.sidebar.markdown("### 👤 Account")
        st.sidebar.write(f"**{user.get_display_name()}**")
        st.sidebar.write(f"📧 {user.email}")
        
        # AI services status
        ai_services = user.get_ai_enabled_services()
        if ai_services:
            st.sidebar.success(f"🤖 AI: {', '.join(ai_services)}")
        else:
            st.sidebar.info("🤖 AI: Not configured")
        
        # Quick actions
        if st.sidebar.button("⚙️ Settings"):
            st.switch_page("settings")
        
        if st.sidebar.button("🚪 Logout"):
            self.logout()
            st.rerun()
        
        return user
    
    def _render_login_sidebar(self) -> Optional[User]:
        """Render sidebar login form"""
        st.sidebar.markdown("### 🔑 Login")
        
        with st.sidebar.form("quick_login"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.form_submit_button("Login"):
                    user = self._attempt_login(email, password)
                    if user:
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
            
            with col2:
                if st.form_submit_button("Register"):
                    st.switch_page("login")
        
        return None
    
    def _render_login_form(self) -> Optional[User]:
        """Render main login form"""
        st.markdown("### 🔑 Sign In")
        
        with st.form("login_form"):
            email = st.text_input(
                "📧 Email Address",
                placeholder="Enter your email address"
            )
            
            password = st.text_input(
                "🔒 Password",
                type="password",
                placeholder="Enter your password"
            )
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                login_clicked = st.form_submit_button("🔑 Sign In", type="primary")
            
            with col2:
                forgot_password = st.form_submit_button("❓ Forgot Password")
            
            if login_clicked:
                if not email or not password:
                    st.error("Please enter both email and password.")
                    return None
                
                user = self._attempt_login(email, password)
                if user:
                    st.success(f"✅ Welcome back, {user.get_display_name()}!")
                    st.balloons()
                    # Small delay to show success message
                    import time
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Invalid email or password. Please try again.")
            
            if forgot_password:
                st.info("Password reset functionality coming soon!")
        
        return None
    
    def _render_registration_form(self) -> Optional[User]:
        """Render user registration form"""
        st.markdown("### 📝 Create Your Account")
        
        with st.form("registration_form"):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                first_name = st.text_input("First Name")
                email = st.text_input("📧 Email Address", placeholder="your.email@example.com")
                password = st.text_input("🔒 Password", type="password")
            
            with col2:
                last_name = st.text_input("Last Name")
                username = st.text_input("Username (optional)", placeholder="Choose a username")
                confirm_password = st.text_input("🔒 Confirm Password", type="password")
            
            # Terms and conditions
            agree_terms = st.checkbox("I agree to the Terms of Service and Privacy Policy")
            
            # Email notifications
            email_notifications = st.checkbox("Send me recipe recommendations and updates", value=True)
            
            register_clicked = st.form_submit_button("📝 Create Account", type="primary")
            
            if register_clicked:
                # Validation
                if not self._validate_registration_form(
                    email, password, confirm_password, agree_terms
                ):
                    return None
                
                # Attempt registration
                try:
                    user = self.auth.register_user(
                        email=email.strip().lower(),
                        password=password,
                        username=username.strip(),
                        first_name=first_name.strip(),
                        last_name=last_name.strip()
                    )
                    
                    if user:
                        # Create session
                        session = self.auth.create_session(user)
                        if session:
                            st.session_state[self.USER_KEY] = user
                            st.session_state[self.SESSION_KEY] = session
                            
                            st.success(f"🎉 Welcome to Pans Cookbook, {user.get_display_name()}!")
                            st.balloons()
                            import time
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Account created but login failed. Please try signing in.")
                    else:
                        st.error("Registration failed. Email may already be in use.")
                
                except Exception as e:
                    logger.error(f"Registration error: {e}")
                    st.error("Registration failed. Please try again.")
        
        return None
    
    def _render_profile_settings(self, user: User) -> bool:
        """Render profile settings form"""
        st.markdown("#### 👤 Profile Information")
        
        with st.form("profile_settings"):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                first_name = st.text_input("First Name", value=user.first_name)
                email = st.text_input("Email", value=user.email, disabled=True)
            
            with col2:
                last_name = st.text_input("Last Name", value=user.last_name)
                username = st.text_input("Username", value=user.username)
            
            if st.form_submit_button("💾 Save Profile", type="primary"):
                # Update user profile
                success = self._update_user_profile(
                    user.id, first_name, last_name, username
                )
                
                if success:
                    # Update session state
                    user.first_name = first_name
                    user.last_name = last_name
                    user.username = username
                    st.session_state[self.USER_KEY] = user
                    
                    st.success("✅ Profile updated successfully!")
                    return True
                else:
                    st.error("❌ Failed to update profile.")
        
        return False
    
    def _render_preference_settings(self, user: User) -> bool:
        """Render user preference settings form"""
        st.markdown("#### 🍽️ Recipe Preferences")
        
        with st.form("preference_settings"):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # Units preference
                preferred_units = st.selectbox(
                    "Measurement Units",
                    options=["imperial", "metric"],
                    index=0 if user.preferences.preferred_units == "imperial" else 1
                )
                
                # Default servings
                default_servings = st.slider(
                    "Default Recipe Servings",
                    min_value=1,
                    max_value=12,
                    value=user.preferences.default_servings
                )
                
                # Max cook time
                max_cook_time = st.number_input(
                    "Max Cook Time (minutes, 0 = no limit)",
                    min_value=0,
                    max_value=480,
                    value=user.preferences.max_cook_time_minutes or 0
                )
            
            with col2:
                # Dietary restrictions
                dietary_restrictions = st.multiselect(
                    "Dietary Restrictions",
                    options=[
                        "vegetarian", "vegan", "gluten-free", "dairy-free", "nut-free",
                        "low-carb", "keto", "paleo", "high-protein", "low-sodium"
                    ],
                    default=user.preferences.dietary_restrictions
                )
                
                # Preferred cuisines
                preferred_cuisines = st.multiselect(
                    "Preferred Cuisines",
                    options=[
                        "American", "Italian", "Mexican", "Chinese", "Indian", "French",
                        "Thai", "Japanese", "Mediterranean", "Greek", "Korean"
                    ],
                    default=user.preferences.preferred_cuisines
                )
            
            # Additional preferences
            hide_complex = st.checkbox(
                "Hide complex recipes (hard difficulty)",
                value=user.preferences.hide_complex_recipes
            )
            
            email_notifications = st.checkbox(
                "Email notifications",
                value=user.preferences.email_notifications
            )
            
            if st.form_submit_button("💾 Save Preferences", type="primary"):
                # Create updated preferences
                new_preferences = UserPreferences(
                    preferred_units=preferred_units,
                    dietary_restrictions=dietary_restrictions,
                    preferred_cuisines=preferred_cuisines,
                    default_servings=default_servings,
                    hide_complex_recipes=hide_complex,
                    max_cook_time_minutes=max_cook_time if max_cook_time > 0 else None,
                    email_notifications=email_notifications
                )
                
                # Save preferences
                success = self._update_user_preferences(user.id, new_preferences)
                
                if success:
                    user.preferences = new_preferences
                    st.session_state[self.USER_KEY] = user
                    st.success("✅ Preferences saved successfully!")
                    return True
                else:
                    st.error("❌ Failed to save preferences.")
        
        return False
    
    def _render_api_key_settings(self, user: User) -> bool:
        """Render API key configuration form"""
        st.markdown("#### 🤖 AI Service Configuration")
        st.markdown("*Configure API keys for AI-powered recipe features (optional)*")
        
        settings_saved = False
        
        for service_id, service_info in self.AI_SERVICES.items():
            with st.expander(f"{service_info['name']}", expanded=False):
                st.markdown(f"**{service_info['description']}**")
                st.info(service_info['help'])
                
                # Check if user has this API key
                has_key = user.has_api_key(service_id)
                
                if has_key:
                    st.success("✅ API key configured")
                    
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button(f"🔄 Update {service_info['name']} Key", key=f"update_{service_id}"):
                            st.session_state[f'show_update_{service_id}'] = True
                    
                    with col2:
                        if st.button(f"🗑️ Remove Key", key=f"remove_{service_id}"):
                            if self._remove_api_key(user, service_id):
                                st.success("API key removed")
                                st.rerun()
                else:
                    st.warning("❌ No API key configured")
                    st.session_state[f'show_update_{service_id}'] = True
                
                # Show API key input form
                if st.session_state.get(f'show_update_{service_id}', False):
                    with st.form(f"api_key_form_{service_id}"):
                        api_key = st.text_input(
                            f"{service_info['name']} API Key",
                            type="password",
                            placeholder="Enter your API key"
                        )
                        
                        password_for_encryption = st.text_input(
                            "Your Account Password (for encryption)",
                            type="password",
                            help="We encrypt your API keys using your account password"
                        )
                        
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            if st.form_submit_button("💾 Save API Key", type="primary"):
                                if api_key and password_for_encryption:
                                    success = self._save_api_key(
                                        user, service_id, api_key, password_for_encryption
                                    )
                                    
                                    if success:
                                        st.success("✅ API key saved successfully!")
                                        st.session_state[f'show_update_{service_id}'] = False
                                        settings_saved = True
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to save API key. Check your password.")
                                else:
                                    st.error("Please enter both API key and password.")
                        
                        with col2:
                            if st.form_submit_button("❌ Cancel"):
                                st.session_state[f'show_update_{service_id}'] = False
                                st.rerun()
        
        return settings_saved
    
    def _render_security_settings(self, user: User) -> bool:
        """Render security settings form"""
        st.markdown("#### 🔒 Security Settings")
        
        # Password change form
        with st.expander("🔑 Change Password"):
            with st.form("change_password"):
                current_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm New Password", type="password")
                
                if st.form_submit_button("🔄 Change Password", type="primary"):
                    if not all([current_password, new_password, confirm_password]):
                        st.error("All fields are required.")
                    elif new_password != confirm_password:
                        st.error("New passwords don't match.")
                    elif len(new_password) < 8:
                        st.error("Password must be at least 8 characters long.")
                    else:
                        success = self._change_password(user, current_password, new_password)
                        if success:
                            st.success("✅ Password changed successfully!")
                            return True
                        else:
                            st.error("❌ Current password is incorrect.")
        
        # Account activity
        st.markdown("#### 📊 Account Activity")
        st.write(f"**Account created:** {user.created_at.strftime('%B %d, %Y')}")
        st.write(f"**Last login:** {user.last_login.strftime('%B %d, %Y at %I:%M %p')}")
        st.write(f"**Total logins:** {user.login_count}")
        
        # Danger zone
        with st.expander("⚠️ Danger Zone", expanded=False):
            st.warning("**Warning:** These actions cannot be undone.")
            
            if st.button("🗑️ Delete Account", type="secondary"):
                st.error("Account deletion feature coming soon.")
        
        return False
    
    def _attempt_login(self, email: str, password: str) -> Optional[User]:
        """Attempt to authenticate user"""
        try:
            user = self.auth.authenticate_user(email.strip().lower(), password)
            if user:
                # Create session
                session = self.auth.create_session(user)
                if session:
                    st.session_state[self.USER_KEY] = user
                    st.session_state[self.SESSION_KEY] = session
                    logger.info(f"User logged in: {user.email}")
                    return user
            return None
        except Exception as e:
            logger.error(f"Login error: {e}")
            return None
    
    def _validate_registration_form(self, email: str, password: str, 
                                  confirm_password: str, agree_terms: bool) -> bool:
        """Validate registration form data"""
        if not email or not password:
            st.error("Email and password are required.")
            return False
        
        if not self._is_valid_email(email):
            st.error("Please enter a valid email address.")
            return False
        
        if len(password) < 8:
            st.error("Password must be at least 8 characters long.")
            return False
        
        if password != confirm_password:
            st.error("Passwords don't match.")
            return False
        
        if not agree_terms:
            st.error("You must agree to the Terms of Service.")
            return False
        
        return True
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _update_user_profile(self, user_id: int, first_name: str, 
                           last_name: str, username: str) -> bool:
        """Update user profile in database"""
        try:
            with self.auth.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET
                        first_name = ?, last_name = ?, username = ?
                    WHERE id = ?
                """, (first_name, last_name, username, user_id))
                
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Profile update error: {e}")
            return False
    
    def _update_user_preferences(self, user_id: int, preferences: UserPreferences) -> bool:
        """Update user preferences in database"""
        try:
            with self.auth.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET preferences = ? WHERE id = ?
                """, (preferences.to_json(), user_id))
                
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Preferences update error: {e}")
            return False
    
    def _save_api_key(self, user: User, service: str, api_key: str, password: str) -> bool:
        """Save encrypted API key for user"""
        try:
            # First verify the password
            if not self.auth.verify_password(password, user.password_hash):
                return False
            
            # Store encrypted API key
            return self.auth.store_user_api_key(user.id, service, api_key, password)
        except Exception as e:
            logger.error(f"API key save error: {e}")
            return False
    
    def _remove_api_key(self, user: User, service: str) -> bool:
        """Remove API key for service"""
        try:
            with self.auth.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current API keys
                cursor.execute("SELECT api_keys FROM users WHERE id = ?", (user.id,))
                row = cursor.fetchone()
                
                if row and row['api_keys']:
                    import json
                    api_keys = json.loads(row['api_keys'])
                    api_keys.pop(service, None)
                    
                    cursor.execute("""
                        UPDATE users SET api_keys = ? WHERE id = ?
                    """, (json.dumps(api_keys), user.id))
                    
                    conn.commit()
                    
                    # Update user object
                    user.api_keys.pop(service, None)
                    st.session_state[self.USER_KEY] = user
                    
                    return True
            
            return False
        except Exception as e:
            logger.error(f"API key removal error: {e}")
            return False
    
    def _change_password(self, user: User, current_password: str, new_password: str) -> bool:
        """Change user password"""
        try:
            # Verify current password
            if not self.auth.verify_password(current_password, user.password_hash):
                return False
            
            # Hash new password
            new_hash = self.auth.hash_password(new_password)
            
            # Update in database
            with self.auth.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET password_hash = ? WHERE id = ?
                """, (new_hash, user.id))
                
                conn.commit()
                return cursor.rowcount > 0
        
        except Exception as e:
            logger.error(f"Password change error: {e}")
            return False
    
    def _inject_custom_css(self):
        """Inject custom CSS styling"""
        st.markdown("""
        <style>
            .auth-container {
                max-width: 600px;
                margin: 0 auto;
                padding: 2rem;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                background-color: white;
            }
            .auth-header {
                text-align: center;
                margin-bottom: 2rem;
            }
            .api-key-status {
                padding: 0.5rem;
                border-radius: 6px;
                margin: 0.5rem 0;
                text-align: center;
                font-weight: bold;
            }
            .api-key-configured {
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .api-key-missing {
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .settings-section {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 1.5rem;
                margin: 1rem 0;
                background-color: #f8f9fa;
            }
        </style>
        """, unsafe_allow_html=True)


def create_auth_interface(auth_service: Optional[AuthService] = None) -> AuthenticationInterface:
    """Factory function to create authentication interface"""
    return AuthenticationInterface(auth_service)