@echo off
setlocal

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

set "VENV_DIR=.venv"
set "SYSTEM_PY=python"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "RUN_PY=%VENV_PY%"
set "LOCAL_TMP=%PROJECT_DIR%.runtime_tmp"

if not exist "%LOCAL_TMP%" mkdir "%LOCAL_TMP%" >nul 2>&1
set "TEMP=%LOCAL_TMP%"
set "TMP=%LOCAL_TMP%"

if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found in project root.
    pause
    exit /b 1
)

%SYSTEM_PY% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not available in PATH.
    pause
    exit /b 1
)

if not exist "%VENV_PY%" (
    echo [INFO] Creating virtual environment...
    %SYSTEM_PY% -m venv "%VENV_DIR%" >nul 2>&1
)

if not exist "%VENV_PY%" (
    echo [WARN] Standard venv creation failed. Retrying with --without-pip...
    if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%" >nul 2>&1
    %SYSTEM_PY% -m venv --without-pip "%VENV_DIR%" >nul 2>&1
)

if not exist "%VENV_PY%" (
    echo [WARN] Failed to create virtual environment. Falling back to system Python.
    set "RUN_PY=%SYSTEM_PY%"
)

if /I "%RUN_PY%"=="%VENV_PY%" (
    "%VENV_PY%" -m pip --version >nul 2>&1
    if errorlevel 1 (
        echo [INFO] Bootstrapping pip into virtual environment...
        %SYSTEM_PY% -m pip --version >nul 2>&1
        if errorlevel 1 (
            echo [WARN] System pip is unavailable. Falling back to system Python.
            set "RUN_PY=%SYSTEM_PY%"
        ) else (
            %SYSTEM_PY% -m pip --python "%VENV_PY%" install --upgrade pip setuptools wheel >nul 2>&1
            if errorlevel 1 (
                echo [WARN] Failed to bootstrap pip into virtual environment. Falling back to system Python.
                set "RUN_PY=%SYSTEM_PY%"
            )
        )
    )
)

%RUN_PY% -c "import aiohttp, jinja2" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing dependencies with: python -m pip install -r requirements.txt
    %RUN_PY% -m pip --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] pip is unavailable in current Python interpreter.
        pause
        exit /b 1
    )

    %RUN_PY% -m pip install --upgrade pip setuptools wheel
    if errorlevel 1 (
        echo [WARN] pip/setuptools/wheel upgrade failed. Continuing...
    )

    %RUN_PY% -m pip install --prefer-binary --only-binary=aiohttp aiohttp==3.13.5
    if errorlevel 1 (
        echo [ERROR] Failed to install binary wheel for aiohttp.
        echo [ERROR] Please use Python 3.10-3.14 ^(64-bit^) and update pip, then retry.
        pause
        exit /b 1
    )

    %RUN_PY% -m pip install --prefer-binary -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install requirements.
        pause
        exit /b 1
    )
)

%RUN_PY% -c "import aiohttp, jinja2" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Dependency check failed after installation.
    pause
    exit /b 1
)

echo [INFO] Starting server on http://127.0.0.1:8000
echo [INFO] Runtime Python: %RUN_PY%
%RUN_PY% -m app.main

endlocal
