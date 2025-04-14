@echo off
echo Installing Discord Music Bot as a Windows Service...

:: Download NSSM
powershell -Command "& {Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile 'nssm.zip'}"
powershell -Command "& {Expand-Archive -Path 'nssm.zip' -DestinationPath '.' -Force}"

:: Copy NSSM to the right location based on system architecture
if exist "%PROGRAMFILES(X86)%" (
    copy /Y "nssm-2.24\win64\nssm.exe" "nssm.exe"
) else (
    copy /Y "nssm-2.24\win32\nssm.exe" "nssm.exe"
)

:: Get the current directory
set "CURRENT_DIR=%CD%"

:: Install the service
nssm.exe install DiscordMusicBot "%CURRENT_DIR%\start_bot.bat"
nssm.exe set DiscordMusicBot AppDirectory "%CURRENT_DIR%"
nssm.exe set DiscordMusicBot DisplayName "Discord Music Bot"
nssm.exe set DiscordMusicBot Description "Discord Music Bot Service"
nssm.exe set DiscordMusicBot Start SERVICE_AUTO_START

:: Start the service
net start DiscordMusicBot

:: Clean up
rmdir /S /Q nssm-2.24
del /F /Q nssm.zip
del /F /Q nssm.exe

echo.
echo Discord Music Bot has been installed as a Windows service!
echo The bot will now start automatically when Windows starts.
echo.
echo To manage the service:
echo - Open Services (services.msc)
echo - Look for "Discord Music Bot"
echo - You can start/stop/restart the service from there
echo.
pause 