import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:5000/api/parlay";

function App() {
  const [games, setGames] = useState([]);
  const [parlayOdds, setParlayOdds] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    fetch(API_URL)
      .then((res) => {
        if (!res.ok) throw new Error(`Server responded ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setGames(data.games);
        setParlayOdds(data.parlay_odds);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  if (status === "loading") {
    return <div className="app">Loading today's parlay...</div>;
  }

  if (status === "error") {
    return (
      <div className="app">
        Couldn't load predictions. Is the Flask server running on port 5000?
      </div>
    );
  }

  return (
    <div className="app">
      <h1>predmark</h1>
      <p className="subtitle">Best 5-leg parlay, ranked by expected value</p>

      <div className="games">
        {games.map((g, i) => (
          <div className="game-card" key={`${g.home}-${g.away}-${g.date}-${i}`}>
            <div className="matchup">
              {g.away} @ {g.home}
            </div>
            <div className="pick">Pick: {g.pick}</div>
            <div className="stats">
              <span>Win prob: {(g.pick_prob * 100).toFixed(1)}%</span>
              <span>Odds: {g.pick_odds}</span>
              <span>EV: {g.ev.toFixed(3)}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="parlay-summary">
        Combined parlay odds: <strong>{parlayOdds.toFixed(2)}</strong>
      </div>
    </div>
  );
}

export default App;
