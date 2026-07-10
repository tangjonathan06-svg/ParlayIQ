import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from flask import Flask, jsonify
from flask_cors import CORS
from predict import build_parlay

app = Flask(__name__)
CORS(app)


@app.route("/api/parlay")
def get_parlay():
    top_picks, parlay_odds = build_parlay()
    return jsonify({"games": top_picks, "parlay_odds": parlay_odds})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
