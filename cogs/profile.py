import discord
from discord.ext import commands
from utils.riot_api import get_summoner_by_riot_id, get_summoner_by_puuid, get_league_info, get_profile_icon_url

class ProfileCog(commands.Cog):
    def __init__(self, bot, *args, **kwargs):
        self.bot = bot

    @commands.hybrid_command(name="profile", description="登録済みサモナーのリアルタイム情報を表示します")
    async def profile(self, ctx):
        await ctx.defer()
        # LoLCogのsummoner_mapからサモナー名・タグを取得
        lol_cog = self.bot.get_cog("LoLCog")
        user_id = ctx.author.id
        if not lol_cog or user_id not in lol_cog.summoner_map:
            await ctx.send("先に /lol コマンドでサモナー名を登録してください。", ephemeral=True)
            return
        summoner_name, tag = lol_cog.summoner_map[user_id]
        # 最新情報をAPIから取得
        account_info = get_summoner_by_riot_id(summoner_name, tag)
        if not account_info:
            await ctx.send("サモナーが見つかりませんでした。", ephemeral=True)
            return
        summoner_info = get_summoner_by_puuid(account_info['puuid'])
        if not summoner_info:
            await ctx.send("サモナー情報の取得に失敗しました。", ephemeral=True)
            return
        league_info = get_league_info(summoner_info['id'])
        display_name = f"{account_info['gameName']}#{account_info['tagLine']}"
        embed = discord.Embed(
            title=f"{display_name} の情報 (リアルタイム)",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=get_profile_icon_url(summoner_info['profileIconId']))
        embed.add_field(name="サモナーレベル", value=str(summoner_info.get('summonerLevel', '不明')), inline=True)
        if league_info:
            for queue in league_info:
                queue_names = {
                    'RANKED_SOLO_5x5': 'ソロランク',
                    'RANKED_FLEX_SR': 'フレックスランク',
                    'RANKED_TFT': 'TFTランク'
                }
                queue_name = queue_names.get(queue['queueType'], queue['queueType'])
                tier = queue['tier']
                rank = queue['rank']
                lp = queue['leaguePoints']
                wins = queue['wins']
                losses = queue['losses']
                winrate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
                embed.add_field(
                    name=queue_name,
                    value=f"{tier} {rank} ({lp}LP)\n{wins}勝 {losses}敗 (勝率: {winrate:.1f}%)",
                    inline=False
                )
        else:
            embed.add_field(name="ランク情報", value="ランク情報なし", inline=False)
        await ctx.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ProfileCog(bot)) 
