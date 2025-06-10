FROM python:3.9-slim
WORKDIR /app
COPY bike_model.pkl app.py ./
RUN pip install fastapi[all] joblib pandas
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
