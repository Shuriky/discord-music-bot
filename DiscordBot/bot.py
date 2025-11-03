import os
import discord
import re
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import yt_dlp
import asyncio

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

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
    await interaction.response.send_message(f"Playing {song_query} (Give it a few seconds to load the audio)")

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

    ffmpeg_options = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", # Handle stream reconnections
        "options": "-vn", # Audio options
    }

    # Play the audio
    source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options, executable="bin\\ffmpeg\\ffmpeg.exe")
    voice_client.play(source)


bot.run(TOKEN)