# Implementation Plan

## Task Overview

The implementation follows a layered approach, starting with core service infrastructure, then building data models, AI parsing capabilities, database integration, and finally the enhanced user interface. Each task focuses on creating atomic, testable components with comprehensive error handling that ensures no failures are masked by fallbacks.

## Tasks

- [x] 1. Create data models and result classes in src/scraper/models.py
  - File: src/scraper/models.py
  - Define ParsedRecipe, ParsedHerb, ScrapingResult, ValidationResult dataclasses
  - Include all required fields matching database schema
  - Add comprehensive error tracking fields
  - _Leverage: database.py dataclasses for field structure reference_
  - _Requirements: 1.1, 2.2, 3.1_

- [x] 2. Create validation service in src/scraper/validation_service.py
  - File: src/scraper/validation_service.py
  - Implement ValidationService class with safety checking methods
  - Add validate_recipe_data and validate_herb_safety functions
  - Include dangerous content detection with explicit error reporting
  - Never fail silently - all validation issues must be reported
  - _Leverage: existing database.py field validation patterns_
  - _Requirements: 5.2, 5.3, 2.3_

- [x] 3. Create database service in src/scraper/database_service.py
  - File: src/scraper/database_service.py
  - Implement DatabaseService class with transaction-safe operations
  - Add save_recipe_with_herbs, find_similar_herbs, create_herb_if_not_exists methods
  - Include comprehensive error logging and transaction rollback
  - Expose all SQL errors with detailed context for debugging
  - _Leverage: database.py connection management and model classes_
  - _Requirements: 3.1, 3.2, 3.3, 7.1, 7.2_

- [x] 4. Create AI parsing service in src/scraper/ai_parsing_service.py
  - File: src/scraper/ai_parsing_service.py
  - Implement AIParsingService class with enhanced LM Studio integration
  - Add parse_recipe and extract_herb_info methods with detailed error handling
  - Include structured prompts for recipe and herb extraction
  - Log all AI failures with complete input/output context
  - _Leverage: existing LM Studio client setup from scraper_ui.py_
  - _Requirements: 4.1, 4.2, 4.3, 1.1, 2.2_

- [x] 5. Create orchestration service in src/scraper/scraper_service.py
  - File: src/scraper/scraper_service.py
  - Implement ScraperService class to coordinate all operations
  - Add scrape_and_save_recipe and parse_and_save_recipe methods
  - Include comprehensive error aggregation and reporting
  - Ensure all component errors are captured and exposed
  - _Leverage: validation_service.py, database_service.py, ai_parsing_service.py_
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 6. Create logging and error handling utilities in src/scraper/logger.py
  - File: src/scraper/logger.py
  - Implement ScraperLogger class with structured error logging
  - Add methods for AI errors, database errors, validation errors
  - Include debug file output for detailed error analysis
  - Ensure no errors are hidden - all logged with full context
  - _Leverage: Python logging module best practices_
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 7. Update scraper_ui.py to use new service architecture
  - File: scraper_ui.py (modify existing)
  - Replace direct parsing logic with ScraperService calls
  - Add comprehensive error display with technical details
  - Include progress indicators and status updates
  - Show all errors and warnings with actionable guidance
  - _Leverage: existing Streamlit UI patterns and session state management_
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 8. Add herb discovery and matching interface to scraper_ui.py
  - File: scraper_ui.py (continue modification)
  - Implement new herb discovery workflow with user confirmation
  - Add herb similarity matching with conflict resolution UI
  - Include herb information review and approval interface
  - Display all herb extraction details for user verification
  - _Leverage: existing multiselect patterns from main app.py_
  - _Requirements: 2.1, 2.2, 7.1, 7.3, 6.2_

- [x] 9. Integrate with SQLite database instead of CSV workflow
  - File: scraper_ui.py (continue modification)
  - Remove all CSV file operations and replace with database calls
  - Update herb loading to use load_herbs_from_db function
  - Add database connection error handling with clear user feedback
  - Ensure transaction consistency across recipe and herb operations
  - _Leverage: database.py load_herbs_from_db and migration functions_
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 10. Add comprehensive error display and debugging interface
  - File: scraper_ui.py (continue modification)
  - Create detailed error reporting UI with expandable sections
  - Add debug information display for technical troubleshooting
  - Include raw AI response viewer for parsing failures
  - Implement retry mechanisms with error context preservation
  - _Leverage: existing Streamlit expander and error display patterns_
  - _Requirements: 5.1, 5.4, 6.3, 6.4_

- [ ] 11. Create unit tests for validation service
  - File: tests/test_validation_service.py
  - Write comprehensive tests for ValidationService methods
  - Test safety validation rules and dangerous content detection
  - Verify error reporting accuracy and completeness
  - Include edge cases and malformed input handling
  - _Leverage: existing test patterns and pytest framework_
  - _Requirements: 5.2, 5.3_

- [ ] 12. Create unit tests for database service
  - File: tests/test_database_service.py
  - Write tests for DatabaseService with transaction rollback verification
  - Test herb matching and conflict resolution logic
  - Mock database operations and test error handling paths
  - Verify data consistency under failure conditions
  - _Leverage: existing database connection patterns and test utilities_
  - _Requirements: 3.1, 3.2, 3.3, 7.1, 7.2_

- [ ] 13. Create unit tests for AI parsing service
  - File: tests/test_ai_parsing_service.py
  - Write tests for AIParsingService with mocked LM Studio responses
  - Test JSON parsing and repair functionality
  - Verify error handling for malformed AI responses
  - Include prompt validation and response format verification
  - _Leverage: existing OpenAI client patterns and response mocking_
  - _Requirements: 4.1, 4.2, 4.3, 1.1, 2.2_

- [ ] 14. Create integration tests for complete scraping workflow
  - File: tests/test_scraper_integration.py
  - Write end-to-end tests for complete URL to database workflow
  - Test error propagation through all service layers
  - Verify database consistency under various failure scenarios
  - Include network failure simulation and recovery testing
  - _Leverage: existing database setup and teardown utilities_
  - _Requirements: All requirements integrated testing_

- [ ] 15. Add enhanced error logging and monitoring
  - File: src/scraper/logger.py (enhance existing)
  - Add structured logging with error categorization
  - Implement error rate monitoring and alerting capabilities
  - Include performance metrics and operation timing
  - Create debug log rotation and cleanup mechanisms
  - _Leverage: Python logging module advanced features_
  - _Requirements: 5.1, 5.4_

- [ ] 16. Final integration and user acceptance testing
  - Files: Multiple files for final integration
  - Test complete user workflows with real recipe URLs
  - Verify all error scenarios provide clear user guidance
  - Validate herb discovery and database integration
  - Ensure no errors are masked by fallback behaviors
  - _Leverage: Complete system integration_
  - _Requirements: All requirements final validation_