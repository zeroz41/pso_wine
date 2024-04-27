@echo off

set "params_file=USER_PARAMS.txt"

if not exist "%params_file%" (
    echo USER_PARAMS.txt file not found. Please create the file with the required parameters.
    exit /b 1
)

for /f "tokens=1,2 delims==" %%a in (%params_file%) do (
    if "%%a"=="WINDOWED" set "windowed=%%b"
    if "%%a"=="HOR_RES" set "hor_res=%%b"
    if "%%a"=="VER_RES" set "ver_res=%%b"
    if "%%a"=="DIRECT3D" set "direct3d=%%b"
)

echo Parameter values:
echo WINDOWED: %windowed%
echo HOR_RES: %hor_res%
echo VER_RES: %ver_res%
echo DIRECT3D: %direct3d%

set "script_dir=%~dp0"
set "utils_bat=%script_dir%\..\scripts\utils.bat"

if not exist "%utils_bat%" (
    echo utils.bat not found. Please check the file path.
    exit /b 1
)

call "%utils_bat%" set_registry_params %windowed% %hor_res% %ver_res% %direct3d%