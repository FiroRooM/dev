import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Dict, Optional, List
import asyncio
from datetime import datetime, timedelta
from utils.riot_api import get_summoner_by_riot_id, get_summoner_by_puuid, get_league_info, get_tft_league_info
from utils.helper import RANK_EMOJIS, RANK_IMAGE_URLS

class GameModeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="ランク", value="ranked", emoji="🏆"),
            discord.SelectOption(label="ノーマル", value="normal", emoji="🎮"),
            discord.SelectOption(label="TFT", value="tft", emoji="🎲")
        ]
        super().__init__(placeholder="ゲームモードを選択", options=options, custom_id="game_mode_select")

    async def callback(self, interaction: discord.Interaction):
        modal = SummonerModal()
        modal.game_mode = self.values[0]
        await interaction.response.send_modal(modal)

class SummonerModal(discord.ui.Modal, title="サモナー名を入力"):
    summoner_input = discord.ui.TextInput(
        label="サモナー名#タグ",
        placeholder="例: Test#1234",
        required=True
    )

    def __init__(self):
        super().__init__()
        self.game_mode = None

    async def on_submit(self, interaction: discord.Interaction):
        try:
            name, tag = str(self.summoner_input.value).split('#')
            account_info = await interaction.client.loop.run_in_executor(
                None, lambda: get_summoner_by_riot_id(name.strip(), tag.strip())
            )
            
            if not account_info:
                await interaction.response.send_message("サモナーが見つかりませんでした。", ephemeral=True)
                return

            await interaction.response.send_message("アカウントが見つかりました！", ephemeral=True)
            # 次のステップ（人数選択）を表示
            await self.show_team_size_selection(interaction, account_info)
        except ValueError:
            await interaction.response.send_message("正しい形式で入力してください（例: Test#1234）", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)

    async def show_team_size_selection(self, interaction: discord.Interaction, account_info: dict):
        view = TeamSizeView(account_info, self.game_mode)
        await interaction.followup.send("募集人数を選択してください：", view=view, ephemeral=True)

class TeamSizeView(discord.ui.View):
    def __init__(self, account_info: dict, game_mode: str):
        super().__init__(timeout=None)
        self.account_info = account_info
        self.game_mode = game_mode
        
        # ゲームモードに応じてボタンを追加
        if game_mode == 'ranked':
            self.add_item(TeamSizeButton("Duo", 2))
            self.add_item(TeamSizeButton("Flex", 5))
            self.add_item(TeamSizeButton("Unlimited", None))
        elif game_mode == 'normal':
            self.add_item(TeamSizeButton("Duo", 2))
            self.add_item(TeamSizeButton("Trio", 3))
            self.add_item(TeamSizeButton("Squad", 4))
            self.add_item(TeamSizeButton("Flex", 5))
            self.add_item(TeamSizeButton("Unlimited", None))
        else:  # TFT
            self.add_item(TeamSizeButton("Duo", 2))
            self.add_item(TeamSizeButton("Unlimited", None))

class TeamSizeButton(discord.ui.Button):
    def __init__(self, label: str, size: Optional[int]):
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=f"size_{label.lower()}")
        self.size = size

    async def callback(self, interaction: discord.Interaction):
        try:
            print(f"TeamSizeButton callback started - User: {interaction.user}, Size: {self.size}, Label: {self.label}")
            print(f"View info - Account: {self.view.account_info}, Game mode: {self.view.game_mode}")
            
            if self.view.game_mode == 'tft':
                # TFTの場合は直接タイトル入力へ
                modal = TitleModal(
                    self.view.account_info,
                    self.view.game_mode,
                    self.size,
                    self.label,
                    'none'  # TFTの場合はロールを'none'として扱う
                )
                await interaction.response.send_modal(modal)
            else:
                # それ以外の場合はロール選択へ
                view = RoleSelectView(self.view.account_info, self.view.game_mode, self.size, self.label)
                await interaction.response.send_message("ロールを選択してください：", view=view, ephemeral=True)
            
            print("TeamSizeButton callback completed successfully")
        except Exception as e:
            print(f"TeamSizeButton callback error: {e}")
            import traceback
            print(traceback.format_exc())
            if not interaction.response.is_done():
                await interaction.response.send_message("エラーが発生しました。もう一度お試しください。", ephemeral=True)
            else:
                await interaction.followup.send("エラーが発生しました。もう一度お試しください。", ephemeral=True)

class RoleSelectView(discord.ui.View):
    def __init__(self, account_info: dict, game_mode: str, team_size: Optional[int], size_label: str):
        try:
            print(f"Initializing RoleSelectView - Game mode: {game_mode}, Team size: {team_size}, Size label: {size_label}")
            print(f"Account info: {account_info}")
            
            super().__init__(timeout=None)
            self.account_info = account_info
            self.game_mode = game_mode
            self.team_size = team_size
            self.size_label = size_label
            self.add_item(RoleSelect())
            
            print("RoleSelectView initialized successfully")
        except Exception as e:
            print(f"RoleSelectView initialization error: {e}")
            import traceback
            print(traceback.format_exc())
            raise  # 元のエラーを再度発生させる

class RoleSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="TOP", value="top"),
            discord.SelectOption(label="JG", value="jungle"),
            discord.SelectOption(label="MID", value="mid"),
            discord.SelectOption(label="BOT", value="bot"),
            discord.SelectOption(label="SUP", value="support"),
            discord.SelectOption(label="Autofill", value="fill")
        ]
        super().__init__(placeholder="ロールを選択", options=options, custom_id="role_select")

    async def callback(self, interaction: discord.Interaction):
        modal = TitleModal(
            self.view.account_info,
            self.view.game_mode,
            self.view.team_size,
            self.view.size_label,
            self.values[0]
        )
        await interaction.response.send_modal(modal)

# レーン表示用の定義を更新
ROLE_EMOJIS = {
    "top": "TOP",
    "jungle": "JG",
    "mid": "MID",
    "bot": "BOT",
    "support": "SUP",
    "fill": "Autofill"
}

# ランク絵文字の定義を更新
RANK_EMOJIS = {
    "IRON": "<:RankIron:1372722873613484032>",
    "BRONZE": "<:RankBronze:1372722862045360128>",
    "SILVER": "<:RankSilver:1372722879766347776>",
    "GOLD": "<:RankGold:1372722867854880778>",
    "PLATINUM": "<:RankPlatinum:1372722871566467082>",
    "EMERALD": "<:RankEmerald:1372722865732509696>",
    "DIAMOND": "<:RankDiamond:1372722864436133888>",
    "MASTER": "<:RankMaster:1372722869918392320>",
    "GRANDMASTER": "<:RankGrandmaster:1372722869918392320>",
    "CHALLENGER": "<:RankChallenger:1372722860854505472>"
}

class TitleModal(discord.ui.Modal, title="募集タイトルを入力"):
    title_input = discord.ui.TextInput(
        label="タイトル",
        placeholder="例: カジュアルにランク回す",
        required=True,
        max_length=100
    )

    def __init__(self, account_info: dict, game_mode: str, team_size: Optional[int], size_label: str, role: str):
        super().__init__()
        self.account_info = account_info
        self.game_mode = game_mode
        self.team_size = team_size
        self.size_label = size_label
        self.role = role

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("RecruitmentCog")
        if not cog:
            await interaction.response.send_message("エラーが発生しました。", ephemeral=True)
            return

        await cog.create_recruitment(
            interaction,
            self.account_info,
            self.game_mode,
            self.team_size,
            self.size_label,
            self.role,
            str(self.title_input)
        )

class RecruitmentCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vc_check.start()
        self.active_vcs: Dict[int, datetime] = {}  # VC ID: 最後のアクティブ時間
        self.recruitment_messages: Dict[int, int] = {}  # チャンネルID: メッセージID
        self.active_recruitments: Dict[int, discord.Message] = {}  # VC ID: 募集メッセージ
        
        # 既存のチャンネルID
        self.CHANNEL_IDS = {
            'recruitment': 1372707529049637018,
            'ranked': 1368909351791890532,
            'normal': 1368907113954279526,
            'tft': 1368909399162224691
        }
        
        # VCカテゴリID
        self.VC_CATEGORY_ID = 1369008978134171729

    def cog_unload(self):
        self.vc_check.cancel()

    @tasks.loop(seconds=60)
    async def vc_check(self):
        """空のVCを定期的にチェックして削除"""
        current_time = datetime.now()
        for vc_id, last_active in list(self.active_vcs.items()):
            if current_time - last_active > timedelta(minutes=1):
                vc = self.bot.get_channel(vc_id)
                if vc and len(vc.members) == 0:
                    try:
                        await vc.delete()
                        del self.active_vcs[vc_id]
                        # 関連する募集メッセージを更新
                        await self.update_recruitment_message(vc_id)
                    except:
                        pass

    async def update_recruitment_message(self, vc_id: int):
        """VCが削除された時に関連する募集メッセージを更新"""
        # 実装予定: メッセージのタイトルを"募集終了"に変更

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """VCの状態変更を監視"""
        if before.channel != after.channel:
            if before.channel and before.channel.id in self.active_vcs:
                if len(before.channel.members) == 0:
                    self.active_vcs[before.channel.id] = datetime.now()
            if after.channel and after.channel.id in self.active_vcs:
                self.active_vcs[after.channel.id] = datetime.now()

    @commands.Cog.listener()
    async def on_ready(self):
        """Bot起動時の処理"""
        print("RecruitmentCog is ready!")
        await self.setup_persistent_views()  # 永続的なViewを再登録

    async def setup_persistent_views(self):
        """永続的なViewを再登録"""
        try:
            # 募集チャンネルを取得
            recruitment_channel = self.bot.get_channel(self.CHANNEL_IDS['recruitment'])
            if not recruitment_channel:
                print("警告: 募集チャンネルが見つかりません。")
                return

            # 最新の100メッセージを取得
            async for message in recruitment_channel.history(limit=100):
                if message.author == self.bot.user and len(message.embeds) > 0:
                    # 募集開始メッセージを見つけた場合
                    if message.embeds[0].title == "募集を開始":
                        # 新しいViewを作成して既存のメッセージに追加
                        view = discord.ui.View(timeout=None)
                        view.add_item(GameModeSelect())
                        message.view = view
                        await message.edit(view=view)
                        self.recruitment_messages[recruitment_channel.id] = message.id
                        print("募集メッセージのViewを再登録しました。")
                        break

        except Exception as e:
            print(f"永続的なViewの再登録中にエラー: {e}")

    @commands.command(name='setup_recruitment')
    @commands.has_permissions(administrator=True)
    async def setup_recruitment_command(self, ctx):
        """募集チャンネルに初期メッセージを送信するコマンド（管理者のみ使用可能）"""
        try:
            # 募集チャンネルを取得
            recruitment_channel = self.bot.get_channel(self.CHANNEL_IDS['recruitment'])
            if not recruitment_channel:
                await ctx.send("エラー: 募集チャンネルが見つかりません。")
                return

            # 既存のメッセージを削除
            try:
                async for message in recruitment_channel.history(limit=100):
                    if message.author == self.bot.user:
                        await message.delete()
            except Exception as e:
                await ctx.send(f"既存メッセージの削除中にエラー: {e}")

            # 新しいメッセージを送信
            embed = discord.Embed(
                title="募集を開始",
                description="下のボタンから募集を開始できます。\n\n"
                           "**ゲームモード**\n"
                           "🏆 ランク\n"
                           "🎮 ノーマル\n"
                           "🎲 TFT",
                color=discord.Color.blue()
            )
            
            view = discord.ui.View(timeout=None)
            view.add_item(GameModeSelect())
            
            message = await recruitment_channel.send(embed=embed, view=view)
            self.recruitment_messages[recruitment_channel.id] = message.id

        except discord.Forbidden:
            await ctx.send("エラー: Botに必要な権限がありません。")
        except Exception as e:
            await ctx.send(f"エラーが発生しました: {e}")

    async def create_recruitment(
        self,
        interaction: discord.Interaction,
        account_info: dict,
        game_mode: str,
        team_size: Optional[int],
        size_label: str,
        role: str,
        title: str
    ):
        """募集を作成"""
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)

            # 既存のVCをチェック
            for vc_id in list(self.active_vcs.keys()):
                vc = self.bot.get_channel(vc_id)
                if vc and vc.name == f"[{game_mode.upper()}] {interaction.user.display_name}の{size_label}":
                    await interaction.followup.send("既に募集用VCを作成しています。", ephemeral=True)
                    return

            # VCカテゴリを取得
            category = self.bot.get_channel(self.VC_CATEGORY_ID)
            if not category:
                await interaction.followup.send("VCカテゴリが見つかりません。", ephemeral=True)
                return

            vc_name = f"[{game_mode.upper()}] {interaction.user.display_name}の{size_label}"
            vc = await interaction.guild.create_voice_channel(
                name=vc_name,
                category=category,
                user_limit=team_size
            )
            self.active_vcs[vc.id] = datetime.now()

            # サモナー情報を取得
            try:
                summoner_info = await interaction.client.loop.run_in_executor(
                    None, lambda: get_summoner_by_puuid(account_info['puuid'])
                )
                print(f"Summoner info: {summoner_info}")  # デバッグ用

                league_info = await interaction.client.loop.run_in_executor(
                    None, lambda: get_league_info(summoner_info['id'])
                )
                print(f"League info: {league_info}")  # デバッグ用
            except Exception as e:
                print(f"Error fetching summoner info: {e}")
                summoner_info = None
                league_info = None

            # ランク情報を取得
            rank_display = "未設定"
            rank_image = RANK_IMAGE_URLS['UNRANKED']
            if league_info is not None:
                try:
                    if game_mode == 'tft':
                        # TFTのランク情報を取得
                        print(f"Fetching TFT rank for summoner ID: {summoner_info['id']}")  # デバッグ用
                        tft_league_info = await interaction.client.loop.run_in_executor(
                            None, lambda: get_tft_league_info(summoner_info['id'])
                        )
                        print(f"TFT league info: {tft_league_info}")  # デバッグ用

                        if tft_league_info and len(tft_league_info) > 0:
                            tft_rank = tft_league_info[0]  # 最初のランク情報を使用
                            tier = tft_rank['tier']
                            rank = tft_rank['rank']
                            rank_display = f"TFT {tier} {rank}"
                            rank_image = RANK_IMAGE_URLS.get(tier, RANK_IMAGE_URLS['UNRANKED'])
                            print(f"TFT rank found: {rank_display}")
                        else:
                            print("No TFT rank found in response")
                    else:
                        # 通常のソロランク情報を取得
                        solo_rank = next((q for q in league_info if q['queueType'] == 'RANKED_SOLO_5x5'), None)
                        if solo_rank:
                            tier = solo_rank['tier']
                            rank = solo_rank['rank']
                            rank_display = f"{tier} {rank}"
                            rank_image = RANK_IMAGE_URLS.get(tier, RANK_IMAGE_URLS['UNRANKED'])
                            print(f"Solo rank found: {rank_display}")  # デバッグ用
                except Exception as e:
                    print(f"Error processing rank info: {e}")
                    print(f"Full error details: ", exc_info=True)  # より詳細なエラー情報

            # 募集メッセージを作成
            try:
                embed = discord.Embed(
                    title=title,
                    color=discord.Color.blue()
                )
                
                # サムネイルの設定
                if rank_image:
                    try:
                        embed.set_thumbnail(url=rank_image)
                    except Exception as e:
                        print(f"Error setting thumbnail: {e}")

                embed.add_field(
                    name="作成者",
                    value=f"{interaction.user.mention} ({account_info['gameName']}#{account_info['tagLine']})",
                    inline=False
                )
                embed.add_field(name="作成者のランク", value=rank_display, inline=False)
                if game_mode != 'tft' and role != 'none':  # TFTまたはロールが'none'の場合はロール表示をスキップ
                    embed.add_field(name="作成者のロール", value=f"{ROLE_EMOJIS.get(role, '')}", inline=False)
                embed.add_field(name="募集人数", value=f"{team_size if team_size else '制限なし'}人", inline=False)
                embed.add_field(name="ボイスチャンネル", value=vc.mention, inline=False)

                # 募集チャンネルに送信
                channel_id = self.CHANNEL_IDS.get(game_mode)
                if channel_id:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        message = await channel.send(embed=embed)
                        self.active_recruitments[vc.id] = message
                        await interaction.followup.send("募集を作成しました！", ephemeral=True)
                    else:
                        raise ValueError("募集チャンネルが見つかりませんでした。")
                else:
                    raise ValueError("対応する募集チャンネルが設定されていません。")

            except Exception as e:
                print(f"Error creating recruitment message: {e}")
                if 'vc' in locals():
                    try:
                        await vc.delete()
                    except:
                        pass
                await interaction.followup.send("募集の作成中にエラーが発生しました。", ephemeral=True)

        except Exception as e:
            print(f"募集作成エラー: {e}")
            await interaction.followup.send("募集の作成中にエラーが発生しました。", ephemeral=True)
            if 'vc' in locals():
                try:
                    await vc.delete()
                except:
                    pass

async def setup(bot):
    await bot.add_cog(RecruitmentCog(bot)) 
