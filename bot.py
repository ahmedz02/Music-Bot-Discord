import os
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select
from dotenv import load_dotenv
import yt_dlp
import asyncio
import logging
import urllib.parse
from collections import deque
import random
import aiohttp
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

# Check FFmpeg installation
try:
    ffmpeg_path = subprocess.check_output(['which', 'ffmpeg']).decode().strip()
    logger.info(f"FFmpeg found at: {ffmpeg_path}")
except subprocess.CalledProcessError:
    logger.error("FFmpeg not found in PATH")
    try:
        # Try to find FFmpeg in common locations
        common_paths = [
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
            '/opt/ffmpeg/ffmpeg'
        ]
        for path in common_paths:
            if os.path.exists(path):
                logger.info(f"Found FFmpeg at: {path}")
                os.environ['PATH'] = f"{os.path.dirname(path)}:{os.environ.get('PATH', '')}"
                break
    except Exception as e:
        logger.error(f"Error searching for FFmpeg: {e}")

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Bot setup
class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(command_prefix='!', intents=intents)
        self.music_queues = {}  # Dictionary to store queues for each guild
        
    async def setup_hook(self):
        await self.tree.sync()
        logger.info("Commands synced!")

bot = MusicBot()

# Suppress noise about console usage from errors
yt_dlp.utils.bug_reports_message = lambda: ''

# YouTube DL configuration
ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'force-ipv4': True,
    'prefer_ffmpeg': True,
    'ffmpeg_location': '/usr/local/bin/ffmpeg'  # Specify FFmpeg location
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class QueueView(View):
    def __init__(self, guild_state):
        super().__init__(timeout=None)
        self.guild_state = guild_state
        self.page = 0
        self.items_per_page = 10

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.grey)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await self.update_queue_message(interaction)

    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.grey)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (self.page + 1) * self.items_per_page < len(self.guild_state.queue):
            self.page += 1
            await self.update_queue_message(interaction)

    @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.blurple)
    async def shuffle_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        queue_list = list(self.guild_state.queue)
        random.shuffle(queue_list)
        self.guild_state.queue = deque(queue_list)
        await self.update_queue_message(interaction)

    async def update_queue_message(self, interaction: discord.Interaction):
        start_idx = self.page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        queue_items = list(self.guild_state.queue)[start_idx:end_idx]
        
        queue_list = "\n".join([f"{i+start_idx+1}. {song.title}" for i, song in enumerate(queue_items)])
        embed = discord.Embed(
            title="🎵 Music Queue",
            description=queue_list if queue_list else "Queue is empty!",
            color=discord.Color.blue()
        )
        
        if self.guild_state.current_player:
            embed.add_field(
                name="Now Playing", 
                value=f"🎵 {self.guild_state.current_player.title}\n" + 
                      (f"🔁 Loop: {'Enabled' if self.guild_state.loop else 'Disabled'}" if hasattr(self.guild_state, 'loop') else ""),
                inline=False
            )
        
        total_pages = (len(self.guild_state.queue) - 1) // self.items_per_page + 1
        embed.set_footer(text=f"Page {self.page + 1}/{total_pages}")
        
        await interaction.response.edit_message(embed=embed, view=self)

class MusicControls(discord.ui.View):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=None)
        self.interaction = interaction

    @discord.ui.button(label="🔉 Down", style=discord.ButtonStyle.secondary, row=0)
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            guild_id = interaction.guild_id
            if guild_id in guild_states:
                guild_states[guild_id].volume = max(0.0, guild_states[guild_id].volume - 0.1)
                current_volume = int(guild_states[guild_id].volume * 100)
                if interaction.guild.voice_client and interaction.guild.voice_client.source:
                    interaction.guild.voice_client.source.volume = guild_states[guild_id].volume
                await interaction.response.send_message(f"🔉 Volume: {current_volume}%", ephemeral=True)
            else:
                await interaction.response.send_message("No music is playing right now.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in volume down: {e}")
            await interaction.response.send_message("An error occurred while adjusting volume.", ephemeral=True)

    @discord.ui.button(label="⏮️ Back", style=discord.ButtonStyle.primary, row=0)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            voice_client = interaction.guild.voice_client
            if voice_client and voice_client.is_playing():
                # For now, just restart the current song
                voice_client.seek(0)
                await interaction.response.send_message("⏮️ Restarted the current song", ephemeral=True)
            else:
                await interaction.response.send_message("Nothing is playing right now.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in back button: {e}")
            await interaction.response.send_message("An error occurred.", ephemeral=True)

    @discord.ui.button(label="⏯️ Resume/Pause", style=discord.ButtonStyle.success, row=0)
    async def resume_pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            voice_client = interaction.guild.voice_client
            if not voice_client:
                await interaction.response.send_message("Not playing anything right now.", ephemeral=True)
                return

            if voice_client.is_paused():
                voice_client.resume()
                await interaction.response.send_message("▶️ Resumed", ephemeral=True)
            elif voice_client.is_playing():
                voice_client.pause()
                await interaction.response.send_message("⏸️ Paused", ephemeral=True)
            else:
                await interaction.response.send_message("No audio playing.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in resume/pause: {e}")
            await interaction.response.send_message("An error occurred.", ephemeral=True)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.primary, row=0)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            voice_client = interaction.guild.voice_client
            if voice_client and voice_client.is_playing():
                voice_client.stop()
                await interaction.response.send_message("⏭️ Skipped", ephemeral=True)
            else:
                await interaction.response.send_message("Nothing to skip.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in skip: {e}")
            await interaction.response.send_message("An error occurred.", ephemeral=True)

    @discord.ui.button(label="🔊 Up", style=discord.ButtonStyle.secondary, row=0)
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            guild_id = interaction.guild_id
            if guild_id in guild_states:
                guild_states[guild_id].volume = min(2.0, guild_states[guild_id].volume + 0.1)
                current_volume = int(guild_states[guild_id].volume * 100)
                if interaction.guild.voice_client and interaction.guild.voice_client.source:
                    interaction.guild.voice_client.source.volume = guild_states[guild_id].volume
                await interaction.response.send_message(f"🔊 Volume: {current_volume}%", ephemeral=True)
            else:
                await interaction.response.send_message("No music is playing right now.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in volume up: {e}")
            await interaction.response.send_message("An error occurred while adjusting volume.", ephemeral=True)

    @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.secondary, row=1)
    async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            guild_id = interaction.guild_id
            if guild_id in bot.music_queues and bot.music_queues[guild_id].queue:
                queue_list = list(bot.music_queues[guild_id].queue)
                random.shuffle(queue_list)
                bot.music_queues[guild_id].queue = deque(queue_list)
                await interaction.response.send_message("🔀 Queue shuffled!", ephemeral=True)
            else:
                await interaction.response.send_message("No songs in queue to shuffle.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in shuffle: {e}")
            await interaction.response.send_message("An error occurred.", ephemeral=True)

    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.secondary, row=1)
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            guild_id = interaction.guild_id
            if guild_id in guild_states:
                guild_states[guild_id].loop = not guild_states[guild_id].loop
                status = "enabled" if guild_states[guild_id].loop else "disabled"
                await interaction.response.send_message(f"🔁 Loop {status}", ephemeral=True)
            else:
                await interaction.response.send_message("No music is playing right now.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in loop: {e}")
            await interaction.response.send_message("An error occurred.", ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger, row=1)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            voice_client = interaction.guild.voice_client
            if voice_client:
                await voice_client.disconnect()
                await interaction.response.send_message("⏹️ Stopped and disconnected", ephemeral=True)
            else:
                await interaction.response.send_message("Not connected to a voice channel.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in stop: {e}")
            await interaction.response.send_message("An error occurred.", ephemeral=True)

    @discord.ui.button(label="⏺️ AutoPlay", style=discord.ButtonStyle.secondary, row=1)
    async def autoplay_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # This is a placeholder for autoplay functionality
        await interaction.response.send_message("AutoPlay feature coming soon!", ephemeral=True)

    @discord.ui.button(label="📜 Playlist", style=discord.ButtonStyle.secondary, row=1)
    async def playlist_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            guild_state = bot.music_queues.get(interaction.guild_id)
            if not guild_state or not guild_state.queue:
                await interaction.response.send_message("The queue is empty!", ephemeral=True)
                return

            view = QueueView(guild_state)
            await view.update_queue_message(interaction)
        except Exception as e:
            logger.error(f"Error showing playlist: {e}")
            await interaction.response.send_message("An error occurred while showing the playlist.", ephemeral=True)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.thumbnail = data.get('thumbnail')
        self.duration = data.get('duration')
        self.webpage_url = data.get('webpage_url')

    @classmethod
    async def search_and_get_song(cls, search_query, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        try:
            # If it's not a URL, search for it
            if not search_query.startswith('http'):
                search_query = f"ytsearch1:{search_query}"
            
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search_query, download=not stream))
            
            if 'entries' in data:
                data = data['entries'][0]
                
            filename = data['url'] if stream else ytdl.prepare_filename(data)
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
        except Exception as e:
            logger.error(f"Error downloading song: {e}")
            raise

class GuildMusicState:
    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.queue = deque()
        self.current_player = None
        self.is_playing = False
        self.last_interaction = None
        self.loop = False
        self.volume = 1.0
        self.disconnect_task = None

    async def play_next(self, voice_client):
        if not voice_client or not voice_client.is_connected():
            return

        # Cancel any existing disconnect task
        if self.disconnect_task:
            self.disconnect_task.cancel()
            self.disconnect_task = None

        # If nothing to play and not looping
        if not self.queue and not self.loop:
            self.disconnect_task = asyncio.create_task(self.disconnect_after_timeout(voice_client))
            return

        self.is_playing = True

        if self.loop and self.current_player:
            # If loop is enabled, keep playing the same song
            voice_client.play(self.current_player, after=lambda e: asyncio.run_coroutine_threadsafe(self.song_finished(e, voice_client), bot.loop))
        elif self.queue:
            self.current_player = self.queue.popleft()
            voice_client.play(self.current_player, after=lambda e: asyncio.run_coroutine_threadsafe(self.song_finished(e, voice_client), bot.loop))
            
            # Send now playing message
            if self.last_interaction:
                embed = discord.Embed(
                    title="🎵 Now Playing",
                    description=f"[{self.current_player.title}]({self.current_player.webpage_url})",
                    color=discord.Color.blue()
                )
                if self.current_player.thumbnail:
                    embed.set_thumbnail(url=self.current_player.thumbnail)
                if self.current_player.duration:
                    minutes, seconds = divmod(self.current_player.duration, 60)
                    embed.add_field(name="Duration", value=f"{minutes}:{seconds:02d}", inline=True)
                embed.add_field(name="Requested by", value=self.last_interaction.user.mention, inline=True)
                if self.queue:
                    embed.add_field(name="Up Next", value=f"{len(self.queue)} song(s) in queue", inline=True)
                
                view = MusicControls(self.last_interaction)
                await self.last_interaction.channel.send(embed=embed, view=view)

    async def disconnect_after_timeout(self, voice_client):
        try:
            await asyncio.sleep(180)  # Wait 3 minutes
            if voice_client and voice_client.is_connected() and not self.is_playing and not self.queue:
                await voice_client.disconnect()
                if self.last_interaction:
                    await self.last_interaction.channel.send("👋 Left the voice channel due to inactivity.")
        except asyncio.CancelledError:
            pass

    async def song_finished(self, error, voice_client):
        if error:
            logger.error(f"Error in playback: {error}")
            if self.last_interaction:
                await self.last_interaction.channel.send(f"❌ Error playing the song: {str(error)}")
        
        self.is_playing = False
        
        if voice_client and voice_client.is_connected():
            if self.loop:
                # If looping, don't clear current_player
                await self.play_next(voice_client)
            else:
                # Only clear current_player if not looping
                self.current_player = None
                await self.play_next(voice_client)

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Error syncing commands: {e}")

@bot.tree.command(name="join", description="Join a voice channel")
async def join(interaction: discord.Interaction):
    """Join a voice channel"""
    try:
        if not interaction.user.voice:
            await interaction.response.send_message("You are not connected to a voice channel.", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect()

        await interaction.response.send_message(f"Joined {channel.name}")
    except Exception as e:
        logger.error(f"Error in join command: {e}")
        await interaction.response.send_message("An error occurred while trying to join the voice channel.", ephemeral=True)

@bot.tree.command(name="play", description="Play a song by name or URL")
async def play(interaction: discord.Interaction, query: str):
    """Play a song by name or URL"""
    try:
        if not interaction.user.voice:
            await interaction.response.send_message("You are not connected to a voice channel.", ephemeral=True)
            return

        await interaction.response.defer()

        # Get or create guild music state
        guild_state = bot.music_queues.get(interaction.guild_id)
        if not guild_state:
            guild_state = GuildMusicState(interaction.guild_id)
            bot.music_queues[interaction.guild_id] = guild_state

        if not interaction.guild.voice_client:
            await interaction.user.voice.channel.connect()

        try:
            player = await YTDLSource.search_and_get_song(query, loop=bot.loop, stream=True)
            guild_state.last_interaction = interaction
            
            if not guild_state.is_playing:
                guild_state.queue.append(player)
                await guild_state.play_next(interaction.guild.voice_client)
                await interaction.followup.send("🎵 Playing your song!")
            else:
                guild_state.queue.append(player)
                await interaction.followup.send(f"🎵 Added **{player.title}** to the queue! Position: {len(guild_state.queue)}")
                
        except Exception as e:
            logger.error(f"Error playing song: {e}")
            await interaction.followup.send(f"Error playing the song: {str(e)}")
    except Exception as e:
        logger.error(f"Error in play command: {e}")
        await interaction.followup.send("An error occurred while trying to play the song.")

@bot.tree.command(name="stop", description="Stop playing and disconnect")
async def stop(interaction: discord.Interaction):
    """Stop playing and disconnect"""
    try:
        if not interaction.guild.voice_client:
            await interaction.response.send_message("I'm not connected to a voice channel.", ephemeral=True)
            return

        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("Disconnected from voice channel.")
    except Exception as e:
        logger.error(f"Error in stop command: {e}")
        await interaction.response.send_message("An error occurred while trying to stop.", ephemeral=True)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == bot.user.id and after.channel is None:  # Bot was disconnected
        guild_state = bot.music_queues.get(member.guild.id)
        if guild_state:
            guild_state.queue.clear()
            guild_state.is_playing = False
            guild_state.current_player = None

@bot.tree.command(name="clear", description="Clear the music queue")
async def clear(interaction: discord.Interaction):
    """Clear the music queue"""
    guild_state = bot.music_queues.get(interaction.guild_id)
    if not guild_state:
        await interaction.response.send_message("No music queue exists!", ephemeral=True)
        return

    guild_state.queue.clear()
    await interaction.response.send_message("🗑️ Music queue cleared!")

@bot.tree.command(name="remove", description="Remove a song from the queue by its position")
async def remove(interaction: discord.Interaction, position: int):
    """Remove a song from the queue"""
    guild_state = bot.music_queues.get(interaction.guild_id)
    if not guild_state or not guild_state.queue:
        await interaction.response.send_message("Queue is empty!", ephemeral=True)
        return

    if 1 <= position <= len(guild_state.queue):
        song = list(guild_state.queue)[position-1]
        guild_state.queue.remove(song)
        await interaction.response.send_message(f"Removed **{song.title}** from the queue!")
    else:
        await interaction.response.send_message("Invalid position!", ephemeral=True)

@bot.tree.command(name="shuffle", description="Shuffle the music queue")
async def shuffle(interaction: discord.Interaction):
    """Shuffle the music queue"""
    guild_state = bot.music_queues.get(interaction.guild_id)
    if not guild_state or not guild_state.queue:
        await interaction.response.send_message("Queue is empty!", ephemeral=True)
        return

    queue_list = list(guild_state.queue)
    random.shuffle(queue_list)
    guild_state.queue = deque(queue_list)
    await interaction.response.send_message("🔀 Queue shuffled!")

@bot.tree.command(name="queue", description="Show the current music queue")
async def queue(interaction: discord.Interaction):
    """Show the current music queue"""
    guild_state = bot.music_queues.get(interaction.guild_id)
    if not guild_state or not guild_state.queue:
        await interaction.response.send_message("The queue is empty!", ephemeral=True)
        return

    view = QueueView(guild_state)
    await view.update_queue_message(interaction)

# Error handling for general command errors
@bot.event
async def on_command_error(ctx, error):
    logger.error(f"Command error: {error}")
    await ctx.send(f"An error occurred: {str(error)}")

# Run the bot
try:
    bot.run(TOKEN, log_handler=None)
except Exception as e:
    logger.error(f"Error running bot: {e}") 