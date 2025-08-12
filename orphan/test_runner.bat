@echo off
echo ====================================
echo    Pans Cookbook - Test Runner
echo ====================================
echo.

echo [1/6] Testing Database Service...
python test_database.py
if errorlevel 1 (
    echo [FAIL] Database tests failed
    pause
    exit /b 1
)
echo.

echo [2/6] Testing Scraping Service...
python test_scraper.py
if errorlevel 1 (
    echo [FAIL] Scraping tests failed
    pause
    exit /b 1
)
echo.

echo [3/6] Testing Parsing Service...
python test_parsing.py
if errorlevel 1 (
    echo [FAIL] Parsing tests failed
    pause
    exit /b 1
)
echo.

echo [4/6] Testing AI Service...
python test_ai_service.py
if errorlevel 1 (
    echo [FAIL] AI service tests failed
    pause
    exit /b 1
)
echo.

echo [5/6] Testing AI Features UI...
python test_ai_features_ui.py
if errorlevel 1 (
    echo [FAIL] AI Features UI tests failed
    pause
    exit /b 1
)
echo.

echo [6/6] Testing Authentication Service...
python test_auth.py
if errorlevel 1 (
    echo [FAIL] Authentication tests failed
    pause
    exit /b 1
)
echo.

echo ====================================
echo    ALL TESTS PASSED SUCCESSFULLY!
echo ====================================
echo.
echo You can now run the main application with:
echo   streamlit run main.py
echo.
echo For enhanced AI features, start LM Studio first then run:
echo   streamlit run main.py
echo.
pause