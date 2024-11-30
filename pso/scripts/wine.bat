@echo off

::zeroz41

if "%1"=="configure_wine" (
    call :configure_wine
    exit /b
)

if "%1"=="check_admin_privileges" (
    call :check_admin_privileges
    exit /b
)

if "%1"=="reg_set" (
    call :reg_set %2 %3 %4
    exit /b
)

if "%1"=="winetricks_install" (
    call :winetricks_install
    exit /b
)

exit /b

:check_admin_privileges
echo Checking if the script is running with administrative privileges...
net session >nul 2>&1
if %errorLevel% == 0 (
    echo No error in checking admin priv
) else (
    echo This script requires administrative privileges. Please run it as an administrator.
    ping -n 6 127.0.0.1 >nul
    exit /b 1
)
exit /b


::defunct, remove later
:reg_set
:: set the window mode to a variable
echo Received in wine.bat:installdir %1, windowMode: %~2, useD3D9: %~3
set "installDir=%~1"
set "windowMode=%~2"
set "useD3D9=%~3"
echo Setting the dll override "d3d9" to native...
reg add "HKCU\Software\Wine\DllOverrides" /v "d3d9" /t REG_SZ /d "native,builtin" /f

echo Setting the path to the registry files...
set "registryDir=%~dp0..\registry"
set "installRegFile=%registryDir%\wrap_install.reg"
set "sonicRegFile=%registryDir%\wrap_sonic.reg"

echo Updating wrap_install.reg with the determined EphineaPSO path...
(
    echo [HKEY_CURRENT_USER\Software\EphineaPSO]
    echo "Install_Dir"=%installDir%
) > "%installRegFile%"

echo Updating USE_D3D9 and WINDOW_MODE registry values...
echo windowmode is %windowMode%
echo useD3D9 is %useD3D9%
setlocal enabledelayedexpansion
reg add "HKCU\Software\SonicTeam\PSOBB" /v "WINDOW_MODE" /t REG_DWORD /d !windowMode! /f
reg add "HKCU\Software\SonicTeam\PSOBB\Ephinea" /v "USE_D3D9" /t REG_DWORD /d !useD3D9! /f
endlocal

echo Importing registry file: wrap_install.reg...
reg import "%installRegFile%"
::call :check_error "Failed to import wrap_install.reg. Please check if the file exists."

echo Importing registry file: wrap_sonic.reg...
reg import "%sonicRegFile%"
::call :check_error "Failed to import wrap_sonic.reg. Please check if the file exists."

echo Registry files installed successfully!
exit /b


::safe to use winecfg, as we suppress gui popups if run through linux
:configure_wine

echo Setting the Windows version to Windows 7...
winecfg -v win7

:: set d3d9 override to nb
echo Setting the dll override "d3d9" to native,builtin...
reg add "HKCU\Software\Wine\DllOverrides" /v "d3d9" /t REG_SZ /d "native,builtin" /f
exit /b


::defunct, remove later
:winetricks_install
echo Checking if winetricks is installed...
where winetricks >nul 2>&1
if %errorlevel% equ 0 (
    echo Winetricks is installed. Installing dotnet462 and gecko...
    winetricks dotnet462 gecko
    if %errorlevel% neq 0 (
        echo Error: Failed to install dotnet462 and gecko using winetricks.
        exit /b 1
    )
) else (
    echo Winetricks is not installed. Skipping installation of dotnet462 and gecko.
)
exit /b

::unneeded, toss out
:check_error
if %errorlevel% neq 0 (
    echo %~1
    ping -n 6 127.0.0.1 >nul
    exit /b 1
)
goto :eof
