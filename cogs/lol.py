import discord
from discord.ext import commands
from utils.riot_api import get_summoner_by_riot_id, get_summoner_by_puuid, get_league_info, get_profile_icon_url

class LoLCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.summoner_map = {}  # user_id: (name, tag)
        self.reverse_summoner_map = {}  # (name, tag): user_id
        self.RANK_EMOJIS = {
            "IRON": "<:Iron:1338975778884288552>",
            "BRONZE": "<:Bronze:1338975778884288552>",
            "SILVER": "<:Silver:1338975778884288552>",
            "GOLD": "<:Gold:1338975778884288552>",
            "PLATINUM": "<:Platinum:1338975778884288552>",
            "DIAMOND": "<:Diamond:1338975778884288552>",
            "MASTER": "<:Master:1338975778884288552>",
            "GRANDMASTER": "<:Grandmaster:1338975778884288552>",
            "CHALLENGER": "<:Challenger:1338975778884288552>"
        }

    @commands.hybrid_command(name="lol", description="League of Legendsのサモナー名とタグを登録します")
    async def lol(self, ctx, summoner_name: str, tag: str):
        await ctx.defer()
        # サモナー名・タグの存在確認のみAPIで行う
        account_info = get_summoner_by_riot_id(summoner_name, tag)
        if not account_info:
            await ctx.send("サモナーが見つかりませんでした。", ephemeral=True)
            return

        game_name = account_info['gameName']
        tag_line = account_info['tagLine']
        summoner_key = (game_name, tag_line)

        # 他のユーザーが既に登録しているか確認
        if summoner_key in self.reverse_summoner_map:
            existing_user_id = self.reverse_summoner_map[summoner_key]
            if existing_user_id != ctx.author.id:
                existing_user = ctx.guild.get_member(existing_user_id)
                existing_user_name = existing_user.display_name if existing_user else "別のユーザー"
                await ctx.send(f"このサモナー名は既に {existing_user_name} によって登録されています。", ephemeral=True)
                return

        # 自分が既に別のアカウントを登録しているか確認
        if ctx.author.id in self.summoner_map:
            old_name, old_tag = self.summoner_map[ctx.author.id]
            # 同じアカウントの場合は早期リターン
            if old_name == game_name and old_tag == tag_line:
                await ctx.send("このアカウントは既に登録されています。", ephemeral=True)
                return
            
            # 確認メッセージを送信
            confirm_view = discord.ui.View(timeout=60)
            async def confirm_callback(interaction: discord.Interaction):
                if interaction.user.id != ctx.author.id:
                    await interaction.response.send_message("このボタンは使用できません。", ephemeral=True)
                    return
                # 古いアカウントの逆引きを削除
                old_key = (old_name, old_tag)
                if old_key in self.reverse_summoner_map:
                    del self.reverse_summoner_map[old_key]
                # 新しいアカウントを登録
                self.summoner_map[ctx.author.id] = (game_name, tag_line)
                self.reverse_summoner_map[summoner_key] = ctx.author.id
                await self.display_summoner_info(interaction, game_name, tag_line, edit_message=True)

            async def cancel_callback(interaction: discord.Interaction):
                if interaction.user.id != ctx.author.id:
                    await interaction.response.send_message("このボタンは使用できません。", ephemeral=True)
                    return
                await interaction.response.edit_message(content="アカウントの更新をキャンセルしました。", view=None)

            confirm_button = discord.ui.Button(label="更新する", style=discord.ButtonStyle.primary)
            cancel_button = discord.ui.Button(label="キャンセル", style=discord.ButtonStyle.secondary)
            confirm_button.callback = confirm_callback
            cancel_button.callback = cancel_callback
            confirm_view.add_item(confirm_button)
            confirm_view.add_item(cancel_button)

            await ctx.send(
                f"既に {old_name}#{old_tag} を登録済みです。\n"
                f"新しいアカウント {game_name}#{tag_line} に更新しますか？",
                view=confirm_view,
                ephemeral=True
            )
            return

        # 新規登録
        self.summoner_map[ctx.author.id] = (game_name, tag_line)
        self.reverse_summoner_map[summoner_key] = ctx.author.id
        await self.display_summoner_info(ctx, game_name, tag_line)

    async def display_summoner_info(self, ctx, game_name: str, tag_line: str, edit_message: bool = False):
        account_info = get_summoner_by_riot_id(game_name, tag_line)
        if not account_info:
            await ctx.send("サモナー情報の取得に失敗しました。", ephemeral=True)
            return
        
        summoner_info = get_summoner_by_puuid(account_info['puuid'])
        if not summoner_info:
            await ctx.send("サモナー情報の取得に失敗しました。", ephemeral=True)
            return

        embed = discord.Embed(
            title="=== サモナー情報 ===",
            color=discord.Color.blue()
        )
        
        # サモナー基本情報
        embed.add_field(
            name="名前",
            value=f"{account_info['gameName']}#{account_info['tagLine']}",
            inline=False
        )
        embed.add_field(
            name="レベル",
            value=str(summoner_info['summonerLevel']),
            inline=False
        )
        embed.set_thumbnail(url=get_profile_icon_url(summoner_info['profileIconId']))

        # ランク情報
        league_info = get_league_info(summoner_info['id'])
        if league_info:
            embed.add_field(name="\n=== ランク情報 ===", value="", inline=False)
            
            # ソロランク情報
            solo_rank = next((q for q in league_info if q['queueType'] == 'RANKED_SOLO_5x5'), None)
            if solo_rank:
                tier = solo_rank['tier']
                rank = solo_rank['rank']
                lp = solo_rank['leaguePoints']
                wins = solo_rank['wins']
                losses = solo_rank['losses']
                winrate = (wins / (wins + losses)) * 100 if wins + losses > 0 else 0
                
                rank_emoji = self.RANK_EMOJIS.get(tier, "")
                embed.add_field(
                    name="ソロランク",
                    value=f"ランク: {rank_emoji} {tier} {rank} ({lp}LP)\n"
                          f"戦績: {wins}勝 {losses}敗 (勝率: {winrate:.1f}%)",
                    inline=False
                )

            # フレックスランク情報
            flex_rank = next((q for q in league_info if q['queueType'] == 'RANKED_FLEX_SR'), None)
            if flex_rank:
                tier = flex_rank['tier']
                rank = flex_rank['rank']
                lp = flex_rank['leaguePoints']
                wins = flex_rank['wins']
                losses = flex_rank['losses']
                winrate = (wins / (wins + losses)) * 100 if wins + losses > 0 else 0
                
                rank_emoji = self.RANK_EMOJIS.get(tier, "")
                embed.add_field(
                    name="フレックスランク",
                    value=f"ランク: {rank_emoji} {tier} {rank} ({lp}LP)\n"
                          f"戦績: {wins}勝 {losses}敗 (勝率: {winrate:.1f}%)",
                    inline=False
                )
        else:
            embed.add_field(name="ランク情報", value="ランク情報なし", inline=False)

        if edit_message:
            await ctx.response.edit_message(content=None, embed=embed, view=None)
        else:
            await ctx.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LoLCog(bot)) 
