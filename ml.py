import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import pickle

base = os.path.dirname(__file__)
df = pd.read_csv(os.path.join(base, "games.csv"))
df = df[df["home_won"] != ""]
X = df[["home_odds", "away_odds", "home_win_rate", "away_win_rate", "home_whip", "away_whip", "home_pitcher_era", "away_pitcher_era"]]
y = df["home_won"]
X=X.dropna()
y=y[X.index]
X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=0.2)
model=RandomForestClassifier(n_estimators=100,random_state=42)
model.fit(X_train,y_train)
predictions=model.predict(X_test)
fi = pd.Series(model.feature_importances_, index=X.columns)
pickle.dump(model, open(os.path.join(base, "model.pkl"), "wb"))
print("Accuracy:", accuracy_score(y_test, predictions))
print(fi.sort_values(ascending=False))
