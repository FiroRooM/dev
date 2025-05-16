import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

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

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f"Bot ID: {bot.user.id}")
    print(f"参加しているサーバー:")
    for guild in bot.guilds:
        print(f"- {guild.name} (ID: {guild.id})")
    
    try:
        # 起動時のステータス設定（赤色のみ）
        await bot.change_presence(status=discord.Status.do_not_disturb)
        print("ステータスを設定しました")
        
        # RecruitmentCogを読み込み
        print("RecruitmentCogを読み込み中...")
        await bot.load_extension('cogs.recruitment')
        print("Recruitment cog loaded successfully!")
        
        # Cogが正しく読み込まれたか確認
        if 'RecruitmentCog' in [cog.__class__.__name__ for cog in bot.cogs.values()]:
            print("RecruitmentCogが正常に読み込まれました")
        else:
            print("警告: RecruitmentCogが読み込まれていません")
        
        # コマンドを同期
        print("コマンドを同期中...")
        await bot.tree.sync()
        print("Commands synced successfully!")
        
    except Exception as e:
        print(f"Error during startup: {e}")
        import traceback
        print(traceback.format_exc())
        # エラーが発生した場合でもBotは継続して動作
        if not any(cog.lower() == 'recruitment' for cog in bot.cogs):
            print("Warning: RecruitmentCog failed to load. Some features may be unavailable.")

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

if __name__ == "__main__":
    bot.run(TOKEN)
