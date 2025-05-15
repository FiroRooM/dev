import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.helper import get_rank_display, get_rank_image_url, get_rank_emoji
from utils.riot_api import get_summoner_by_riot_id, get_summoner_by_puuid, get_league_info, get_profile_icon_url
import asyncio
from typing import Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class Team:
    creator_id: str
    purpose: str
    voice_channel_id: int
    members: Dict[str, str]
    created_at: str
    recruitment_count: str
    message_id: int = None

class TeamRecruitmentView(discord.ui.View):
    def __init__(self, team_id: str, voice_channel: discord.VoiceChannel, cog):
        super().__init__(timeout=None)
        self.team_id = team_id
        self.voice_channel = voice_channel
        self.cog = cog
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
        if self.team_id not in self.cog.teams:
            await interaction.response.send_message("このチーム募集は既に終了しています。", ephemeral=True)
            return
        if user_id not in self.cog.teams[self.team_id].members:
            role_view = RoleSelectionView(self.team_id, self.voice_channel, self.cog)
            await interaction.response.send_message("ロールを選択してください:", view=role_view, ephemeral=True)
            return
        # 参加予定リストに追加
        self.cog.pending_joins[user_id] = {
            'team_id': self.team_id,
            'voice_channel': self.voice_channel,
            'timestamp': datetime.utcnow()
        }
        await interaction.response.send_message("VCに参加すると自動で移動します。", ephemeral=True)

    async def show_members_button(self, interaction: discord.Interaction):
        if self.team_id not in self.cog.teams:
            await interaction.response.send_message("このチーム募集は既に終了しています。", ephemeral=True)
            return
        team_data = self.cog.teams[self.team_id]
        embed = discord.Embed(
            title="チームメンバー",
            color=discord.Color.blue()
        )
        for member_id, role in team_data.members.items():
            member = interaction.guild.get_member(int(member_id))
            member_name = member.display_name if member else "不明"
            embed.add_field(
                name=f"{member_name} ({self.cog.ROLE_NAMES.get(role, role)})",
                value=f"ロール: {self.cog.ROLE_NAMES.get(role, role)}",
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
    def __init__(self, team_id: str, voice_channel: discord.VoiceChannel, cog):
        super().__init__()
        self.team_id = team_id
        self.voice_channel = voice_channel
        self.cog = cog

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
        if self.team_id not in self.cog.teams:
            await interaction.response.send_message("このチーム募集は既に終了しています。", ephemeral=True)
            return
        self.cog.teams[self.team_id].members[user_id] = role
        await interaction.response.send_message(f"チームに参加しました！ロール: **{self.cog.ROLE_NAMES[role]}**", ephemeral=True)
        # 参加予定リストに追加
        self.cog.pending_joins[user_id] = {
            'team_id': self.team_id,
            'voice_channel': self.voice_channel,
            'timestamp': datetime.utcnow()
        }
        await interaction.followup.send("VCに参加すると自動で移動します。", ephemeral=True)

class TeamCog(commands.Cog):
    def __init__(self, bot, ROLE_NAMES, GAME_TYPES):
        self.bot = bot
        self.ROLE_NAMES = ROLE_NAMES
        self.GAME_TYPES = GAME_TYPES
        self.teams: Dict[str, Team] = {}
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
        user_id = interaction.user.id

        # 既存のVCを確認
        for team in self.teams.values():
            if str(team.creator_id) == str(user_id):
                await interaction.response.send_message("既にチーム募集を作成しています。新しく作成する前に、既存の募集を終了してください。", ephemeral=True)
                return

        # LoLCogからサモナー情報を取得
        lol_cog = self.bot.get_cog("LoLCog")
        if not lol_cog:
            await interaction.response.send_message("LoLCogが読み込まれていません。", ephemeral=True)
            return

        if not hasattr(lol_cog, 'summoner_map') or user_id not in lol_cog.summoner_map:
            await interaction.response.send_message("先に /lol コマンドでサモナー名を登録してください。", ephemeral=True)
            return

        summoner_name, tag = lol_cog.summoner_map[user_id]
        
        try:
            # Riot APIから最新サモナー情報取得
            account_info = get_summoner_by_riot_id(summoner_name, tag)
            if not account_info:
                await interaction.response.send_message("サモナー情報の取得に失敗しました。", ephemeral=True)
                return

            summoner_info = get_summoner_by_puuid(account_info['puuid'])
            if not summoner_info:
                await interaction.response.send_message("サモナー情報の取得に失敗しました。", ephemeral=True)
                return

            league_info = get_league_info(summoner_info['id'])
            
            # ソロランクを優先
            rank_display = "不明"
            rank_emoji = ""
            if league_info:
                solo = next((q for q in league_info if q['queueType'] == 'RANKED_SOLO_5x5'), None)
                if solo:
                    tier = solo['tier']
                    rank = solo['rank']
                    rank_display = f"{tier} {rank}"
                    rank_emoji = lol_cog.RANK_EMOJIS.get(tier, "")
                else:
                    q = league_info[0]
                    tier = q['tier']
                    rank = q['rank']
                    rank_display = f"{tier} {rank}"
                    rank_emoji = lol_cog.RANK_EMOJIS.get(tier, "")

            display_name = f"{account_info['gameName']}#{account_info['tagLine']}"

            # VCチャンネル作成
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

            team_id = f"team_{len(self.teams) + 1}"
            team = Team(
                creator_id=str(user_id),
                purpose=purpose.value,
                voice_channel_id=voice_channel.id,
                members={str(user_id): main_lane.value},
                created_at=datetime.utcnow().isoformat(),
                recruitment_count=recruitment_count.value
            )
            self.teams[team_id] = team

            embed = discord.Embed(
                title=f"チーム募集: {self.GAME_TYPES.get(purpose.value, purpose.name)}ゲーム",
                description=f"作成者: {interaction.user.mention} ({display_name})",
                color=discord.Color.green()
            )

            if rank_emoji:
                embed.add_field(name="作成者のランク", value=f"{rank_emoji} {rank_display}", inline=False)
            else:
                embed.add_field(name="作成者のランク", value=rank_display, inline=False)

            embed.add_field(name="作成者のロール", value=self.ROLE_NAMES[main_lane.value], inline=False)
            embed.add_field(name="募集人数", value="制限なし" if recruitment_count.value == "0" else f"{recruitment_count.value}人", inline=False)
            embed.add_field(name="ボイスチャンネル", value=voice_channel.mention, inline=False)

            # プロフィールアイコンを設定
            icon_url = get_profile_icon_url(summoner_info['profileIconId'])
            embed.set_thumbnail(url=icon_url)

            view = TeamRecruitmentView(team_id, voice_channel, self)
            await interaction.response.send_message(embed=embed, view=view)
            sent_message = await interaction.original_response()
            self.teams[team_id].message_id = sent_message.id

        except Exception as e:
            print(f"チーム作成エラー: {e}")
            if 'voice_channel' in locals():
                await voice_channel.delete()
            await interaction.response.send_message("チーム作成中にエラーが発生しました。", ephemeral=True)

    @tasks.loop(seconds=30)
    async def check_empty_vcs(self):
        await self.bot.wait_until_ready()
        current_time = datetime.utcnow()
        for team_id, team in list(self.teams.items()):
            voice_channel = self.bot.get_channel(team.voice_channel_id)
            if voice_channel:
                created_at = datetime.fromisoformat(team.created_at)
                time_diff = (current_time - created_at).total_seconds()
                if len(voice_channel.members) == 0 and time_diff > 300:
                    print(f"VC {voice_channel.name} を削除します。作成から {time_diff} 秒経過")
                    await voice_channel.delete()
                    del self.teams[team_id]

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
            is_team_vc = any(team_data.voice_channel_id == before.channel.id for team_data in self.teams.values())
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
            for team_id, team_data in list(self.teams.items()):
                if team_data.voice_channel_id == channel.id:
                    message_id = team_data.message_id
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
                                view = TeamRecruitmentView(team_id, channel, self)
                                for item in view.children:
                                    item.disabled = True
                                embed = msg.embeds[0]
                                embed.description = (embed.description or "") + "\n\n**この募集は終了しました**"
                                await msg.edit(embed=embed, view=view)
                        except Exception as e:
                            print(f"メッセージ更新エラー: {e}")
                    del self.teams[team_id]
                    print(f"チームデータ {team_id} を削除しました。")
                    break
            await channel.delete()
            print(f"VC {channel.name} の削除が完了しました。")
        except discord.Forbidden as e:
            print(f"VC削除権限エラー: {e}")
        except Exception as e:
            print(f"VC削除エラー: {e}")

async def setup(bot):
    from bot import ROLE_NAMES, GAME_TYPES
    await bot.add_cog(TeamCog(bot, ROLE_NAMES, GAME_TYPES)) 
