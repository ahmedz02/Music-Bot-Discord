# Discord Music Bot

A simple Discord music bot that can play music from YouTube and other sources.

## Features

- Join voice channels
- Play music from YouTube URLs
- Pause/resume playback
- Adjust volume
- Stop playback and disconnect

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Install FFmpeg:
- Windows: Download from https://ffmpeg.org/download.html and add to PATH
- Linux: `sudo apt-get install ffmpeg`
- macOS: `brew install ffmpeg`

3. Create a Discord bot:
   - Go to https://discord.com/developers/applications
   - Create a New Application
   - Go to the "Bot" tab and create a bot
   - Copy the bot token
   - Enable the following Privileged Gateway Intents:
     - MESSAGE CONTENT INTENT
     - SERVER MEMBERS INTENT
     - PRESENCE INTENT

4. Edit the `.env` file and replace `your_bot_token_here` with your actual bot token

5. Invite the bot to your server:
   - Go to OAuth2 > URL Generator
   - Select the following scopes:
     - bot
     - applications.commands
   - Select the following bot permissions:
     - Send Messages
     - Connect
     - Speak
     - Use Voice Activity
   - Copy the generated URL and open it in your browser

## Usage

- `!join` - Makes the bot join your voice channel
- `!play <url>` - Plays a song from the given URL
- `!pause` - Pauses the current song
- `!resume` - Resumes the current song
- `!stop` - Stops playback and disconnects the bot
- `!volume <0-100>` - Adjusts the volume

## Running the Bot

```bash
python bot.py
``` 