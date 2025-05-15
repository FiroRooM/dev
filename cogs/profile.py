import discord
from discord import app_commands
from discord.ext import commands
from utils.helper import get_rank_emoji, get_rank_display, get_rank_image_url

class ProfileCog(commands.Cog):
    def __init__(self, bot, db, ROLE_NAMES):
        self.bot = bot
        self.db = db
        self.ROLE_NAMES = ROLE_NAMES

    @app_commands.command(name="register", description="プロフィールを登録します")
    @app_commands.choices(
        rank=[
            app_commands.Choice(name="ノーランク", value="UNRANKED"),
            app_commands.Choice(name="アイアン", value="IRON"),
            app_commands.Choice(name="ブロンズ", value="BRONZE"),
            app_commands.Choice(name="シルバー", value="SILVER"),
            app_commands.Choice(name="ゴールド", value="GOLD"),
            app_commands.Choice(name="プラチナ", value="PLATINUM"),
            app_commands.Choice(name="エメラルド", value="EMERALD"),
            app_commands.Choice(name="ダイヤモンド", value="DIAMOND"),
            app_commands.Choice(name="マスター", value="MASTER"),
            app_commands.Choice(name="グランドマスター", value="GRANDMASTER"),
            app_commands.Choice(name="チャレンジャー", value="CHALLENGER")
        ],
        division=[
            app_commands.Choice(name="4", value="4"),
            app_commands.Choice(name="3", value="3"),
            app_commands.Choice(name="2", value="2"),
            app_commands.Choice(name="1", value="1")
        ],
        main_lane=[
            app_commands.Choice(name="TOP", value="top"),
            app_commands.Choice(name="JG", value="jungle"),
            app_commands.Choice(name="MID", value="mid"),
            app_commands.Choice(name="ADC", value="adc"),
            app_commands.Choice(name="SUP", value="support")
        ]
    )
    async def register(self, interaction: discord.Interaction, summoner_name: str, rank: app_commands.Choice[str], division: app_commands.Choice[str] = None, main_lane: app_commands.Choice[str] = None):
        user_id = str(interaction.user.id)
        if user_id in self.db.users:
            await interaction.response.send_message("既に登録済みです。プロフィールを更新する場合は /update_profile コマンドを使用してください。", ephemeral=True)
            return
        if "#" not in summoner_name:
            await interaction.response.send_message("サモナー名には#を含めてください（例：テスト#JP1）", ephemeral=True)
            return
        if rank.value in ["UNRANKED", "MASTER", "GRANDMASTER", "CHALLENGER"]:
            if division is not None:
                await interaction.response.send_message("このランクではディビジョンを選択できません。", ephemeral=True)
                return
            rank_info = rank.value
        else:
            if division is None:
                await interaction.response.send_message("このランクではディビジョンを選択してください。", ephemeral=True)
                return
            rank_info = f"{rank.value} {division.value}"
        self.db.users[user_id] = {
            'summoner_name': summoner_name,
            'rank_info': rank_info,
            'main_lane': main_lane.value if main_lane else "未設定"
        }
        self.db.save_data()
        embed = discord.Embed(
            title="プロフィール登録完了",
            description=f"登録名: **{summoner_name}**",
            color=discord.Color.green()
        )
        emoji = get_rank_emoji(rank_info)
        rank_display = get_rank_display(rank_info)
        embed.add_field(name="ランク", value=rank_display, inline=False)
        embed.add_field(name="メインレーン", value=self.ROLE_NAMES.get(self.db.users[user_id]['main_lane'], self.db.users[user_id]['main_lane']), inline=False)
        image_url = get_rank_image_url(rank_info)
        if image_url:
            embed.set_thumbnail(url=image_url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="update_profile", description="プロフィール情報を更新します")
    @app_commands.choices(
        rank=[
            app_commands.Choice(name="ノーランク", value="UNRANKED"),
            app_commands.Choice(name="アイアン", value="IRON"),
            app_commands.Choice(name="ブロンズ", value="BRONZE"),
            app_commands.Choice(name="シルバー", value="SILVER"),
            app_commands.Choice(name="ゴールド", value="GOLD"),
            app_commands.Choice(name="プラチナ", value="PLATINUM"),
            app_commands.Choice(name="エメラルド", value="EMERALD"),
            app_commands.Choice(name="ダイヤモンド", value="DIAMOND"),
            app_commands.Choice(name="マスター", value="MASTER"),
            app_commands.Choice(name="グランドマスター", value="GRANDMASTER"),
            app_commands.Choice(name="チャレンジャー", value="CHALLENGER")
        ],
        division=[
            app_commands.Choice(name="4", value="4"),
            app_commands.Choice(name="3", value="3"),
            app_commands.Choice(name="2", value="2"),
            app_commands.Choice(name="1", value="1")
        ],
        main_lane=[
            app_commands.Choice(name="TOP", value="top"),
            app_commands.Choice(name="JG", value="jungle"),
            app_commands.Choice(name="MID", value="mid"),
            app_commands.Choice(name="ADC", value="adc"),
            app_commands.Choice(name="SUP", value="support")
        ]
    )
    async def update_profile(self, interaction: discord.Interaction, summoner_name: str = None, rank: app_commands.Choice[str] = None, division: app_commands.Choice[str] = None, main_lane: app_commands.Choice[str] = None):
        user_id = str(interaction.user.id)
        if user_id not in self.db.users:
            await interaction.response.send_message("先に /register コマンドで登録してください！", ephemeral=True)
            return
        if not summoner_name and not rank and not main_lane:
            await interaction.response.send_message("少なくとも1つのフィールドを更新する必要があります。", ephemeral=True)
            return
        if summoner_name:
            self.db.users[user_id]['summoner_name'] = summoner_name
        if rank:
            rank_info = rank.value
            if rank.value != "UNRANKED" and division:
                rank_info = f"{rank.value} {division.value}"
            self.db.users[user_id]['rank_info'] = rank_info
        if main_lane:
            self.db.users[user_id]['main_lane'] = main_lane.value
        self.db.save_data()
        embed = discord.Embed(
            title="プロフィール更新完了",
            description=f"更新されたプロフィール情報:",
            color=discord.Color.green()
        )
        user_data = self.db.users[user_id]
        rank_info = user_data['rank_info']
        rank_display = get_rank_display(rank_info)
        embed.add_field(name="サモナー名", value=user_data['summoner_name'], inline=False)
        embed.add_field(name="ランク", value=rank_display, inline=False)
        embed.add_field(name="メインレーン", value=self.ROLE_NAMES.get(user_data['main_lane'], user_data['main_lane']), inline=False)
        image_url = get_rank_image_url(rank_info)
        if image_url:
            embed.set_thumbnail(url=image_url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="profile", description="自分のプロフィールを表示します")
    async def profile(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in self.db.users:
            await interaction.response.send_message("先に /register コマンドで登録してください！", ephemeral=True)
            return
        user_data = self.db.users[user_id]
        embed = discord.Embed(
            title=f"プロフィール: {user_data['summoner_name']}",
            color=discord.Color.blue()
        )
        rank_info = user_data['rank_info']
        rank_display = get_rank_display(rank_info)
        embed.add_field(name="ランク", value=rank_display, inline=False)
        embed.add_field(name="メインレーン", value=self.ROLE_NAMES.get(user_data['main_lane'], user_data['main_lane']), inline=False)
        image_url = get_rank_image_url(rank_info)
        if image_url:
            embed.set_thumbnail(url=image_url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="unregister", description="プロフィール情報を削除します")
    async def unregister(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in self.db.users:
            await interaction.response.send_message("プロフィール情報が登録されていません。", ephemeral=True)
            return
        del self.db.users[user_id]
        self.db.save_data()
        await interaction.response.send_message("プロフィール情報を削除しました。", ephemeral=True)

async def setup(bot):
    from utils.db import Database
    from bot import db, ROLE_NAMES
    await bot.add_cog(ProfileCog(bot, db, ROLE_NAMES)) 