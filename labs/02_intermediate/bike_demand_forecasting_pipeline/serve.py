import os
import mlflow.pyfunc
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Bike Sharing Demand Prediction API")

# Load model at startup
MODEL_PATH = os.getenv("MODEL_PATH", "/app/model")
print(f"Loading model from {MODEL_PATH}")
try:
    model = mlflow.pyfunc.load_model(MODEL_PATH)
    print("Model loaded successfully")
except Exception as e:
    print(f"Error loading model: {e}")
    raise

class BikeFeatures(BaseModel):
    season: int
    yr: int
    mnth: int
    hr: int
    holiday: int
    weekday: int
    workingday: int
    weathersit: int
    temp: float
    atemp: float
    hum: float
    windspeed: float

@app.post("/predict")
async def predict_demand(features: BikeFeatures):
    try:
        # Convert features to DataFrame for prediction
        input_df = pd.DataFrame([features.dict()])
        
        # Rename columns to match training format
        input_df.rename(columns={
            'yr': 'year',
            'mnth': 'month',
            'hr': 'hour',
            'hum': 'humidity'
        }, inplace=True)
        
        # Make prediction
        prediction = model.predict(input_df)
        
        return {"predicted_demand": float(prediction[0])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)