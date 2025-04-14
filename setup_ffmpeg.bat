@echo off
echo Downloading FFmpeg...
powershell -Command "(New-Object Net.WebClient).DownloadFile('https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip', 'ffmpeg.zip')"

echo Extracting FFmpeg...
powershell -Command "Expand-Archive -Path ffmpeg.zip -DestinationPath C:\ffmpeg -Force"

echo Adding FFmpeg to PATH...
setx PATH "%PATH%;C:\ffmpeg\bin" /M

echo Cleaning up...
del ffmpeg.zip

echo FFmpeg installation complete!
pause 