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
    home_stats = team_stats.get(home, {})
    away_stats = team_stats.get(away, {})
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
    ]], columns=["home_odds", "away_odds", "home_win_rate", "away_win_rate",
                 "home_whip", "away_whip", "home_pitcher_era", "away_pitcher_era",
                 "home_runs_per_game", "away_runs_per_game",
                 "home_runs_allowed_per_game", "away_runs_allowed_per_game",
                 "home_pitcher_k9", "away_pitcher_k9",
                 "home_pitcher_bb9", "away_pitcher_bb9",
                 "home_run_diff_per_game", "away_run_diff_per_game",
                 "home_away_win_rate", "away_home_win_rate"])
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


