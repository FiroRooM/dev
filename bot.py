import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from utils.db import Database

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATA_PATH = os.getenv('DATA_PATH', '/data/data.json')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

db = Database(DATA_PATH)

ROLE_NAMES = {
    "top": "TOP",
    "jungle": "JG",
    "mid": "MID",
    "adc": "ADC",
    "support": "SUP",
    "fill": "Autofill"
}

GAME_TYPES = {
    "ranked": "ランク",
    "normal": "ノーマル"
}

@tasks.loop(minutes=20)
async def keep_alive():
    print("Bot is alive - Preventing sleep")

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    await bot.change_presence(status=discord.Status.dnd)
    keep_alive.start()
    # Cogの同期は各Cogのsetupで行う

async def load_cogs():
    await bot.load_extension('cogs.profile')
    await bot.load_extension('cogs.team')
    await bot.load_extension('cogs.admin')

if __name__ == "__main__":
    import asyncio
    asyncio.run(load_cogs())
    bot.run(TOKEN)