import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

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

# # on_message: handle incoming messages
# @bot.event
# async def on_message(message):
#     # Prevent the bot from responding to its own messages
#     if message.author == bot.user:
#         return
#     print(f'Message from {message.author}: {message.content}')

# Test slash command
@bot.tree.command(name="ping", description="Says pong!")
async def ping_command(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

bot.run(TOKEN)