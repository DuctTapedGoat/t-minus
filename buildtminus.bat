@echo off
setlocal

echo [BUILD] Checking for Virtual Environment...
if not exist "venv\Scripts\python.exe" (
    echo [BUILD] Creating Virtual Environment...
    python -m venv venv
    echo [BUILD] Installing dependencies...
    .\venv\Scripts\pip install pygame pyinstaller
)

echo [BUILD] Compiling T-Minus.py to Executable...
.\venv\Scripts\python.exe -m PyInstaller --onefile --noconsole --name T-Minus t-minus.py

if exist "dist\T-Minus.exe" (
    echo [BUILD] Convering EXE to SCR (Screensaver)...
    if exist "dist\T-Minus.scr" del "dist\T-Minus.scr"
    ren "dist\T-Minus.exe" T-Minus.scr
    echo.
    echo [SUCCESS] Build complete! 
    echo [SUCCESS] Your optimized screensaver is at: dist\T-Minus.scr
) else (
    echo [ERROR] Build failed! Check the output above.
)

pause
