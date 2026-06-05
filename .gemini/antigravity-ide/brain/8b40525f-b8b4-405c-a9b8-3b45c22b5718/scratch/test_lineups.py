import requests
from datetime import datetime

def test_fallback(team_id):
    current_year = datetime.now().year
    url_schedule = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&season={current_year}&teamId={team_id}"
    res = requests.get(url_schedule).json()
    
    # Scan backwards for the first completed game
    completed_game = None
    dates = res.get("dates", [])
    # We want to reverse the dates list to search from most recent
    for date_node in reversed(dates):
        for g in reversed(date_node.get("games", [])):
            if g["status"]["statusCode"] in ["F", "O"]:
                completed_game = g
                break
        if completed_game:
            break
            
    if not completed_game:
        print(f"No completed game found for team {team_id}")
        return None
        
    game_pk = completed_game["gamePk"]
    print(f"Last completed game for team {team_id} was gamePk {game_pk} on {completed_game['gameDate']}")
    
    url_boxscore = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
    box_data = requests.get(url_boxscore).json()
    
    # Figure out if team was home or away
    side = "home" if completed_game["teams"]["home"]["team"]["id"] == team_id else "away"
    
    team_box = box_data.get("teams", {}).get(side, {})
    order = team_box.get("battingOrder", [])
    players = team_box.get("players", {})
    
    lineup = []
    for pid in order[:9]:
        p_info = players.get(f"ID{pid}", {})
        p_name = p_info.get("person", {}).get("fullName", "Unknown")
        p_pos = p_info.get("position", {}).get("abbreviation", "N/A")
        lineup.append({"id": pid, "name": p_name, "position": p_pos})
        
    print(f"Fallback lineup for team {team_id}:")
    for b in lineup:
        print(f" - {b['name']} ({b['position']}, ID: {b['id']})")
    return lineup

if __name__ == "__main__":
    test_fallback(147) # Yankees
