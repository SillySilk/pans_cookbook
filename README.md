# 🍳 Pans Cookbook

A recipe finder and manager with web scraping capabilities, built using traditional HTML parsing with manual validation workflows.

## Features

- **Traditional Web Scraping**: Uses BeautifulSoup for reliable HTML parsing without AI dependencies
- **Manual Validation Forms**: Review and correct scraped recipe data before saving
- **Multi-User Support**: SQLite database with secure user authentication and encrypted API key storage
- **Intelligent Ingredient Matching**: Suggests database matches when parsing ingredients
- **Optional AI Integration**: Support for OpenAI/Anthropic APIs using user-provided keys
- **Streamlit Interface**: Clean, responsive web UI for all operations

## Architecture

Built using **spec-driven development** methodology with structured phases:
- Requirements → Design → Tasks → Implementation
- Code reuse prioritization and systematic validation
- Comprehensive testing and documentation

### Components

- **Database Service**: Multi-user recipe and ingredient management
- **Scraping Service**: Robots.txt compliant web scraping with rate limiting
- **Parsing Service**: Recipe data normalization and validation
- **Authentication Service**: User management with encrypted credential storage
- **Validation UI**: Interactive forms for manual data correction

## Getting Started

### Prerequisites

- Python 3.8+
- Required packages: `streamlit`, `beautifulsoup4`, `requests`, `bcrypt`, `cryptography`

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/SillySilk/pans_cookbook.git
   cd pans_cookbook
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run tests to verify setup:
   ```bash
   # Windows
   test_runner.bat
   
   # Linux/Mac
   python test_database.py && python test_scraper.py && python test_parsing.py
   ```

4. Launch the application:
   ```bash
   streamlit run main.py
   ```

## Usage

### Recipe Scraping Workflow

1. **Scrape Recipe**: Provide a recipe URL
2. **Auto-Parse**: System extracts ingredients, instructions, times
3. **Manual Validation**: Review and correct parsed data using interactive forms
4. **Ingredient Matching**: Assign ingredients to database entries or create new ones
5. **Save Recipe**: Validated recipe is saved to your personal collection

### Multi-User Features

- Secure user registration and authentication
- Personal recipe collections
- Encrypted API key storage for AI features
- Shared ingredient database with personal customizations

## Development

### Project Structure

```
pans_cookbook/
├── models/           # Data models and schemas
├── services/         # Business logic services
├── ui/              # Streamlit interface components
├── utils/           # Configuration and utilities
├── .spec-workflow/  # Spec-driven development artifacts
├── tests/           # Test files
└── main.py          # Application entry point
```

### Testing

Run the comprehensive test suite:

```bash
# All tests
test_runner.bat

# Individual components
python test_database.py    # Database operations
python test_scraper.py     # Web scraping functionality  
python test_parsing.py     # Recipe parsing and validation
python test_auth.py        # Authentication system
```

### Spec-Driven Development

This project follows a structured spec workflow:
- **Requirements**: User stories and acceptance criteria
- **Design**: Technical architecture leveraging existing code
- **Tasks**: Atomic implementation steps with requirement traceability
- **Implementation**: Systematic task execution with validation

View the complete specifications in `.spec-workflow/specs/pans-cookbook/`.

## Contributing

1. Follow the existing code patterns and conventions
2. Prioritize code reuse over creating new components
3. Include comprehensive tests for new functionality
4. Update documentation for user-facing changes
5. Use the spec workflow for significant features

## Security

- User passwords are hashed with bcrypt
- API keys are encrypted using Fernet symmetric encryption
- No hardcoded secrets or credentials
- Robots.txt compliance for ethical web scraping
- Rate limiting and respectful scraping practices

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built upon patterns from the Herbalism app
- Utilizes Streamlit for rapid UI development
- Follows Python best practices and security guidelines
- Implements ethical web scraping standards

---

**Status**: Active Development  
**Current Version**: v0.6.0 - Manual Validation Forms Complete