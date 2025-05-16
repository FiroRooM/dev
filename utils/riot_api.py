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

def get_summoner_by_riot_id(game_name: str, tag_line: str) -> Optional[Dict]:
    """RiotIDからサモナー情報を取得"""
    url = f"{RIOT_API_BASE_URL}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    response = requests.get(url, headers={"X-Riot-Token": API_KEY})
    if response.status_code == 200:
        return response.json()
    return None

def get_summoner_by_puuid(puuid: str) -> Optional[Dict]:
    """PUUIDからサモナー情報を取得"""
    url = f"{RIOT_API_JP_URL}/lol/summoner/v4/summoners/by-puuid/{puuid}"
    response = requests.get(url, headers={"X-Riot-Token": API_KEY})
    if response.status_code == 200:
        return response.json()
    return None

def get_league_info(summoner_id: str) -> Optional[List[Dict]]:
    """サモナーIDからランク情報を取得"""
    url = f"{RIOT_API_JP_URL}/lol/league/v4/entries/by-summoner/{summoner_id}"
    response = requests.get(url, headers={"X-Riot-Token": API_KEY})
    if response.status_code == 200:
        return response.json()
    return None

def get_tft_league_info(summoner_id: str) -> Optional[List[Dict]]:
    """サモナーIDからTFTのランク情報を取得"""
    url = f"{RIOT_API_JP_URL}/tft/league/v1/entries/by-summoner/{summoner_id}"
    response = requests.get(url, headers={"X-Riot-Token": API_KEY})
    if response.status_code == 200:
        return response.json()
    return None

def get_profile_icon_url(icon_id: int) -> str:
    """プロフィールアイコンのURLを取得"""
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/profileicon/{icon_id}.png" 
