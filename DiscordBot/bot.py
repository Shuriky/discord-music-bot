import os
import discord
import re
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import yt_dlp
import asyncio
from collections import deque

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

SONG_QUEUES = {}

# Handle yt_dlp search asynchronously
async def search_ytdlp_async(query, ydl_options):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _extract(query, ydl_options))

# Extract info using yt_dlp (search function)
def _extract(query, ydl_options):
    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        return ydl.extract_info(query, download=False)

# Set up bot intents (required for accessing message content)
intents = discord.Intents.default()
intents.message_content = True # Let the bot read messages

# Initialize the bot with command prefix and intents
bot = commands.Bot(command_prefix='!', intents=intents)

# on_ready: run the code when the bot comes online
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('Bot is ready to use!')

# on_message: handle incoming messages
@bot.event
async def on_message(message):
    # Prevent the bot from responding to its own messages
    if message.author == bot.user:
        return
    # Remove Discord mentions
    content_without_mentions = re.sub(r'<@!?\d+>', '', message.content)
    if '67' in content_without_mentions:
        await message.channel.send('https://tenor.com/view/bosnov-67-bosnov-67-67-meme-gif-16727368109953357722')

# Test slash command
@bot.tree.command(name="ping", description="Says pong!")
async def ping_command(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

# Play command
@bot.tree.command(name="play", description="Play a song")
async def play_command(interaction: discord.Interaction, song_query: str):
    await interaction.response.send_message(f"Loading: **{song_query}**")

    # Connect to the user's voice channel
    voice_channel = interaction.user.voice.channel

    if voice_channel is None:
        await interaction.followup.send("You are not connected to a voice channel.")
        return
    
    voice_client = interaction.guild.voice_client

    if voice_client is None:
        voice_client = await voice_channel.connect()
    elif voice_channel != voice_client.channel:
        await voice_client.move_to(voice_channel)

    # Set up youtube-dl options
    ydl_options = {
        "format": "bestaudio[abr<=96]/bestaudio", # Limit audio download speed to 96kbps
        "noplaylist": True, # Skip playlists
        "youtube_include_dash_manifest": False, # Emit some download infos
        "youtube_include_hls_manifest": False,
    }

    # Search for the song
    query = "ytsearch1: " + song_query
    result = await search_ytdlp_async(query, ydl_options)
    tracks = result.get('entries', [])
    if not tracks:
        await interaction.followup.send("No results found.")
        return
    
    first_track = tracks[0]
    audio_url = first_track['url']
    title = first_track.get('title', 'Untitled')

    # Check if the server has a queue ready, add one if not
    guild_id = str(interaction.guild.id)
    if SONG_QUEUES.get(guild_id) is None:
        SONG_QUEUES[guild_id] = deque()

    SONG_QUEUES[guild_id].append((audio_url, title))

    # If something is already playing, just add to the queue
    if voice_client.is_playing() or voice_client.is_paused():
        await interaction.followup.send(f"Added to queue: **{title}**")
    # Else play immediately
    else:
        await interaction.followup.send(f"Now playing: **{title}**")
        await play_next_song(voice_client, guild_id, voice_channel)

# Skip command
@bot.tree.command(name="skip", description="Skip the current song")
async def skip_command(interaction: discord.Interaction):
    if interaction.guild.voice_client and (interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused()):
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("Skipped the current song.")
    else:
        await interaction.response.send_message("No song is currently playing.")

# Pause command
@bot.tree.command(name="pause", description="Pause the currently playing song.")
async def pause(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    # Check if the bot is in a voice channel
    if voice_client is None:
        return await interaction.response.send_message("I'm not in a voice channel.")

    # Check if something is actually playing
    if not voice_client.is_playing():
        return await interaction.response.send_message("Nothing is currently playing.")
    
    # Pause the track
    voice_client.pause()
    await interaction.response.send_message("Playback paused!")

# Stop command
@bot.tree.command(name="stop", description="Stop playback and clear the queue.")
async def stop(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    # Check if the bot is in a voice channel
    if not voice_client or not voice_client.is_connected():
        await interaction.response.send_message("I'm not connected to any voice channel.")
        return

    # Clear the guild's queue
    guild_id_str = str(interaction.guild_id)
    if guild_id_str in SONG_QUEUES:
        SONG_QUEUES[guild_id_str].clear()

    # If something is playing or paused, stop it
    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()

    # Disconnect from the channel
    await interaction.response.send_message("Stopped playback and disconnected!")
    await voice_client.disconnect()

# Resume command
@bot.tree.command(name="resume", description="Resume the currently paused song.")
async def resume(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    # Check if the bot is in a voice channel
    if voice_client is None:
        return await interaction.response.send_message("I'm not in a voice channel.")

    # Check if it's actually paused
    if not voice_client.is_paused():
        return await interaction.response.send_message("I’m not paused right now.")
    
    # Resume playback
    voice_client.resume()
    await interaction.response.send_message("Playback resumed!")

# Play next song in the queue
async def play_next_song(voice_client, guild_id, channel):
    if SONG_QUEUES[guild_id]:
        video_url, title = SONG_QUEUES[guild_id].popleft()

        # If it's a YouTube video URL, extract the stream URL
        if "youtube.com/watch" in video_url:
            ydl_options = {
                "format": "bestaudio[abr<=96]/bestaudio",
                "noplaylist": True,
                "youtube_include_dash_manifest": False,
                "youtube_include_hls_manifest": False,
                "quiet": True,
            }
            
            try:
                result = await search_ytdlp_async(video_url, ydl_options)
                if result and 'url' in result:
                    audio_url = result['url']
                else:
                    print(f"Could not extract stream URL for: {title}")
                    return await play_next_song(voice_client, guild_id, channel)  # Try next song
            except Exception as e:
                print(f"Error extracting stream for {title}: {e}")
                return await play_next_song(voice_client, guild_id, channel)  # Try next song
        else:
            audio_url = video_url  # Already a stream URL

        ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn",
        }

        try:
            source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options, executable="bin\\ffmpeg\\ffmpeg.exe")
            
            # Callback to play the next song after the current one ends
            def after_play(error):
                if error:
                    print(f"Error playing {title}: {error}")
                asyncio.run_coroutine_threadsafe(play_next_song(voice_client, guild_id, channel), bot.loop)

            voice_client.play(source, after=after_play)
            await channel.send(f"Now playing: **{title}**")
            
        except Exception as e:
            print(f"Error creating audio source for {title}: {e}")
            # Try next song
            await play_next_song(voice_client, guild_id, channel)
    
    # If the queue is empty, disconnect
    else:
        await voice_client.disconnect()
        SONG_QUEUES[guild_id] = deque()
        await channel.send("Queue is empty. Disconnected from the voice channel.")



# Run the bot
bot.run(TOKEN)