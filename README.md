# predmark

A machine learning model that predicts MLB game outcomes and generates daily parlay recommendations.

## How it works

1. `fetch.py` — runs daily to collect game data from The Odds API and MLB Stats API
2. `ml.py` — trains a Random Forest model on completed game data (build once you have enough data)
3. `predict.py` — uses the trained model to recommend a 5-leg parlay (build once model is trained)

## Data collected per game

**Odds**
- Home and away odds from FanDuel via The Odds API

**Team stats** (from MLB standings)
- Win rate (overall, home, away)
- Runs scored per game
- Runs allowed per game
- Run differential per game

**Pitcher stats** (from MLB Stats API)
- ERA
- WHIP
- Strikeouts per 9 innings (K/9)
- Walks per 9 innings (BB/9)

**Hitting stats** (from MLB Stats API)
- OPS (on-base + slugging)
- Home runs per game
- Strikeout rate
- Walk rate
- Batting average

**Result**
- Whether the home team won (filled in after the game)

## Setup

1. Create a `.env` file with your API key:
   ```
   THE_ODDS_API_KEY=your_key_here
   ```
2. Install dependencies:
   ```
   pip install requests python-dotenv certifi
   ```

## Daily workflow

Run `fetch.py` every day to collect new games and update results from the previous day:
```
python fetch.py
```

## Web UI

`predict.py`'s picks are also available through a small Flask + React app in `webapp/`.

Start the backend (from `predmark/`):
```
python webapp/backend/app.py
```
This serves `GET /api/parlay` on `http://localhost:5000`.

Start the frontend (from `webapp/frontend/`):
```
npm run dev
```
This opens the dashboard on `http://localhost:5173`, which fetches from the Flask server above.

## Requirements

- Python 3.8+
- The Odds API key (free tier works)
- No API key needed for MLB Stats API
