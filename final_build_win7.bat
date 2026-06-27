@echo off
setlocal EnableExtensions

rem ================================================================
rem STM32 Git Release Tool - Windows 7 one-click build
rem Required host: Windows 7 SP1 64-bit and Python 3.8.x 64-bit
rem Output: STM32GitReleaseTool-Win7.exe in this project directory
rem ================================================================

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR:~0,-1%"
set "MAIN_FILE=%PROJECT_DIR%\main.py"
set "VERSION_FILE=%PROJECT_DIR%\packaging\windows_version_info.txt"
set "TEMPLATE_DIR=%PROJECT_DIR%\templates"
set "README_FILE=%PROJECT_DIR%\README.md"
set "LICENSE_FILE=%PROJECT_DIR%\LICENSE"
set "VENV_DIR=%PROJECT_DIR%\.win7_build_env"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "BUILD_DIR=%PROJECT_DIR%\win7_build"
set "DIST_DIR=%PROJECT_DIR%\win7_dist"
set "SPEC_DIR=%PROJECT_DIR%\win7_spec"
set "PACKAGE_DIR=%PROJECT_DIR%\win7_release"
set "FINAL_EXE=%PROJECT_DIR%\STM32GitReleaseTool-Win7.exe"
set "BUILT_EXE=%DIST_DIR%\STM32GitReleaseTool-Win7.exe"
set "WHEEL_DIR=%PROJECT_DIR%\win7_wheels"

cd /d "%PROJECT_DIR%"

echo ================================================================
echo   STM32 Git Release Tool - Windows 7 Build
echo ================================================================
echo Project: %PROJECT_DIR%
echo.

echo [1/7] Checking required project files...
if not exist "%MAIN_FILE%" goto missing_main
if not exist "%VERSION_FILE%" goto missing_version
if not exist "%TEMPLATE_DIR%" goto missing_templates
if not exist "%README_FILE%" goto missing_readme
if not exist "%LICENSE_FILE%" goto missing_license
echo [OK] Project files found.
echo.

echo [2/7] Checking system Python...
where python >nul 2>&1
if errorlevel 1 goto missing_python
python --version
python -c "import sys,struct; ok=(sys.version_info[:2]==(3,8) and struct.calcsize('P')*8==64); print('Python architecture:',struct.calcsize('P')*8,'bit'); sys.exit(0 if ok else 1)"
if errorlevel 1 goto wrong_python
echo [OK] Python 3.8 64-bit detected.
echo.

echo [3/7] Creating isolated build environment...
if not exist "%VENV_PYTHON%" (
    python -m venv "%VENV_DIR%"
    if errorlevel 1 goto venv_failed
)
"%VENV_PYTHON%" --version
echo [OK] Build environment ready.
echo.

echo [4/7] Installing fixed Windows 7 build dependencies...
"%VENV_PYTHON%" -m pip install --upgrade pip==24.0 setuptools==69.5.1 wheel==0.43.0
if errorlevel 1 goto pip_tools_failed

if exist "%WHEEL_DIR%" (
    echo Local wheel folder detected: %WHEEL_DIR%
    "%VENV_PYTHON%" -m pip install --no-index --find-links="%WHEEL_DIR%" PyQt5==5.15.2 PyQt5-Qt5==5.15.2 PyQt5-sip==12.13.0 PyInstaller==4.10
) else (
    echo No win7_wheels folder found. Installing from PyPI...
    "%VENV_PYTHON%" -m pip install --only-binary=:all: PyQt5==5.15.2 PyQt5-Qt5==5.15.2 PyQt5-sip==12.13.0
    if errorlevel 1 goto pyqt_failed
    "%VENV_PYTHON%" -m pip install PyInstaller==4.10
)
if errorlevel 1 goto dependency_failed

"%VENV_PYTHON%" -c "import PyQt5.QtCore as q; import PyInstaller; print('PyQt5:',q.PYQT_VERSION_STR,'Qt:',q.QT_VERSION_STR); print('PyInstaller:',PyInstaller.__version__)"
if errorlevel 1 goto dependency_failed
"%VENV_PYTHON%" -c "from ui.main_window import MainWindow; print('Application import preflight: OK')"
if errorlevel 1 goto source_compatibility_failed
echo [OK] Fixed dependencies installed.
echo.

echo [5/7] Checking Git runtime...
where git >nul 2>&1
if errorlevel 1 (
    echo [WARN] Git is not installed or is not in PATH.
    echo [WARN] The EXE can be built, but the application requires Git at runtime.
) else (
    git --version
)
echo.

echo [6/7] Cleaning old output and building EXE...
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "%SPEC_DIR%" rmdir /s /q "%SPEC_DIR%"
if exist "%PACKAGE_DIR%" rmdir /s /q "%PACKAGE_DIR%"
if exist "%FINAL_EXE%" del /f /q "%FINAL_EXE%"

mkdir "%BUILD_DIR%" >nul 2>&1
mkdir "%DIST_DIR%" >nul 2>&1
mkdir "%SPEC_DIR%" >nul 2>&1

"%VENV_PYTHON%" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name "STM32GitReleaseTool-Win7" ^
    --distpath "%DIST_DIR%" ^
    --workpath "%BUILD_DIR%" ^
    --specpath "%SPEC_DIR%" ^
    --version-file "%VERSION_FILE%" ^
    --add-data "%TEMPLATE_DIR%;templates" ^
    --add-data "%README_FILE%;." ^
    --add-data "%LICENSE_FILE%;." ^
    "%MAIN_FILE%"
if errorlevel 1 goto build_failed
if not exist "%BUILT_EXE%" goto output_missing
echo [OK] PyInstaller build completed.
echo.

echo [7/7] Creating final release files...
copy /y "%BUILT_EXE%" "%FINAL_EXE%" >nul
if errorlevel 1 goto copy_failed

mkdir "%PACKAGE_DIR%" >nul 2>&1
copy /y "%FINAL_EXE%" "%PACKAGE_DIR%\STM32GitReleaseTool-Win7.exe" >nul
copy /y "%README_FILE%" "%PACKAGE_DIR%\README.md" >nul
copy /y "%LICENSE_FILE%" "%PACKAGE_DIR%\LICENSE" >nul

certutil -hashfile "%FINAL_EXE%" SHA256 > "%PROJECT_DIR%\STM32GitReleaseTool-Win7.sha256.txt"
if errorlevel 1 (
    echo [WARN] Could not create SHA256 file with certutil.
)

for %%F in ("%FINAL_EXE%") do set "FINAL_SIZE=%%~zF"
echo.
echo ================================================================
echo [SUCCESS] Windows 7 build completed
echo ================================================================
echo EXE: %FINAL_EXE%
echo Size: %FINAL_SIZE% bytes
echo Package folder: %PACKAGE_DIR%
echo SHA256: %PROJECT_DIR%\STM32GitReleaseTool-Win7.sha256.txt
echo.
echo Copy the EXE to a clean Windows 7 SP1 64-bit computer and test:
echo   1. Application startup
echo   2. Chinese and English switching
echo   3. Project selection and Git status
echo   4. Commit, tag, package, branch, diff, and recovery workflows
echo.
set /p OPEN_DIR="Open output folder now? (Y/N): "
if /i "%OPEN_DIR%"=="Y" explorer "%PROJECT_DIR%"
echo.
pause
exit /b 0

:missing_main
echo [FAIL] main.py was not found: %MAIN_FILE%
goto failed

:missing_version
echo [FAIL] Version file was not found: %VERSION_FILE%
goto failed

:missing_templates
echo [FAIL] templates folder was not found: %TEMPLATE_DIR%
goto failed

:missing_readme
echo [FAIL] README.md was not found: %README_FILE%
goto failed

:missing_license
echo [FAIL] LICENSE was not found: %LICENSE_FILE%
goto failed

:missing_python
echo [FAIL] Python was not found in PATH.
echo Install 64-bit Python 3.8.10 and enable Add Python to PATH.
goto failed

:wrong_python
echo [FAIL] This Win7 build requires 64-bit Python 3.8.x.
echo Recommended version: Python 3.8.10 64-bit.
echo Do not use Python 3.9 or newer on Windows 7.
goto failed

:venv_failed
echo [FAIL] Could not create the isolated Python environment.
goto failed

:pip_tools_failed
echo [FAIL] Could not install Python 3.8 compatible pip tools.
echo Check network and Windows 7 TLS/SHA-2 updates.
goto failed

:pyqt_failed
echo [FAIL] Could not install the fixed PyQt5 packages.
echo Check network, TLS support, and that Python is 3.8 64-bit.
goto failed

:dependency_failed
echo [FAIL] Could not install or import the build dependencies.
goto failed

:source_compatibility_failed
echo [FAIL] The application source cannot be imported by Python 3.8.
echo Run tests\smoke_test.py on the development computer and fix compatibility errors.
goto failed

:build_failed
echo [FAIL] PyInstaller failed to build the application.
echo Review the messages above. Build work directory:
echo %BUILD_DIR%
goto failed

:output_missing
echo [FAIL] PyInstaller finished without creating:
echo %BUILT_EXE%
goto failed

:copy_failed
echo [FAIL] Could not copy the final EXE to the project directory.
goto failed

:failed
echo.
echo Build failed. No release should be published from this run.
echo.
pause
exit /b 1
