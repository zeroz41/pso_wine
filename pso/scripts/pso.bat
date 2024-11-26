@echo off
setlocal enabledelayedexpansion

set "execute=0"
set "install=0"
set "uninstall=0"
set "launcher=0"
set "desktop_shortcuts=0"

:: made by zeroz41, tj

::TODO, add option to use better icons. Classic pso ugly
::make modular to run other popular client installs with core functionality. Can swap "Ephinea" string with others for key

::MAKE IT SHUTUP
set WINEDEBUG=-all

:: scripts folder
set "current_dir=%~dp0"

:: base dir is pso folder
for %%i in ("%current_dir%..") do set "base_dir=%%~fi"

:: Bin and log directories within the parent directory
set "bin_dir=%base_dir%\bin"
set "log_dir=%base_dir%\logs"

::set the log file based on the user
:: Set the log file to the script_dir logs folder
set "logFile=%log_dir%\execution.log"

:: Make the script_dir logs folder if it doesn't exist
if not exist "%base_dir%\logs" mkdir "%base_dir%\logs"
if not exist "%base_dir%\bin" mkdir "%base_dir%\bin"


:parse_args
set "installer_path="

for %%a in (%*) do (
    if "%%a"=="-i" (
        set "install=1"
        set "next_arg_is_installer_path=1"
    ) else if defined next_arg_is_installer_path (
        if "%%a:~0,1%%" neq "-" (
            if exist "%%a" (
                echo Installer found: %%a
                set "installer_path=%%a"
            ) else (
                echo Installer path "%%a" does not exist. Trying default path...
            )
            set "next_arg_is_installer_path="
        ) else (
            set "next_arg_is_installer_path="
        )
    )
    if "%%a" neq "-i" (
        if "%%a"=="-u" (
            echo setting uninstall to %uninstall%
            set "uninstall=1"
        )
        if "%%a"=="-e" (
            set "execute=1"
        )
        if "%%a"=="-l" (
            set "launcher=1"
        )
        if "%%a"=="-s" (
            set "desktop_shortcuts=1"
        )
    )
)

:: Only check for installer if installing
if %install% equ 1 (
    if not defined installer_path (
        echo Installer path not provided. Trying default path...
        goto check_default_installer
    )
) else (
    goto continue
)

:check_default_installer
if exist "%bin_dir%\Ephinea_PSOBB_Installer.exe" (
    set "installer_path=%bin_dir%\Ephinea_PSOBB_Installer.exe"
    setlocal enabledelayedexpansion
    echo Set installer path to default: !installer_path!
    endlocal
) else (
    echo Installer not found. Attempting to download Ephinea_PSOBB_Installer.exe... please wait
    call :dl_installer
    if %errorlevel% neq 0 (
        echo Download failed. Exiting script.
        goto end
    )
)
goto continue

:continue

::attempts to find installation path from registry entry
call :get_installed_path

::if for some reason you screwed with things, we try to search around a little
if not defined install_dir (
    call :find_install_dir
)

echo Using installation directory: %install_dir%

::mostly unneeded. remove later
::echo Checking admin privs
::call "%~dp0wine.bat" check_admin_privileges

::sets need win7 mode and d3d9 n,b override for wine directx9 to run system dx9 w/ native aux ephinea dx dlls
:: you could perhaps want to use pure native if using things like dxwrapper or dgvoodoo. but that may require
:: an extra d3d9.dll in install folder. 
:: ...or, an additional all native hack is steal one of the dgvoo_d3d9 or dxvk and copy and rename it to d3d9,
:: dxwrapper can allow you to also enable better debugging and some extra features to try....with the use of built in or native d3d9,
:: all you'd have to do is configure the fake wrapper dx to point to either system directx or spoof it to a directx dll in this folder.
::also i see know real benefit to using dgvoodoo for this game unless its the only way to get it to work. -tj

if %install% equ 1 (
    echo Configuring wine
    call "%~dp0wine.bat" configure_wine
    echo Installing Ephinea...
    call :install_ephinea
)

if %uninstall% equ 1 (
    echo Uninstalling Ephinea...
    call :uninstall_ephinea
)

if %execute% equ 1 (
    echo Running the game... in directory %install_dir%
    ::also log the echo
    echo Running the game... in directory %install_dir% >> "%logFile%"
    if %launcher% equ 1 (
        call :execute_game "%install_dir%" "online.exe"
    ) else (
        call :execute_game "%install_dir%" "PsoBB.exe"
    )
) else (
    echo Not running the game, execute is false...
    echo Not running the game, execute is false... >> "%logFile%"
)

echo.
echo Script execution completed...
::pause >nul
goto end

::FUNCTIONS BELOW. END MAIN SCRIPT ABOVE
:: batch scripting is a horrible thing. What a waste. -tj
:: ;)


::not super important, but as a fallback we use this ungodly if tree to search where PSO might be installed.
::not really necessary to use either.
:find_install_dir
echo Determining EphineaPSO directory...

if exist "C:\users\%USERNAME%\EphineaPSO" (
    set "install_dir=C:\users\%USERNAME%\EphineaPSO"
    echo Found EphineaPSO directory: !install_dir!
) else (
    if exist "C:\EphineaPSO" (
        set "install_dir=C:\EphineaPSO"
        echo Found EphineaPSO directory: !install_dir!
    ) else (
        if exist "E:\EphineaPSO" (
            set "install_dir=E:\EphineaPSO"
            echo Found EphineaPSO directory: !install_dir!
        ) else (
            if exist "F:\EphineaPSO" (
                set "install_dir=F:\EphineaPSO"
                echo Found EphineaPSO directory: !install_dir!
                ::ping -n 6 127.0.0.1 >nul
                ::exit /b 1
                ) else (
                    if exist "D:\EphineaPSO" (
                    set "install_dir=D:\EphineaPSO"
                    echo Found EphineaPSO directory: !install_dir!
                    ::ping -n 6 127.0.0.1 >nul
                    ::exit /b 1
                    ) else (

                
                        set "install_dir=C:\EphineaPSO"
                        echo No existing EphineaPSO install directory found....setting to default
                    )
                )
            )
        )
)

goto :eof

:install_ephinea
set "total_size=1334232"
::want to put a live progress bar in batch. having trouble...removing for now (better with python)
:: again cmd script is trash and requires creativity. multithreading...
setlocal enabledelayedexpansion
echo Running the installer in silent mode...
:: Debugging echo to ensure paths are correct
echo Installer Path: !installer_path!
echo Install Dir: !install_dir!

:: Execute the installer with the correct path
echo "!installer_path!" /S /D=!install_dir!
"!installer_path!" /S /D=!install_dir!

echo Installation completed.

call :remove_unwanted_shortcuts
call :create_wanted_shortcuts

goto :eof

:create_shortcut
set "name=%~1"
set "target=%~2"
set "shortcut_path=%~3"

echo Creating shortcut: %shortcut_path%
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = "%shortcut_path%" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "%target%" >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs
cscript CreateShortcut.vbs
del CreateShortcut.vbs

goto :eof

:create_wanted_shortcuts
set "profile_path=%USERPROFILE%"
call :create_shortcut "Ephinea Launcher" "%install_dir%\online.exe" "%profile_path%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Ephinea Launcher.lnk"
call :create_shortcut "Ephinea PSOBB" "%install_dir%\PsoBB.exe" "%profile_path%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Ephinea PSOBB.lnk"

::desktop icons...enable for android install likely. 
::defaults to off. would put them on linux host as well. 
if %desktop_shortcuts% equ 1 (
    call :create_shortcut "Ephinea Launcher" "%install_dir%\online.exe" "%profile_path%\Desktop\Ephinea Launcher.lnk"
    call :create_shortcut "Ephinea PSOBB" "%install_dir%\PsoBB.exe" "%profile_path%\Desktop\Ephinea PSOBB.lnk"
)

goto :eof

:remove_unwanted_shortcuts
set "profile_path=%USERPROFILE%"
echo Profile path is %USERPROFILE%
::not all of these entries are really necessary, but its fine ha
::this removes ALL. which is why it is called before install wanted.
::it is recalled on uninstall
call :remove_shortcut "%profile_path%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Ephinea PSOBB\Launch Ephinea PSOBB.lnk"
call :remove_shortcut "%profile_path%\Desktop\Ephinea.lnk"
call :remove_shortcut "%profile_path%\Desktop\Ephinea Launcher.lnk"
call :remove_shortcut "%profile_path%\Desktop\Ephinea Launcherlink.lnk"
call :remove_shortcut "%profile_path%\Desktop\Ephinea PSOBB.lnk"
call :remove_shortcut "%profile_path%\Desktop\Ephinea Readme.lnk"
call :remove_shortcut "%profile_path%\Desktop\Ephinea Readmelink.lnk"
call :remove_shortcut "%profile_path%\Start Menu\Programs\Ephinea.lnk"
call :remove_shortcut "%profile_path%\Start Menu\Programs\Ephinea Launcherlink.lnk"
call :remove_shortcut "%profile_path%\Start Menu\Programs\Ephinea PSOBB.lnk"
call :remove_shortcut "%profile_path%\Start Menu\Programs\Ephinea Readme.lnk"
call :remove_shortcut "%profile_path%\Start Menu\Programs\Ephinea Readmelink.lnk"
call :remove_shortcut "%profile_path%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Ephinea.lnk"
call :remove_shortcut "%profile_path%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Ephinea Launcherlink.lnk"
call :remove_shortcut "%profile_path%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Ephinea PSOBB.lnk"
call :remove_shortcut "%profile_path%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Ephinea Readme.lnk"
call :remove_shortcut "%profile_path%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Ephinea Readmelink.lnk"
call :remove_shortcut "%profile_path%\Start Menu\Programs\Ephinea Launcher.lnk"
call :remove_shortcut "%profile_path%\Start Menu\Programs\Ephinea PSOBB.lnk"
call :remove_shortcut "%profile_path%\Desktop\Ephinea Launcher.lnk"
call :remove_shortcut "%profile_path%\Desktop\Ephinea PSOBB.lnk"
goto :eof

:uninstall_ephinea
echo Uninstalling Ephinea...
if exist "%install_dir%" (
    echo Removing the installation directory...
    rd /s /q "%install_dir%"
    ::todo add the uninstaller.exe and just call it. removes reg entries too i think. havnt tried
)

:: Remove Start menu entries and desktop shortcuts for Ephinea Launcher and Ephinea PSOBB
call :remove_unwanted_shortcuts


echo Uninstallation completed.
goto :eof

:remove_shortcut
set "shortcut_path=%~1"

if exist "%shortcut_path%" (
    del "%shortcut_path%"
)

goto :eof

:execute_game
echo Running %~2 and capturing output and error logs...
:: requires installation dir as arg 1, and executable name as arg 2
::"%~2" > "PsoBB_stdout.log" 2> "PsoBB_stderr.log"
echo starting %~2
start /b "" "%~1\%~2" > "%log_dir%\PsoBB_stdout.log" 2> "%log_dir%\PsoBB_stderr.log" 2> nul

if %errorlevel% neq 0 (
    echo Error: Failed to run %~2. Please check the logs for more details. >> "%logFile%"
    type "PsoBB_stdout.log" >> "%logFile%"
    type "PsoBB_stderr.log" >> "%logFile%"
    exit /b 1
) else (
    echo %~2 launched successfully. >> "%logFile%"
)

goto :eof

:dl_installer
echo Downloading Ephinea_PSOBB_Installer.exe...
cd %bin_dir%
echo Downloading Ephinea Install client to folder %bin_dir%...
call "%bin_dir%\curl_wrapper.bat" "https://files.pioneer2.net/Ephinea_PSOBB_Installer.exe" "%bin_dir%\Ephinea_PSOBB_Installer.exe"

:checkdownload
ping -n 6 127.0.0.1 >nul
if exist "Ephinea_PSOBB_Installer.exe" (
    set "installer_path=%bin_dir%\Ephinea_PSOBB_Installer.exe"
    goto download_complete
)
echo Download still in progress...
goto checkdownload
goto checkdownload
goto checkdownload
goto checkdownload

:download_complete
cd %current_dir%
echo Installer downloaded successfully.
echo Installer downloaded successfully. >> "%logFile%"
goto :eof

:get_installed_path
set "install_dir="

for /f "skip=2 tokens=1,2*" %%a in ('reg query "HKEY_CURRENT_USER\Software\EphineaPSO" /v "Install_Dir" 2^>nul') do (
    if "%%a"=="Install_Dir" (
        set "install_dir=%%c"
    )
)

echo Registry Install directory: %install_dir%

echo Install directory: %install_dir%
goto :eof

:end
endlocal
