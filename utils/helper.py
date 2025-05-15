RANK_EMOJIS = {
    "IRON": "<:Iron:1338975697749803058>",
    "BRONZE": "<:Bronze:1338975778884288552>",
    "SILVER": "<:Silver:1338975837009088636>",
    "GOLD": "<:Gold:1338975886287831151>",
    "PLATINUM": "<:Platinum:1338975944521551893>",
    "EMERALD": "<:Emerald:1338977548599820349>",
    "DIAMOND": "<:Diamond:1338977749947383929>",
    "UNRANKED": "<:Unranked:1338977764749086801>",
    "MASTER": "<:Master:1368896207094812815>",
    "GRANDMASTER": "<:Grandmaster:1368896224865947658>",
    "CHALLENGER": "<:Challenger:1368896237025099876>"
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

def get_rank_emoji(rank_info):
    key = rank_info.split()[0].upper()
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