import discord
from discord.ext import commands
from discord import app_commands

class AdminCog(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    @app_commands.command(name="db_cleanup", description="存在しないVCのチームデータをクリーンアップ（管理者専用）")
    async def db_cleanup(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("このコマンドは管理者のみ使用できます。", ephemeral=True)
            return
        guild = interaction.guild
        removed = 0
        to_delete = []
        for team_id, team_data in self.db.teams.items():
            vc = guild.get_channel(team_data['voice_channel_id'])
            if vc is None:
                to_delete.append(team_id)
        for team_id in to_delete:
            del self.db.teams[team_id]
            removed += 1
        self.db.save_data()
        await interaction.response.send_message(f"{removed}件のゴミデータを削除しました。", ephemeral=True)

async def setup(bot):
    from utils.db import Database
    from bot import db
    await bot.add_cog(AdminCog(bot, db)) 