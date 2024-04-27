@echo off
setlocal

set "url=%~1"
set "output_file=%~2"
set "temp_file=%output_file%.tmp"
set "max_retries=3"
set "retry_count=0"

:download
echo Downloading %url% to %temp_file%...
curl.exe -k -L -C - -o "%temp_file%" "%url%"

if %errorlevel% neq 0 (
    set /a "retry_count+=1"
    if %retry_count% lss %max_retries% (
        echo Download failed. Retrying... (Attempt %retry_count% of %max_retries%)
        goto download
    ) else (
        echo Error: Failed to download the file after %max_retries% attempts.
        exit /b 1
    )
)

echo Renaming %temp_file% to %output_file%...
move /Y "%temp_file%" "%output_file%" >nul

echo Download completed successfully.
exit /b 0