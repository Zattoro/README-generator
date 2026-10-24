@echo off
echo ========================================
echo  Building AI README Generator .exe
echo ========================================

echo.
echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found in PATH. Install python.org and add to PATH.
    pause
    exit /b 1
)

echo.
echo [2/4] Installing PyInstaller...
pip install pyinstaller >nul 2>&1

echo.
echo [3/4] Building .exe (single file, no console)...
pyinstaller --onefile --windowed --name "AI README Generator" --icon=NONE ^
    --hidden-import=readme_gen ^
    --hidden-import=readme_gen.analyzer ^
    --hidden-import=readme_gen.generator ^
    --hidden-import=readme_gen.clone ^
    --hidden-import=readme_gen.config ^
    --hidden-import=readme_gen.gui ^
    --hidden-import=readme_gen.bootstrap ^
    run_gui.py ^
    --distpath dist ^
    --workpath build ^
    --specpath .

if errorlevel 1 (
    echo.
    echo Error during .exe build
    pause
    exit /b 1
)

echo.
echo [4/4] Done!
echo .exe file is located at: dist\AI README Generator.exe
echo.
echo Run it - no command line needed, everything is automatic.
echo.
pause