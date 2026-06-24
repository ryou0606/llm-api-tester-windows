@echo off
echo ========================================
echo   LLM API Tester - Build Script
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
pip install -r requirements.txt pyinstaller -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo [2/4] Cleaning old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [3/4] Building with PyInstaller...
pyinstaller llm_tester.spec --noconfirm --clean
if errorlevel 1 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo [4/4] Copying static files...
if not exist "dist\LLM-API-Tester\static" mkdir "dist\LLM-API-Tester\static"
xcopy /E /Y /Q "static\*" "dist\LLM-API-Tester\static\" >nul 2>&1
if not exist "dist\LLM-API-Tester\data" mkdir "dist\LLM-API-Tester\data"

echo.
echo ========================================
echo   Build complete!
echo ========================================
echo.
echo   Output: dist\LLM-API-Tester\
echo   Run:    dist\LLM-API-Tester\LLM-API-Tester.exe
echo.
pause
