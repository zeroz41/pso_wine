@echo off

set "curr_dir=%~dp0"
set "pso_bat=%curr_dir%\..\scripts\pso.bat"

if not exist "%pso_bat%" (
    echo pso.bat not found. Please check the file path.
    exit /b 1
)

:: i = install. s = desktop shortcuts made
call "%pso_bat%" -i -s