import discord
from discord.ext import commands
from utils.riot_api import get_summoner_by_riot_id, get_summoner_by_puuid, get_league_info, get_profile_icon_url

class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="profile", description="登録済みサモナーのリアルタイム情報を表示します")
    async def profile(self, ctx):
        await ctx.defer()
        # LoLCogのsummoner_mapからサモナー名・タグを取得
        lol_cog = self.bot.get_cog("LoLCog")
        if not lol_cog:
            await ctx.send("LoLCogが読み込まれていません。", ephemeral=True)
            return

        user_id = ctx.author.id
        if user_id not in lol_cog.summoner_map:
            await ctx.send("先に /lol コマンドでサモナー名を登録してください。", ephemeral=True)
            return

        summoner_name, tag = lol_cog.summoner_map[user_id]
        await lol_cog.display_summoner_info(ctx, summoner_name, tag)

async def setup(bot):
    await bot.add_cog(ProfileCog(bot)) 
