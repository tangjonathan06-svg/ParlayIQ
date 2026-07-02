import pickle
import os
import datetime
import csv
import requests
import certifi
import pandas as pd
from dotenv import load_dotenv


base = os.path.dirname(__file__)
model = pickle.load(open(os.path.join(base, "model.pkl"), "rb"))
load_dotenv()
API_KEY = os.getenv("THE_ODDS_API_KEY")
odds_url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
odds_params = {
    "apiKey": API_KEY,
    "regions": "us",
    "markets": "h2h",
    "oddsFormat": "decimal",
    "bookmakers": "fanduel"
}
odds_resp = requests.get(odds_url, params=odds_params, verify=certifi.where()).json()

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
games = []
for game in odds_resp:
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

    home_era, home_whip, home_k9, home_bb9 = get_pitcher_stats(pitcher_ids.get(home))
    away_era, away_whip, away_k9, away_bb9 = get_pitcher_stats(pitcher_ids.get(away))
    home_stats = team_stats.get(name_map.get(home, home), {})
    away_stats = team_stats.get(name_map.get(away, away), {})
    features = pd.DataFrame([[
        home_odds, away_odds,
        home_stats.get("win_rate"), away_stats.get("win_rate"),
        home_whip, away_whip,
        home_era, away_era,
        home_stats.get("runs_per_game"), away_stats.get("runs_per_game"),
        home_stats.get("runs_allowed_per_game"), away_stats.get("runs_allowed_per_game"),
        home_k9, away_k9,
        home_bb9, away_bb9,
        home_stats.get("run_diff_per_game"), away_stats.get("run_diff_per_game"),
        home_stats.get("home_win_rate"), away_stats.get("away_win_rate"),
        home_stats.get("ops"), away_stats.get("ops"),
        home_stats.get("hr_per_game"), away_stats.get("hr_per_game"),
        home_stats.get("k_rate"), away_stats.get("k_rate"),
        home_stats.get("bb_rate"), away_stats.get("bb_rate"),
        home_stats.get("avg"), away_stats.get("avg"),
    ]], columns=["home_odds", "away_odds", "home_win_rate", "away_win_rate",
                 "home_whip", "away_whip", "home_pitcher_era", "away_pitcher_era",
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
                 "home_avg", "away_avg"])
    prob = model.predict_proba(features)[0][1]
    games.append({"home": home, "away": away, "date": date, "home_odds": home_odds, "prob": prob})

games.sort(key=lambda x: x["prob"], reverse=True)
top5 = games[:5]

parlay_odds = 1
for g in top5:
    parlay_odds *= g["home_odds"]

print("Best 5-leg parlay")
for g in top5:
    print(f"{g['home']} vs {g['away']} | home win prob: {round(g['prob']*100, 1)}% | odds: {g['home_odds']}")
print(f"\nCombined parlay odds: {round(parlay_odds, 2)}")

