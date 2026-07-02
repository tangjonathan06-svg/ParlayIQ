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
          "home_odds", "away_odds", "home_won",
          "home_win_rate", "away_win_rate",
          "home_whip", "away_whip",
          "home_pitcher_era", "away_pitcher_era",
          "home_runs_per_game", "away_runs_per_game",
          "home_runs_allowed_per_game", "away_runs_allowed_per_game",
          "home_pitcher_k9", "away_pitcher_k9",
          "home_pitcher_bb9", "away_pitcher_bb9",
          "home_run_diff_per_game", "away_run_diff_per_game",
          "home_away_win_rate", "away_home_win_rate",
          "home_ops", "away_ops",
          "home_hr_per_game", "away_hr_per_game",
          "home_k_rate", "away_k_rate",
          "home_bb_rate", "away_bb_rate",
          "home_avg", "away_avg"]

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
name_map = {
    "Arizona Diamondbacks": "D-backs",
    "Atlanta Braves": "Braves",
    "Baltimore Orioles": "Orioles",
    "Boston Red Sox": "Red Sox",
    "Chicago Cubs": "Cubs",
    "Chicago White Sox": "White Sox",
    "Cincinnati Reds": "Reds",
    "Cleveland Guardians": "Guardians",
    "Colorado Rockies": "Rockies",
    "Detroit Tigers": "Tigers",
    "Houston Astros": "Astros",
    "Kansas City Royals": "Royals",
    "Los Angeles Angels": "Angels",
    "Los Angeles Dodgers": "Dodgers",
    "Miami Marlins": "Marlins",
    "Milwaukee Brewers": "Brewers",
    "Minnesota Twins": "Twins",
    "New York Mets": "Mets",
    "New York Yankees": "Yankees",
    "Athletics": "Athletics",
    "Philadelphia Phillies": "Phillies",
    "Pittsburgh Pirates": "Pirates",
    "San Diego Padres": "Padres",
    "San Francisco Giants": "Giants",
    "Seattle Mariners": "Mariners",
    "St. Louis Cardinals": "Cardinals",
    "Tampa Bay Rays": "Rays",
    "Texas Rangers": "Rangers",
    "Toronto Blue Jays": "Blue Jays",
    "Washington Nationals": "Nationals",
}

standings_url = "https://statsapi.mlb.com/api/v1/standings"
standings_params={"leagueId":"103,104","season":"2026","standingsTypes":"regularSeason"}
standings_resp=requests.get(standings_url,params=standings_params).json()
hit_resp = requests.get("https://statsapi.mlb.com/api/v1/teams/stats?stats=season&season=2026&group=hitting&gameType=R&sportId=1").json()
hitting_by_id = {}
for split in hit_resp["stats"][0]["splits"]:
    hitting_by_id[split["team"]["id"]] = split["stat"]

team_stats = {}
for record in standings_resp["records"]:
    for team in record["teamRecords"]:
        name = team["team"]["name"]
        team_id = team["team"]["id"]
        wins = team["leagueRecord"]["wins"]
        losses = team["leagueRecord"]["losses"]
        games_played = team.get("gamesPlayed", 1) or 1
        runs_scored = team.get("runsScored", 0)
        runs_allowed = team.get("runsAllowed", 0)
        run_diff = team.get("runDifferential", 0)
        home_record = next((r for r in team.get("records", {}).get("splitRecords", []) if r["type"] == "home"), {})
        away_record = next((r for r in team.get("records", {}).get("splitRecords", []) if r["type"] == "away"), {})
        home_wins = home_record.get("wins", 0)
        home_losses = home_record.get("losses", 0)
        away_wins = away_record.get("wins", 0)
        away_losses = away_record.get("losses", 0)
        hit = hitting_by_id.get(team_id, {})
        pa = hit.get("plateAppearances", 1) or 1

        team_stats[name] = {
            "win_rate": wins / (wins + losses) if (wins + losses) > 0 else 0,
            "runs_per_game": runs_scored / games_played,
            "runs_allowed_per_game": runs_allowed / games_played,
            "run_diff_per_game": run_diff / games_played,
            "home_win_rate": home_wins / (home_wins + home_losses) if (home_wins + home_losses) > 0 else 0,
            "away_win_rate": away_wins / (away_wins + away_losses) if (away_wins + away_losses) > 0 else 0,
            "ops": hit.get("ops"),
            "hr_per_game": (hit.get("homeRuns", 0) or 0) / games_played,
            "k_rate": (hit.get("strikeOuts", 0) or 0) / pa,
            "bb_rate": (hit.get("baseOnBalls", 0) or 0) / pa,
            "avg": hit.get("avg"),
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
        return None, None, None, None
    url=f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}/stats?stats=season&season=2026&group=pitching"
    resp = requests.get(url).json()
    splits=resp["stats"][0]["splits"]
    if not splits:
        return None, None, None, None
    stat = splits[0]["stat"]
    return stat.get("era"), stat.get("whip"), stat.get("strikeoutsPer9Inn"), stat.get("walksPer9Inn")
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
    home_era, home_whip, home_k9, home_bb9 = get_pitcher_stats(pitcher_ids.get(home))
    away_era, away_whip, away_k9, away_bb9 = get_pitcher_stats(pitcher_ids.get(away))
    home_stats = team_stats.get(name_map.get(home, home), {})
    away_stats = team_stats.get(name_map.get(away, away), {})
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
        "home_whip": home_whip,
        "away_whip": away_whip,
        "home_pitcher_era": home_era,
        "away_pitcher_era": away_era,
        "home_runs_per_game": home_stats.get("runs_per_game"),
        "away_runs_per_game": away_stats.get("runs_per_game"),
        "home_runs_allowed_per_game": home_stats.get("runs_allowed_per_game"),
        "away_runs_allowed_per_game": away_stats.get("runs_allowed_per_game"),
        "home_pitcher_k9": home_k9,
        "away_pitcher_k9": away_k9,
        "home_pitcher_bb9": home_bb9,
        "away_pitcher_bb9": away_bb9,
        "home_run_diff_per_game": home_stats.get("run_diff_per_game"),
        "away_run_diff_per_game": away_stats.get("run_diff_per_game"),
        "home_away_win_rate": home_stats.get("home_win_rate"),
        "away_home_win_rate": away_stats.get("away_win_rate"),
        "home_ops": home_stats.get("ops"),
        "away_ops": away_stats.get("ops"),
        "home_hr_per_game": home_stats.get("hr_per_game"),
        "away_hr_per_game": away_stats.get("hr_per_game"),
        "home_k_rate": home_stats.get("k_rate"),
        "away_k_rate": away_stats.get("k_rate"),
        "home_bb_rate": home_stats.get("bb_rate"),
        "away_bb_rate": away_stats.get("bb_rate"),
        "home_avg": home_stats.get("avg"),
        "away_avg": away_stats.get("avg"),
    })

with open(save_path, "a", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    for row in rows:
        writer.writerow(row)

print(f"added {len(rows)} new games to games.csv")
