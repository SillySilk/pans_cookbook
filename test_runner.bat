@echo off
echo ====================================
echo    Pans Cookbook - Test Runner
echo ====================================
echo.

echo [1/4] Testing Database Service...
python test_database.py
if errorlevel 1 (
    echo [FAIL] Database tests failed
    pause
    exit /b 1
)
echo.

echo [2/4] Testing Scraping Service...
python test_scraper.py
if errorlevel 1 (
    echo [FAIL] Scraping tests failed
    pause
    exit /b 1
)
echo.

echo [3/4] Testing Parsing Service...
python test_parsing.py
if errorlevel 1 (
    echo [FAIL] Parsing tests failed
    pause
    exit /b 1
)
echo.

echo [4/4] Testing Authentication Service...
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
echo   python main.py
echo.
pause