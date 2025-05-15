import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

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
    # コマンドを同期
    print("コマンドを同期中...")
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)}個のコマンドを同期しました。")
    except Exception as e:
        print(f"コマンド同期エラー: {e}")

# 開発用: コマンドを特定のギルドにのみ同期
@bot.command()
@commands.is_owner()
async def sync_guild(ctx):
    print(f"ギルド {ctx.guild.name} のコマンドを同期中...")
    try:
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"{len(synced)}個のコマンドを同期しました。")
    except Exception as e:
        await ctx.send(f"コマンド同期エラー: {e}")

# 開発用: グローバルにコマンドを同期
@bot.command()
@commands.is_owner()
async def sync_global(ctx):
    print("グローバルコマンドを同期中...")
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"{len(synced)}個のコマンドをグローバルに同期しました。")
    except Exception as e:
        await ctx.send(f"コマンド同期エラー: {e}")

async def load_cogs():
    await bot.load_extension('cogs.profile')
    await bot.load_extension('cogs.team')
    await bot.load_extension('cogs.lol')

if __name__ == "__main__":
    import asyncio
    async def main():
        await load_cogs()
        await bot.start(TOKEN)
    asyncio.run(main())
