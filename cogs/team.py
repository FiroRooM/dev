import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.helper import get_rank_display, get_rank_image_url
import asyncio

class TeamRecruitmentView(discord.ui.View):
    def __init__(self, team_id, voice_channel, cog, db, ROLE_NAMES):
        super().__init__(timeout=None)
        self.team_id = team_id
        self.voice_channel = voice_channel
        self.cog = cog  # TeamCogインスタンス
        self.db = db
        self.ROLE_NAMES = ROLE_NAMES
        self.add_item(discord.ui.Button(
            label="チームに参加",
            style=discord.ButtonStyle.green,
            custom_id=f"persistent:team:join:{team_id}"
        ))
        self.add_item(discord.ui.Button(
            label="メンバー表示",
            style=discord.ButtonStyle.blurple,
            custom_id=f"persistent:team:show:{team_id}"
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith(f"persistent:team:join:{self.team_id}"):
            await self.join_button(interaction)
            return False
        elif custom_id.startswith(f"persistent:team:show:{self.team_id}"):
            await self.show_members_button(interaction)
            return False
        return True

    async def join_button(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in self.db.users:
            await interaction.response.send_message("最初に /register コマンドで登録する必要があります！", ephemeral=True)
            return
        if self.team_id not in self.db.teams:
            await interaction.response.send_message("このチーム募集は既に終了しています。", ephemeral=True)
            return
        if user_id not in self.db.teams[self.team_id]['members']:
            role_view = RoleSelectionView(self.team_id, self.voice_channel, self.cog, self.db, self.ROLE_NAMES)
            await interaction.response.send_message("ロールを選択してください:", view=role_view, ephemeral=True)
            return
        # 参加予定リストに追加
        self.cog.pending_joins[user_id] = {
            'team_id': self.team_id,
            'voice_channel': self.voice_channel,
            'timestamp': discord.utils.utcnow()
        }
        await interaction.response.send_message("VCに参加すると自動で移動します。", ephemeral=True)

    async def show_members_button(self, interaction: discord.Interaction):
        if self.team_id not in self.db.teams:
            await interaction.response.send_message("このチーム募集は既に終了しています。", ephemeral=True)
            return
        team_data = self.db.teams[self.team_id]
        embed = discord.Embed(
            title="チームメンバー",
            color=discord.Color.blue()
        )
        for member_id, role in team_data['members'].items():
            if member_id in self.db.users:
                user_data = self.db.users[member_id]
                member = interaction.guild.get_member(int(member_id))
                member_name = member.display_name if member else "不明"
                rank_info = user_data['rank_info']
                rank_display = get_rank_display(rank_info)
                embed.add_field(
                    name=f"{member_name} ({self.ROLE_NAMES.get(role, role)})",
                    value=f"サモナー名: {user_data['summoner_name']}\nランク: {rank_display}",
                    inline=False
                )
        voice_channel = self.voice_channel
        if voice_channel:
            vc_members = [m.display_name for m in voice_channel.members]
            if vc_members:
                embed.add_field(name="現在VC参加中", value="\n".join(vc_members), inline=False)
            else:
                embed.add_field(name="現在VC参加中", value="誰も参加していません", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RoleSelectionView(discord.ui.View):
    def __init__(self, team_id, voice_channel, cog, db, ROLE_NAMES):
        super().__init__()
        self.team_id = team_id
        self.voice_channel = voice_channel
        self.cog = cog  # TeamCogインスタンス
        self.db = db
        self.ROLE_NAMES = ROLE_NAMES

    @discord.ui.button(label="TOP", style=discord.ButtonStyle.primary)
    async def top_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.join_team(interaction, "top")

    @discord.ui.button(label="JG", style=discord.ButtonStyle.primary)
    async def jungle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.join_team(interaction, "jungle")

    @discord.ui.button(label="MID", style=discord.ButtonStyle.primary)
    async def mid_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.join_team(interaction, "mid")

    @discord.ui.button(label="ADC", style=discord.ButtonStyle.primary)
    async def adc_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.join_team(interaction, "adc")

    @discord.ui.button(label="SUP", style=discord.ButtonStyle.primary)
    async def support_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.join_team(interaction, "support")

    @discord.ui.button(label="Autofill", style=discord.ButtonStyle.secondary)
    async def fill_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.join_team(interaction, "fill")

    async def join_team(self, interaction: discord.Interaction, role):
        user_id = str(interaction.user.id)
        if self.team_id not in self.db.teams:
            await interaction.response.send_message("このチーム募集は既に終了しています。", ephemeral=True)
            return
        self.db.teams[self.team_id]['members'][user_id] = role
        self.db.save_data()
        await interaction.response.send_message(f"チームに参加しました！ロール: **{self.ROLE_NAMES.get(role, role)}**", ephemeral=True)
        # 参加予定リストに追加
        self.cog.pending_joins[user_id] = {
            'team_id': self.team_id,
            'voice_channel': self.voice_channel,
            'timestamp': discord.utils.utcnow()
        }
        await interaction.followup.send("VCに参加すると自動で移動します。", ephemeral=True)

class TeamCog(commands.Cog):
    def __init__(self, bot, db, ROLE_NAMES, GAME_TYPES):
        self.bot = bot
        self.db = db
        self.ROLE_NAMES = ROLE_NAMES
        self.GAME_TYPES = GAME_TYPES
        self.check_empty_vcs.start()
        self.bot.add_listener(self.on_voice_state_update)
        self.pending_joins = {}  # 参加予定ユーザーを管理する辞書

    @app_commands.command(name="create", description="チーム募集を作成します")
    @app_commands.choices(
        purpose=[
            app_commands.Choice(name="ランク", value="ranked"),
            app_commands.Choice(name="ノーマル", value="normal"),
            app_commands.Choice(name="その他モード", value="other")
        ],
        main_lane=[
            app_commands.Choice(name="TOP", value="top"),
            app_commands.Choice(name="JG", value="jungle"),
            app_commands.Choice(name="MID", value="mid"),
            app_commands.Choice(name="ADC", value="adc"),
            app_commands.Choice(name="SUP", value="support"),
            app_commands.Choice(name="Autofill", value="fill")
        ],
        recruitment_count=[
            app_commands.Choice(name="1人", value="1"),
            app_commands.Choice(name="2人", value="2"),
            app_commands.Choice(name="3人", value="3"),
            app_commands.Choice(name="4人", value="4"),
            app_commands.Choice(name="5人", value="5"),
            app_commands.Choice(name="制限なし", value="0")
        ]
    )
    async def create_team(self, interaction: discord.Interaction, purpose: app_commands.Choice[str], main_lane: app_commands.Choice[str], recruitment_count: app_commands.Choice[str]):
        user_id = str(interaction.user.id)
        allowed_channels = {
            "ranked": 1368909351791890532,
            "normal": 1368907113954279526,
            "other": 1368909399162224691
        }
        if interaction.channel.id != allowed_channels[purpose.value]:
            await interaction.response.send_message("このモードはこのチャンネルでのみ使用できます。", ephemeral=True)
            return
        if user_id not in self.db.users:
            await interaction.response.send_message("先に /register コマンドで登録してください！", ephemeral=True)
            return
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="チームボイスチャンネル")
        if not category:
            try:
                category = await guild.create_category("チームボイスチャンネル")
            except discord.Forbidden:
                await interaction.response.send_message("チャンネルを作成する権限がありません。管理者に連絡してください。", ephemeral=True)
                return
        channel_name = f"{interaction.user.display_name}の{self.GAME_TYPES.get(purpose.value, purpose.name)}チーム"
        user_limit = None if recruitment_count.value == "0" else int(recruitment_count.value) + 1
        try:
            voice_channel = await guild.create_voice_channel(name=channel_name, category=category, user_limit=user_limit)
        except discord.Forbidden:
            await interaction.response.send_message("ボイスチャンネルを作成する権限がありません。管理者に連絡してください。", ephemeral=True)
            return
        team_id = f"team_{len(self.db.teams) + 1}"
        self.db.teams[team_id] = {
            'creator_id': user_id,
            'purpose': purpose.value,
            'voice_channel_id': voice_channel.id,
            'members': {user_id: main_lane.value},
            'created_at': discord.utils.utcnow().isoformat(),
            'recruitment_count': recruitment_count.value
        }
        self.db.save_data()
        user_data = self.db.users[user_id]
        embed = discord.Embed(
            title=f"チーム募集: {self.GAME_TYPES.get(purpose.value, purpose.name)}ゲーム",
            description=f"作成者: {interaction.user.mention} ({user_data['summoner_name']})",
            color=discord.Color.green()
        )
        rank_display = get_rank_display(user_data['rank_info'])
        embed.add_field(name="作成者のランク", value=rank_display, inline=False)
        embed.add_field(name="作成者のロール", value=self.ROLE_NAMES[main_lane.value], inline=False)
        embed.add_field(name="募集人数", value="制限なし" if recruitment_count.value == "0" else f"{recruitment_count.value}人", inline=False)
        embed.add_field(name="ボイスチャンネル", value=voice_channel.mention, inline=False)
        image_url = get_rank_image_url(user_data['rank_info'])
        if image_url:
            embed.set_thumbnail(url=image_url)
        view = TeamRecruitmentView(team_id, voice_channel, self, self.db, self.ROLE_NAMES)
        response = await interaction.response.send_message(embed=embed, view=view)
        sent_message = await interaction.original_response()
        self.db.teams[team_id]['message_id'] = sent_message.id
        self.db.save_data()

    @tasks.loop(seconds=30)
    async def check_empty_vcs(self):
        await self.bot.wait_until_ready()
        current_time = discord.utils.utcnow()
        for team_id, team_data in list(self.db.teams.items()):
            voice_channel = self.bot.get_channel(team_data['voice_channel_id'])
            if voice_channel:
                created_at = discord.utils.utcnow().fromisoformat(team_data['created_at'])
                time_diff = (current_time - created_at).total_seconds()
                if len(voice_channel.members) == 0 and time_diff > 300:
                    print(f"VC {voice_channel.name} を削除します。作成から {time_diff} 秒経過")
                    await self.delete_team_vc(voice_channel)

    async def on_voice_state_update(self, member, before, after):
        user_id = str(member.id)
        # VCに参加した場合
        if after.channel and user_id in self.pending_joins:
            pending_data = self.pending_joins[user_id]
            try:
                await member.move_to(pending_data['voice_channel'])
                del self.pending_joins[user_id]  # 移動成功したら参加予定リストから削除
            except Exception as e:
                print(f"VC移動エラー: {e}")
        
        # 既存のVC削除処理
        if before.channel and before.channel.category:
            is_team_vc = any(team_data['voice_channel_id'] == before.channel.id for team_data in self.db.teams.values())
            if is_team_vc:
                if len(before.channel.members) == 0:
                    print(f"VC {before.channel.name} が空になりました。5分後に削除を試みます。")
                    await asyncio.sleep(300)
                    channel = before.channel.guild.get_channel(before.channel.id)
                    if channel and len(channel.members) == 0:
                        await self.delete_team_vc(channel)

    async def delete_team_vc(self, channel):
        print(f"VC {channel.name} を削除します。")
        try:
            for team_id, team_data in list(self.db.teams.items()):
                if team_data['voice_channel_id'] == channel.id:
                    message_id = team_data.get('message_id')
                    if message_id:
                        try:
                            recruitment_channel = None
                            for ch in channel.guild.text_channels:
                                if ch.id in [1368909351791890532, 1368907113954279526, 1368909399162224691]:
                                    try:
                                        msg = await ch.fetch_message(message_id)
                                        recruitment_channel = ch
                                        break
                                    except:
                                        continue
                            if recruitment_channel:
                                msg = await recruitment_channel.fetch_message(message_id)
                                view = TeamRecruitmentView(team_id, channel, self, self.db, self.ROLE_NAMES)
                                for item in view.children:
                                    item.disabled = True
                                embed = msg.embeds[0]
                                embed.description = (embed.description or "") + "\n\n**この募集は終了しました**"
                                await msg.edit(embed=embed, view=view)
                        except Exception as e:
                            print(f"メッセージ更新エラー: {e}")
                    del self.db.teams[team_id]
                    self.db.save_data()
                    print(f"チームデータ {team_id} を削除しました。")
                    break
            await channel.delete()
            print(f"VC {channel.name} の削除が完了しました。")
        except discord.Forbidden as e:
            print(f"VC削除権限エラー: {e}")
        except Exception as e:
            print(f"VC削除エラー: {e}")

async def setup(bot):
    from utils.db import Database
    from bot import db, ROLE_NAMES, GAME_TYPES
    await bot.add_cog(TeamCog(bot, db, ROLE_NAMES, GAME_TYPES)) 