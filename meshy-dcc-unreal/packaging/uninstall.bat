@echo off
REM meshy-dcc-unreal — Windows uninstaller
setlocal

set "PROJECT_ROOT=%CD%"
set "ENGINE_ROOT="

:parse_args
if "%~1"=="" goto :done_args
if /i "%~1"=="--engine" (
    set "ENGINE_ROOT=%~2"
    shift & shift & goto :parse_args
)
if /i "%~1"=="--project" (
    set "PROJECT_ROOT=%~2"
    shift & shift & goto :parse_args
)
shift & goto :parse_args
:done_args

if not "%ENGINE_ROOT%"=="" (
    set "DEST=%ENGINE_ROOT%\Engine\Plugins\MeshyDccUnreal"
) else (
    set "DEST=%PROJECT_ROOT%\Plugins\MeshyDccUnreal"
)

if not exist "%DEST%" (
    echo [meshy-dcc-unreal] Plugin not found at %DEST%
    exit /b 0
)

echo Removing %DEST% ...
rmdir /s /q "%DEST%"
echo [meshy-dcc-unreal] Uninstalled successfully.
endlocal
