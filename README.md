# ParlayIQ

A machine learning model that predicts MLB game outcomes and generates daily parlay recommendations.

## How it works

1. `fetch.py` — runs daily to collect game data from The Odds API and MLB Stats API
2. `ml.py` — trains a Random Forest model on completed game data (build once you have enough data)
3. `predict.py` — uses the trained model to recommend a 5-leg parlay (build once model is trained)

## Data collected per game

- Game odds (home and away) from FanDuel via The Odds API
- Home and away team win rate from MLB standings
- Starting pitcher ERA and WHIP for both teams
- Final result (home team won or lost)

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

## Requirements

- Python 3.8+
- The Odds API key (free tier works)
