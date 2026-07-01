import os
import csv
import requests
import certifi
from dotenv import load_dotenv
import datetime

load_dotenv()

API_KEY = os.getenv("THE_ODDS_API_KEY")
base = os.path.dirname(__file__)
save_path = os.path.join(base, "games.csv")

fields = ["game_id", "date", "home_team", "away_team",
          "home_odds", "away_odds", "home_won", "home_win_rate","away_win_rate","home_whip","away_whip","home_pitcher_era","away_pitcher_era"]

if not os.path.exists(save_path):
    with open(save_path, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=fields).writeheader()

odds_url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
odds_params = {
    "apiKey": API_KEY,
    "regions": "us",
    "markets": "h2h",
    "oddsFormat": "decimal",
    "bookmakers": "fanduel"
}
odds_resp = requests.get(odds_url, params=odds_params, verify=certifi.where()).json()

scores_url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/scores"
scores_resp = requests.get(scores_url, params={"apiKey": API_KEY, "daysFrom": 1}, verify=certifi.where()).json()
scores_by_id = {g["id"]: g for g in scores_resp if g.get("completed")}
standings_url = "https://statsapi.mlb.com/api/v1/standings"
standings_params={"leagueId":"103,104","season":"2026","standingsTypes":"regularSeason"}
standings_resp=requests.get(standings_url,params=standings_params).json()
team_stats = {}
for record in standings_resp["records"]:
    for team in record["teamRecords"]:
        name = team["team"]["name"]
        wins = team["leagueRecord"]["wins"]
        losses = team["leagueRecord"]["losses"]
        team_stats[name] = {
            "win_rate": wins / (wins + losses) if (wins + losses) > 0 else 0,
            "run_diff": team["runDifferential"]
        }

schedule_url = "https://statsapi.mlb.com/api/v1/schedule"
schedule_params = {"sportId": "1", "date": datetime.date.today().strftime("%Y-%m-%d"), "hydrate": "probablePitcher"}
schedule_resp = requests.get(schedule_url, params=schedule_params).json()
pitcher_ids = {}
for date in schedule_resp.get("dates", []):
    for game in date["games"]:
        home = game["teams"]["home"]["team"]["name"]
        away = game["teams"]["away"]["team"]["name"]
        home_pitcher = game["teams"]["home"].get("probablePitcher", {})
        away_pitcher = game["teams"]["away"].get("probablePitcher", {})
        pitcher_ids[home] = home_pitcher.get("id")
        pitcher_ids[away] = away_pitcher.get("id")

def get_pitcher_stats(pitcher_id):
    if not pitcher_id:
        return None, None
    url=f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}/stats?stats=season&season=2026&group=pitching"
    resp = requests.get(url).json()
    splits=resp["stats"][0]["splits"]
    if not splits:
        return None, None
    stat = splits[0]["stat"]
    return stat.get("era"), stat.get("whip")
updated = 0
with open(save_path,"r") as f:
    all_rows=list(csv.DictReader(f))
    for row in all_rows:
        if row["home_won"]=="" and row["game_id"] in scores_by_id:
            s = scores_by_id[row["game_id"]]
            score_map = {sc["name"]: int(sc["score"]) for sc in s.get("scores", [])}
            if row["home_team"] in score_map and row["away_team"] in score_map:
                row["home_won"] = 1 if score_map[row["home_team"]] > score_map[row["away_team"]] else 0
                updated += 1
with open(save_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(all_rows)
print(f"updated {updated} game results")

existing_ids = set()
if os.path.exists(save_path):
    with open(save_path, "r") as f:
        for row in csv.DictReader(f):
            existing_ids.add(row["game_id"])

rows = []
for game in odds_resp:
    gid = game["id"]
    if gid in existing_ids:
        continue

    home = game["home_team"]
    away = game["away_team"]
    date = game["commence_time"][:10]

    home_odds, away_odds = None, None
    for bm in game.get("bookmakers", []):
        for market in bm.get("markets", []):
            for outcome in market.get("outcomes", []):
                if outcome["name"] == home:
                    home_odds = outcome["price"]
                elif outcome["name"] == away:
                    away_odds = outcome["price"]

    # check if game already has a result
    home_won = ""
    if gid in scores_by_id:
        s = scores_by_id[gid]
        score_map = {sc["name"]: int(sc["score"]) for sc in s.get("scores", [])}
        if home in score_map and away in score_map:
            home_won = 1 if score_map[home] > score_map[away] else 0
    home_era, home_whip = get_pitcher_stats(pitcher_ids.get(home))
    away_era, away_whip = get_pitcher_stats(pitcher_ids.get(away))
    home_stats = team_stats.get(home, {})
    away_stats = team_stats.get(away, {})
    rows.append({
        "game_id":   gid,
        "date":      date,
        "home_team": home,
        "away_team": away,
        "home_odds": home_odds,
        "away_odds": away_odds,
        "home_won":  home_won,
        "home_win_rate": home_stats.get("win_rate"),
        "away_win_rate": away_stats.get("win_rate"),
        "home_whip":     home_whip,
        "away_whip":     away_whip,
        "home_pitcher_era": home_era,
        "away_pitcher_era": away_era,

    })

with open(save_path, "a", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    for row in rows:
        writer.writerow(row)

print(f"added {len(rows)} new games to games.csv")
