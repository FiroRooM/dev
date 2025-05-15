import discord
from discord.ext import commands
from utils.riot_api import get_summoner_by_riot_id

class LoLCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.summoner_map = {}  # user_id: (name, tag)
        self.reverse_summoner_map = {}  # (name, tag): user_id

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
                await interaction.response.edit_message(content=f"サモナー名を {game_name}#{tag_line} に更新しました。", view=None)

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
        await ctx.send(f"サモナー名: {game_name}#{tag_line} を登録しました。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(LoLCog(bot)) 
