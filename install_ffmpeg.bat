@echo off
echo Downloading FFmpeg...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' -OutFile 'ffmpeg.zip'"

echo Creating FFmpeg directory...
if not exist "C:\ffmpeg" mkdir "C:\ffmpeg"

echo Extracting FFmpeg...
powershell -Command "Expand-Archive -Force 'ffmpeg.zip' 'C:\ffmpeg'"

echo Adding FFmpeg to PATH...
setx PATH "%PATH%;C:\ffmpeg\ffmpeg-master-latest-win64-gpl\bin" /M

echo Cleaning up...
del ffmpeg.zip

echo FFmpeg installation complete! Please restart your computer for the changes to take effect.
pause 