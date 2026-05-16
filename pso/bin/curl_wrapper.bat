@echo off
setlocal enabledelayedexpansion

set "url=%~1"
set "output_file=%~2"
set "temp_file=%output_file%.tmp"
set "max_retries=3"
set "retry_count=0"

:download
set /a "retry_count+=1"
if exist "%temp_file%" (
    if !retry_count! gtr 1 (
        echo Deleting incomplete temp file before retry...
        del "%temp_file%"
    )
)

echo Downloading %url% to %temp_file%... (Attempt !retry_count! of %max_retries%)
curl.exe -k -L -C - -o "%temp_file%" "%url%"
set "curl_exit=%errorlevel%"

if !curl_exit! neq 0 (
    echo curl exited with code !curl_exit!.
    if !retry_count! lss %max_retries% (
        echo Retrying...
        goto download
    ) else (
        echo Error: Failed to download the file after %max_retries% attempts.
        if exist "%temp_file%" del "%temp_file%"
        exit /b 1
    )
)

:: Verify the downloaded file is not suspiciously small (e.g. an error page)
for %%F in ("%temp_file%") do set "file_size=%%~zF"
if !file_size! lss 1000 (
    echo Error: Downloaded file is only !file_size! bytes - likely an error page, not the real file.
    if exist "%temp_file%" del "%temp_file%"
    if !retry_count! lss %max_retries% (
        echo Retrying with fresh download...
        goto download
    ) else (
        echo Error: Failed to download a valid file after %max_retries% attempts.
        exit /b 1
    )
)

echo Renaming %temp_file% to %output_file%...
move /Y "%temp_file%" "%output_file%" >nul

echo Download completed successfully.
exit /b 0
