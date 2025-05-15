import requests
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List

load_dotenv()
API_KEY = os.getenv('RIOT_API_KEY')
if not API_KEY:
    raise ValueError("RIOT_API_KEYが設定されていません。.envファイルを確認してください。")

REGION = "asia"  # アカウントAPIはasiaリージョンを使用
GAME_REGION = "jp1"  # ゲームデータAPIはjp1リージョンを使用

RIOT_API_BASE_URL = 'https://asia.api.riotgames.com'
RIOT_API_JP_URL = 'https://jp1.api.riotgames.com'

def get_latest_version() -> str:
    """最新のDDragonバージョンを取得"""
    try:
        response = requests.get('https://ddragon.leagueoflegends.com/api/versions.json')
        versions = response.json()
        return versions[0]
    except:
        return '14.1.1'  # フォールバックバージョン

DDRAGON_VERSION = get_latest_version()

def get_summoner_by_riot_id(game_name, tag_line):
    if '#' in tag_line:
        tag_line = tag_line.split('#')[1].strip()
    url = f"https://{REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = {"X-Riot-Token": API_KEY}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return None

def get_summoner_by_puuid(puuid):
    url = f"https://{GAME_REGION}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    headers = {"X-Riot-Token": API_KEY}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return None

def get_league_info(summoner_id):
    url = f"https://{GAME_REGION}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    headers = {"X-Riot-Token": API_KEY}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return None

def get_profile_icon_url(icon_id: int) -> str:
    """プロフィールアイコンのURLを取得"""
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/profileicon/{icon_id}.png" 
