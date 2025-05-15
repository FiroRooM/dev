import discord
from discord.ext import commands
from utils.riot_api import get_summoner_by_riot_id, get_summoner_by_puuid, get_league_info, get_profile_icon_url
from utils.helper import RANK_EMOJIS
from typing import Dict, Tuple
import json
import os

class LoLCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'data/summoner_data.json'
        self.summoner_map: Dict[int, Tuple[str, str]] = {}  # user_id: (name, tag)
        self.reverse_summoner_map: Dict[Tuple[str, str], int] = {}  # (name, tag): user_id
        self.RANK_EMOJIS = RANK_EMOJIS  # helper.pyから共通のランク絵文字を使用
        self.load_data()

    def clear_all_data(self):
        """全てのデータを完全にクリアする"""
        self.summoner_map.clear()
        self.reverse_summoner_map.clear()
        self.delete_data_file()
        self.save_data()  # 空のデータを保存して整合性を保つ

    def load_data(self):
        """データファイルからデータを読み込む"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.summoner_map = {int(k): tuple(v) for k, v in data.get('summoner_map', {}).items()}
                    self.reverse_summoner_map = {tuple(k.split('|')): int(v) for k, v in data.get('reverse_map', {}).items()}
        except Exception as e:
            print(f"データ読み込みエラー: {e}")
            self.clear_all_data()

    def save_data(self):
        """現在のデータをファイルに保存する"""
        try:
            os.makedirs('data', exist_ok=True)
            data = {
                'summoner_map': {str(k): list(v) for k, v in self.summoner_map.items()},
                'reverse_map': {f"{k[0]}|{k[1]}": str(v) for k, v in self.reverse_summoner_map.items()}
            }
            # 一時ファイルに書き込んでから移動
            temp_file = f"{self.data_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, self.data_file)
        except Exception as e:
            print(f"データ保存エラー: {e}")
            if os.path.exists(f"{self.data_file}.tmp"):
                try:
                    os.remove(f"{self.data_file}.tmp")
                except:
                    pass

    def delete_data_file(self):
        """データファイルとディレクトリを削除する"""
        try:
            if os.path.exists(self.data_file):
                os.remove(self.data_file)
            if os.path.exists(f"{self.data_file}.tmp"):
                os.remove(f"{self.data_file}.tmp")
            if os.path.exists('data') and not os.listdir('data'):
                try:
                    os.rmdir('data')
                except Exception as e:
                    print(f"データディレクトリ削除エラー: {e}")
        except Exception as e:
            print(f"データファイル削除エラー: {e}")

    def is_registered(self, user_id: int) -> bool:
        """ユーザーが登録済みかどうかを確認する"""
        return user_id in self.summoner_map

    @commands.hybrid_command(name="unregister", description="登録したサモナー情報を削除します")
    async def unregister(self, ctx):
        user_id = ctx.author.id
        if not self.is_registered(user_id):
            await ctx.send("登録されているサモナー情報がありません。", ephemeral=True)
            return

        try:
            name, tag = self.summoner_map[user_id]
            del self.reverse_summoner_map[(name, tag)]
            del self.summoner_map[user_id]
            self.save_data()
            await ctx.send("サモナー情報を削除しました。", ephemeral=True)
        except Exception as e:
            print(f"アカウント削除エラー: {e}")
            # エラー時は完全にクリア
            self.clear_all_data()
            await ctx.send("サモナー情報を削除しました。", ephemeral=True)

    @commands.hybrid_command(name="clean", description="全てのサモナー情報をリセットします")
    @commands.has_permissions(administrator=True)
    async def clean(self, ctx):
        try:
            self.clear_all_data()
            await ctx.send("全てのサモナー情報をリセットしました。", ephemeral=True)
        except Exception as e:
            print(f"データクリーンアップエラー: {e}")
            await ctx.send("データのリセット中にエラーが発生しました。", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        # 起動時にデータを再読み込み
        self.load_data()

    @commands.hybrid_command(name="lol", description="League of Legendsのサモナー名とタグを登録します")
    async def lol(self, ctx, summoner_name: str, tag: str):
        await ctx.defer()
        try:
            # サモナー名・タグの存在確認
            account_info = get_summoner_by_riot_id(summoner_name, tag)
            if not account_info:
                await ctx.send("サモナーが見つかりませんでした。", ephemeral=True)
                return

            game_name = account_info['gameName']
            tag_line = account_info['tagLine']
            summoner_key = (game_name, tag_line)

            # 他のユーザーが既に登録しているか確認
            if summoner_key in self.reverse_summoner_map and self.reverse_summoner_map[summoner_key] != ctx.author.id:
                existing_user = ctx.guild.get_member(self.reverse_summoner_map[summoner_key])
                existing_user_name = existing_user.display_name if existing_user else "別のユーザー"
                await ctx.send(f"このサモナー名は既に {existing_user_name} によって登録されています。", ephemeral=True)
                return

            # 自分が既に別のアカウントを登録しているか確認
            if self.is_registered(ctx.author.id):
                old_name, old_tag = self.summoner_map[ctx.author.id]
                # 同じアカウントの場合は情報を表示
                if old_name == game_name and old_tag == tag_line:
                    await self.display_summoner_info(ctx, game_name, tag_line)
                    return
                
                # 確認メッセージを送信
                confirm_view = discord.ui.View(timeout=60)
                async def confirm_callback(interaction: discord.Interaction):
                    if interaction.user.id != ctx.author.id:
                        await interaction.response.send_message("このボタンは使用できません。", ephemeral=True)
                        return
                    # 古いデータを削除
                    old_key = (old_name, old_tag)
                    if old_key in self.reverse_summoner_map:
                        del self.reverse_summoner_map[old_key]
                    # 新しいアカウントを登録
                    self.summoner_map[ctx.author.id] = (game_name, tag_line)
                    self.reverse_summoner_map[summoner_key] = ctx.author.id
                    self.save_data()
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
            self.save_data()
            await self.display_summoner_info(ctx, game_name, tag_line)

        except Exception as e:
            print(f"アカウント登録エラー: {e}")
            # エラー時はデータをクリア
            self.clear_all_data()
            await ctx.send("アカウント登録中にエラーが発生しました。", ephemeral=True)

    async def display_summoner_info(self, ctx, game_name: str, tag_line: str, edit_message: bool = False):
        try:
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

            # プロフィールアイコンを設定（必ずアイコンを表示）
            try:
                icon_url = get_profile_icon_url(summoner_info['profileIconId'])
                if icon_url:
                    embed.set_thumbnail(url=icon_url)
            except Exception as e:
                print(f"プロフィールアイコン取得エラー: {e}")

            # ランク情報
            league_info = get_league_info(summoner_info['id'])
            if league_info:
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
                        value=f"{rank_emoji} {tier} {rank} ({lp}LP)\n"
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
                        value=f"{rank_emoji} {tier} {rank} ({lp}LP)\n"
                              f"戦績: {wins}勝 {losses}敗 (勝率: {winrate:.1f}%)",
                        inline=False
                    )
            else:
                embed.add_field(name="ランク情報", value="ランク情報なし", inline=False)

            if edit_message:
                await ctx.response.edit_message(content=None, embed=embed, view=None)
            else:
                await ctx.send(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"サモナー情報表示エラー: {e}")
            await ctx.send("サモナー情報の表示中にエラーが発生しました。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(LoLCog(bot)) 
