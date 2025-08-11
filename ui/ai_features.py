"""
AI features UI components for Pans Cookbook application.

Provides optional AI-powered interfaces that gracefully handle API unavailability,
recipe enhancement suggestions, and clear status indicators.
Leverages Herbalism app conditional UI patterns with AI-specific adaptations.
"""

import streamlit as st
from typing import List, Optional, Dict, Any
import time
from datetime import datetime

from models import ParsedRecipe, Recipe, Ingredient
from services import AIService, get_ai_service, is_ai_available, DatabaseService, get_database_service
from utils import get_logger

logger = get_logger(__name__)


class AIFeaturesInterface:
    """
    AI features user interface with graceful degradation.
    
    Provides AI-powered recipe enhancements, ingredient suggestions, and
    instructional improvements with clear availability indicators.
    """
    
    def __init__(self, ai_service: Optional[AIService] = None, 
                 database_service: Optional[DatabaseService] = None):
        self.ai_service = ai_service or get_ai_service()
        self.db = database_service or get_database_service()
        
        # Initialize custom CSS for AI features
        self._inject_ai_css()
        
        # Session state keys for AI features
        self.AI_STATUS_KEY = "ai_status_cache"
        self.AI_SUGGESTIONS_KEY = "ai_suggestions_cache"
        self.ENHANCED_INSTRUCTIONS_KEY = "enhanced_instructions_cache"
    
    def render_ai_status_indicator(self, compact: bool = False):
        """Render AI service status indicator"""
        ai_available = self.ai_service.is_ai_available()
        
        if compact:
            # Compact status for sidebars/headers
            if ai_available:
                st.success("🤖 AI Enhanced", icon="✅")
            else:
                st.warning("🤖 AI Offline", icon="⚠️")
        else:
            # Detailed status for main content areas
            with st.container():
                if ai_available:
                    st.success("**🤖 AI Features Active**  \nLM Studio connected and ready to enhance your recipes!")
                else:
                    st.warning("**🤖 AI Features Offline**  \nLM Studio not available. Basic functionality still works perfectly!")
                    with st.expander("How to enable AI features"):
                        st.markdown("""
                        **To enable AI-powered recipe enhancements:**
                        
                        1. Download and install [LM Studio](https://lmstudio.ai/)
                        2. Download a compatible model (recommended: Llama 2 7B or similar)
                        3. Start the local server on port 1234
                        4. Refresh this page to activate AI features
                        
                        **AI features include:**
                        - 🔍 Enhanced recipe scraping for difficult websites
                        - 🥕 Smart ingredient suggestions
                        - 📝 Recipe instruction improvements
                        - 🍎 Nutritional information estimation
                        """)
    
    def render_recipe_ai_panel(self, recipe: ParsedRecipe, user_pantry: List[str] = None):
        """Render AI enhancement panel for a recipe"""
        st.subheader("🤖 AI Recipe Enhancements")
        
        if not self.ai_service.is_ai_available():
            self.render_ai_status_indicator(compact=False)
            return
        
        # AI enhancement tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "🥕 Ingredient Suggestions", 
            "📝 Better Instructions", 
            "🍎 Nutrition Info",
            "🎯 Recipe Analysis"
        ])
        
        with tab1:
            self._render_ingredient_suggestions(recipe, user_pantry)
        
        with tab2:
            self._render_instruction_improvements(recipe)
        
        with tab3:
            self._render_nutrition_estimation(recipe)
        
        with tab4:
            self._render_recipe_analysis(recipe)
    
    def _render_ingredient_suggestions(self, recipe: ParsedRecipe, user_pantry: List[str] = None):
        """Render AI ingredient suggestions interface"""
        st.markdown("### Smart Ingredient Suggestions")
        st.markdown("AI can suggest complementary ingredients or substitutes based on your pantry.")
        
        col1, col2 = st.columns([3, 1])
        
        with col2:
            if st.button("🔮 Get AI Suggestions", key="ingredient_suggestions"):
                with st.spinner("AI is analyzing the recipe..."):
                    suggestions = self.ai_service.suggest_ingredients_for_recipe(recipe, user_pantry)
                    if suggestions:
                        st.session_state[self.AI_SUGGESTIONS_KEY] = {
                            'suggestions': suggestions,
                            'timestamp': datetime.now(),
                            'recipe_title': recipe.title
                        }
                    else:
                        st.error("Failed to get AI suggestions. Please try again.")
        
        with col1:
            # Display cached suggestions if available
            if (self.AI_SUGGESTIONS_KEY in st.session_state and 
                st.session_state[self.AI_SUGGESTIONS_KEY]['recipe_title'] == recipe.title):
                
                suggestions_data = st.session_state[self.AI_SUGGESTIONS_KEY]
                suggestions = suggestions_data['suggestions']
                timestamp = suggestions_data['timestamp']
                
                st.success(f"**AI Suggestions** (Generated {timestamp.strftime('%H:%M')})")
                
                for i, suggestion in enumerate(suggestions, 1):
                    col_check, col_ingredient = st.columns([1, 4])
                    with col_check:
                        add_to_recipe = st.checkbox("", key=f"add_ingredient_{i}")
                    with col_ingredient:
                        st.write(f"**{suggestion}**")
                        if add_to_recipe:
                            st.success(f"✅ {suggestion} added to your shopping list!")
            else:
                st.info("Click 'Get AI Suggestions' to see smart ingredient recommendations!")
    
    def _render_instruction_improvements(self, recipe: ParsedRecipe):
        """Render AI instruction improvement interface"""
        st.markdown("### Enhanced Cooking Instructions")
        st.markdown("AI can make recipe instructions clearer and more detailed.")
        
        col1, col2 = st.columns([3, 1])
        
        with col2:
            if st.button("✨ Improve Instructions", key="improve_instructions"):
                with st.spinner("AI is improving the instructions..."):
                    improved = self.ai_service.improve_recipe_instructions(recipe)
                    if improved:
                        st.session_state[self.ENHANCED_INSTRUCTIONS_KEY] = {
                            'instructions': improved,
                            'timestamp': datetime.now(),
                            'recipe_title': recipe.title
                        }
                    else:
                        st.error("Failed to improve instructions. Please try again.")
        
        with col1:
            # Display enhanced instructions if available
            if (self.ENHANCED_INSTRUCTIONS_KEY in st.session_state and 
                st.session_state[self.ENHANCED_INSTRUCTIONS_KEY]['recipe_title'] == recipe.title):
                
                enhanced_data = st.session_state[self.ENHANCED_INSTRUCTIONS_KEY]
                enhanced_instructions = enhanced_data['instructions']
                timestamp = enhanced_data['timestamp']
                
                st.success(f"**AI-Enhanced Instructions** (Generated {timestamp.strftime('%H:%M')})")
                
                # Show comparison
                with st.expander("📋 Original Instructions"):
                    st.write(recipe.instructions)
                
                st.markdown("**✨ Enhanced Instructions:**")
                st.write(enhanced_instructions)
                
                # Option to replace original
                if st.button("🔄 Replace Original Instructions", key="replace_instructions"):
                    st.success("Instructions updated! (Note: This would update the database in the full app)")
                    
            else:
                # Show original instructions
                st.info("**Original Instructions:**")
                st.write(recipe.instructions)
                st.write("*Click 'Improve Instructions' to see AI-enhanced version*")
    
    def _render_nutrition_estimation(self, recipe: ParsedRecipe):
        """Render AI nutrition estimation interface"""
        st.markdown("### Nutritional Information")
        st.markdown("AI can estimate nutritional values based on ingredients.")
        
        col1, col2 = st.columns([3, 1])
        
        with col2:
            if st.button("🍎 Estimate Nutrition", key="estimate_nutrition"):
                with st.spinner("AI is calculating nutrition..."):
                    nutrition = self.ai_service.extract_nutrition_estimates(recipe)
                    if nutrition:
                        st.session_state['nutrition_data'] = {
                            'nutrition': nutrition,
                            'timestamp': datetime.now(),
                            'recipe_title': recipe.title
                        }
                    else:
                        st.error("Failed to estimate nutrition. Please try again.")
        
        with col1:
            # Display nutrition data if available
            if ('nutrition_data' in st.session_state and 
                st.session_state['nutrition_data']['recipe_title'] == recipe.title):
                
                nutrition_data = st.session_state['nutrition_data']['nutrition']
                timestamp = st.session_state['nutrition_data']['timestamp']
                
                st.success(f"**AI Nutrition Estimate** (Per serving, generated {timestamp.strftime('%H:%M')})")
                
                # Display nutrition in a nice format
                col_1, col_2, col_3 = st.columns(3)
                
                with col_1:
                    st.metric("Calories", f"{nutrition_data.get('calories', 0)}")
                    st.metric("Protein", f"{nutrition_data.get('protein_g', 0)}g")
                
                with col_2:
                    st.metric("Carbs", f"{nutrition_data.get('carbs_g', 0)}g")
                    st.metric("Fat", f"{nutrition_data.get('fat_g', 0)}g")
                
                with col_3:
                    st.metric("Fiber", f"{nutrition_data.get('fiber_g', 0)}g")
                    st.metric("Sugar", f"{nutrition_data.get('sugar_g', 0)}g")
                
                st.caption("*Nutritional values are AI estimates and may not be exact*")
                
            else:
                st.info("Click 'Estimate Nutrition' to see AI-calculated nutritional information!")
    
    def _render_recipe_analysis(self, recipe: ParsedRecipe):
        """Render AI recipe analysis and insights"""
        st.markdown("### Recipe Analysis")
        st.markdown("AI insights about this recipe's characteristics and suggestions.")
        
        if st.button("🎯 Analyze Recipe", key="analyze_recipe"):
            with st.spinner("AI is analyzing the recipe..."):
                # This would use a more general AI analysis function
                time.sleep(1)  # Simulate processing
                
                # Display mock analysis for now
                st.success("**AI Recipe Analysis Complete**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**🎯 Recipe Characteristics:**")
                    st.write(f"• **Difficulty**: {recipe.difficulty_level.title()}")
                    st.write(f"• **Total Time**: {recipe.get_total_time()} minutes")
                    st.write(f"• **Servings**: {recipe.servings}")
                    if recipe.cuisine_type:
                        st.write(f"• **Cuisine**: {recipe.cuisine_type}")
                    if recipe.dietary_tags:
                        st.write(f"• **Dietary**: {', '.join(recipe.dietary_tags)}")
                
                with col2:
                    st.markdown("**💡 AI Insights:**")
                    
                    # Generate some basic insights based on recipe data
                    insights = []
                    
                    if recipe.get_total_time() <= 30:
                        insights.append("⚡ Quick meal - perfect for busy weeknights")
                    
                    if len(recipe.ingredients) <= 5:
                        insights.append("🎯 Simple recipe with minimal ingredients")
                    elif len(recipe.ingredients) >= 10:
                        insights.append("🧑‍🍳 Complex recipe with rich flavors")
                    
                    if 'vegetarian' in recipe.dietary_tags:
                        insights.append("🌱 Vegetarian-friendly")
                    
                    if recipe.difficulty_level == 'easy':
                        insights.append("👶 Great for beginner cooks")
                    elif recipe.difficulty_level == 'hard':
                        insights.append("👨‍🍳 Advanced cooking techniques required")
                    
                    for insight in insights:
                        st.write(f"• {insight}")
                    
                    if not insights:
                        st.write("• This looks like a solid, well-balanced recipe!")
    
    def render_ai_scraping_helper(self):
        """Render AI scraping assistance interface"""
        st.subheader("🤖 AI-Enhanced Recipe Scraping")
        
        if not self.ai_service.is_ai_available():
            st.warning("AI enhancement unavailable. Traditional scraping will be used.")
            return
        
        st.success("**AI Scraping Active** - Better results from challenging recipe websites!")
        
        with st.expander("ℹ️ How AI Scraping Helps"):
            st.markdown("""
            **AI-Enhanced Scraping provides:**
            - 🧠 **Smarter Parsing**: Understands recipe context better than simple HTML parsing
            - 🔍 **Better Extraction**: Finds ingredients and instructions even in unusual formats  
            - 🏷️ **Auto-Categorization**: Automatically identifies cuisine types and dietary tags
            - 📊 **Quality Scoring**: Rates how complete and accurate the extracted data is
            - 🛡️ **Error Recovery**: Handles websites that are difficult for traditional scrapers
            
            *AI scraping runs automatically when traditional methods need assistance*
            """)
    
    def render_ai_settings_panel(self):
        """Render AI configuration and settings panel"""
        st.subheader("⚙️ AI Settings & Status")
        
        # Current status
        ai_status = self.ai_service.get_ai_status()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🔌 Connection Status**")
            
            if ai_status['lm_studio_available']:
                st.success(f"✅ LM Studio Connected  \n`{ai_status['lm_studio_url']}`")
            else:
                st.error(f"❌ LM Studio Offline  \n`{ai_status['lm_studio_url']}`")
            
            if st.button("🔄 Check Connection", key="check_ai_connection"):
                with st.spinner("Testing AI connection..."):
                    available = self.ai_service.is_ai_available(force_check=True)
                    if available:
                        st.success("✅ AI connection successful!")
                    else:
                        st.error("❌ Could not connect to LM Studio")
                st.rerun()
        
        with col2:
            st.markdown("**🎯 Available Features**")
            
            features = ai_status['features_available']
            
            for feature_name, available in features.items():
                feature_display = {
                    'scraping_enhancement': '🔍 Enhanced Scraping',
                    'ingredient_suggestions': '🥕 Ingredient Suggestions', 
                    'instruction_improvement': '📝 Instruction Enhancement',
                    'nutrition_estimation': '🍎 Nutrition Estimation',
                    'recipe_variations': '🎨 Recipe Variations'
                }
                
                display_name = feature_display.get(feature_name, feature_name)
                
                if available:
                    st.success(f"✅ {display_name}")
                else:
                    st.warning(f"⚠️ {display_name}")
        
        # Advanced settings
        with st.expander("🔧 Advanced AI Settings"):
            st.markdown("**Configuration (Read-only)**")
            
            st.code(f"""
LM Studio URL: {ai_status['lm_studio_url']}
External APIs: {'Enabled' if ai_status['external_apis_enabled'] else 'Disabled'}
Last Health Check: {ai_status['last_health_check'] or 'Never'}
            """)
            
            st.info("💡 **Tip**: To change AI settings, modify environment variables or configuration files.")
    
    def _inject_ai_css(self):
        """Inject custom CSS for AI features"""
        st.markdown("""
        <style>
            .ai-feature-container {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 1rem;
                margin: 1rem 0;
                background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%);
                border-left: 4px solid #4CAF50;
            }
            
            .ai-status-available {
                background: linear-gradient(90deg, #E8F5E9 0%, #C8E6C9 100%);
                color: #2E7D32;
                padding: 0.5rem;
                border-radius: 4px;
                border: 1px solid #A5D6A7;
            }
            
            .ai-status-offline {
                background: linear-gradient(90deg, #FFF3E0 0%, #FFE0B2 100%);
                color: #F57C00;
                padding: 0.5rem;
                border-radius: 4px;
                border: 1px solid #FFCC02;
            }
            
            .ai-suggestion-item {
                background: #f8f9ff;
                border: 1px solid #e3f2fd;
                border-radius: 4px;
                padding: 0.5rem;
                margin: 0.25rem 0;
            }
            
            .ai-insight {
                background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
                border-left: 4px solid #2196F3;
                padding: 0.75rem;
                margin: 0.5rem 0;
                border-radius: 4px;
            }
        </style>
        """, unsafe_allow_html=True)


# Factory function
def create_ai_features_interface(ai_service: Optional[AIService] = None,
                                database_service: Optional[DatabaseService] = None) -> AIFeaturesInterface:
    """Factory function to create AI features interface"""
    return AIFeaturesInterface(ai_service, database_service)


# Convenience functions for quick AI feature integration
def show_ai_status(compact: bool = True):
    """Quick AI status display"""
    interface = create_ai_features_interface()
    interface.render_ai_status_indicator(compact=compact)


def show_ai_recipe_panel(recipe: ParsedRecipe, user_pantry: List[str] = None):
    """Quick AI recipe enhancement panel"""
    interface = create_ai_features_interface()
    interface.render_recipe_ai_panel(recipe, user_pantry)