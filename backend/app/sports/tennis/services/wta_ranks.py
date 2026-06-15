import re
import json
import requests
from pathlib import Path

base_dir = Path(__file__).parent.parent
data_dir = base_dir / "data"
data_dir.mkdir(parents=True, exist_ok=True)

url = "https://2.flashscore.ninja/2/x/feed/ran_hfDiar3L_1"
headers = {
    "Referer": "https://www.flashscore.com/",
    "Sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "Sec-ch-ua-mobile": "?0",
    "Sec-ch-ua-platform": "Windows",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "X-fsign": "SW9D1eZo",
    "X-Requested-With": "XMLHttpRequest"
}

response = requests.get(url=url, headers=headers)

if response.status_code == 200:
    response_text = response.text
    response_parts = re.findall(r"TS÷RW¬(.*?)TE÷RW¬", response_text, re.DOTALL)
    all_players = {}
    for p in response_parts:
        values = p.split("¬")
        player_dict = {}
        key = None
        value = None
        for v in values:
            player_info = v.split("÷")
            if len(player_info) == 2:
                if player_info[0] == "PT":
                    key = player_info[1]
                elif player_info[0] == "PV":
                    value = player_info[1]

                    if key is not None:
                        player_dict[key] = value
        all_players[player_dict["ID"]] = player_dict

    with open(data_dir / "wta_ranks.json", "w", encoding="utf-8") as f:
        json.dump(all_players, f, ensure_ascii=False, indent=4)

else:
    print("HTTP Error", response.status_code)