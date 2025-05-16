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

RANK_IMAGE_URLS = {
    "IRON": "https://static.wikia.nocookie.net/leagueoflegends/images/f/f8/Season_2023_-_Iron.png/revision/latest?cb=20231007195831",
    "BRONZE": "https://static.wikia.nocookie.net/leagueoflegends/images/c/cb/Season_2023_-_Bronze.png/revision/latest?cb=20231007195824",
    "SILVER": "https://static.wikia.nocookie.net/leagueoflegends/images/c/c4/Season_2023_-_Silver.png/revision/latest?cb=20231007195834",
    "GOLD": "https://static.wikia.nocookie.net/leagueoflegends/images/8/8d/Season_2022_-_Gold.png/revision/latest/scale-to-width-down/250?cb=20220105214225",
    "PLATINUM": "https://static.wikia.nocookie.net/leagueoflegends/images/b/bd/Season_2023_-_Platinum.png/revision/latest/scale-to-width-down/250?cb=20231007195833",
    "EMERALD": "https://static.wikia.nocookie.net/leagueoflegends/images/4/4b/Season_2023_-_Emerald.png/revision/latest/scale-to-width-down/250?cb=20231007195827",
    "DIAMOND": "https://static.wikia.nocookie.net/leagueoflegends/images/3/37/Season_2023_-_Diamond.png/revision/latest?cb=20231007195826",
    "MASTER": "https://support-leagueoflegends.riotgames.com/hc/article_attachments/36726975633427",
    "GRANDMASTER": "https://support-leagueoflegends.riotgames.com/hc/article_attachments/36726975634067",
    "CHALLENGER": "https://support-leagueoflegends.riotgames.com/hc/article_attachments/36727017612179",
    "UNRANKED": "https://static.wikia.nocookie.net/leagueoflegends/images/1/13/Season_2023_-_Unranked.png/revision/latest?cb=20231007211937"
}

def get_rank_emoji(key: str) -> str:
    return RANK_EMOJIS.get(key, "")

def get_rank_display(rank_info):
    emoji = get_rank_emoji(rank_info)
    parts = rank_info.split()
    if len(parts) == 2:
        return f"{emoji} {parts[1]}"
    else:
        return f"{emoji}"

def get_rank_image_url(rank_info):
    key = rank_info.split()[0].upper()
    return RANK_IMAGE_URLS.get(key, "") 
