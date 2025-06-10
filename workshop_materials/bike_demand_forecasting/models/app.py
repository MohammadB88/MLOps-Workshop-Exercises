from fastapi import FastAPI
import joblib
import pandas as pd

app = FastAPI()
model = joblib.load("bike_model.pkl")

@app.post("/predict")
def predict(features: dict):
    df = pd.DataFrame([features])
    prediction = model.predict(df)[0]
    return {"prediction": prediction}
