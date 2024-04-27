@echo off

::note this dxwrapper and copy files functions are defunct. 
::they were only for testing. Thought id include in the history.
::will remove soon. as who would want to manually copy files anyway
::zeroz41

if "%1"=="copy_files" (
    call :copy_files %2
    exit /b
)

if "%1"=="install_dxwrapper" (
    call :install_dxwrapper %2
    exit /b
)

if "%1"=="uninstall_dxwrapper" (
    call :uninstall_dxwrapper %2
    exit /b
)

if "%1"=="set_registry_params" (
    call :set_registry_params %2 %3 %4 %5
    exit /b
)

exit /b

:copy_files
echo Setting the path to the source files...
set "parentDir=%~dp0.."
set "binDir=%parentDir%\bin"
set "ephineaDLL=%binDir%\ephinea.dll"
set "installDir=%~1"

echo copy bin dir is %binDir%
echo copy installDir is %installDir%

if not exist "%ephineaDLL%" (
    echo Unable to find ephinea.dll. Please check the installation.
    ping -n 6 127.0.0.1 >nul
    exit /b 1
)

echo Copying %ephineaDLL% to the %installDir%
copy /Y "%ephineaDLL%" "%installDir%\ephinea.dll"

call :check_error "Failed to copy ephinea.dll. Please check the installation."

echo Duplicating dgVoodoo_d3d9.dll as d3d9.dll in the EphineaPSO folder...
copy /Y "%installDir%\dgVoodoo_d3d9.dll" "%installDir%\d3d9.dll"

call :check_error "Failed to duplicate dgVoodoo_d3d9.dll. Please check the installation."

exit /b

:install_dxwrapper
echo Copying DXWrapper files to the EphineaPSO folder...path: %~1
set "parentDir=%~dp0.."
set "dxwrapperDir=%parentDir%\dxwrapper"

if exist "%dxwrapperDir%" (
    copy /Y "%dxwrapperDir%\dxwrapper.ini" "%~1"
    copy /Y "%dxwrapperDir%\dxwrapper.dll" "%~1"
    copy /Y "%dxwrapperDir%\d3d9.dll" "%~1"
    copy /Y "%dxwrapperDir%\d3d9_real.dll" "%~1"
    copy /Y "%dxwrapperDir%\d3d9.ini" "%~1"
) else (
    echo DXWrapper directory not found. Please check the installation.
    ping -n 6 127.0.0.1 >nul
    exit /b 1
)

exit /b

:uninstall_dxwrapper
echo Checking for DXWrapper files in the EphineaPSO folder...

if exist "%~1\dxwrapper.ini" (
    echo Deleting dxwrapper.ini...
    del /Q "%~1\dxwrapper.ini"
)

if exist "%~1\dxwrapper.dll" (
    echo Deleting dxwrapper.dll...
    del /Q "%~1\dxwrapper.dll"
)

if exist "%~1\d3d9_real.dll" (
    echo Deleting d3d9_real.dll...
    del /Q "%~1\d3d9_real.dll"
)

if exist "%~1\d3d9.ini" (
    echo Deleting d3d9.ini...
    del /Q "%~1\d3d9.ini"
)

exit /b

:set_registry_params
set "windowed=%~1"
set "hor_res=%~2"
set "ver_res=%~3"
set "direct3d=%~4"

echo Setting registry parameters...

reg add "HKCU\Software\SonicTeam\PSOBB" /v "WINDOW_MODE" /t REG_DWORD /d %windowed% /f
reg add "HKCU\Software\SonicTeam\PSOBB\Ephinea" /v "NEW_RES_WIDTH" /t REG_DWORD /d %hor_res% /f
reg add "HKCU\Software\SonicTeam\PSOBB\Ephinea" /v "NEW_RES_HEIGHT" /t REG_DWORD /d %ver_res% /f
reg add "HKCU\Software\SonicTeam\PSOBB\Ephinea" /v "USE_D3D9" /t REG_DWORD /d %direct3d% /f

echo Registry parameters set successfully.

exit /b

:check_error
if %errorlevel% neq 0 (
    echo %~1
    ping -n 6 127.0.0.1 >nul
    exit /b 1
)

exit /b