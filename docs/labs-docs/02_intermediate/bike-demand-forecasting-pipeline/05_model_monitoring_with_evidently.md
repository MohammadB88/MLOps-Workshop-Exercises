# 05_model_monitoring_with_evidently.md

## Model Monitoring with Evidently

The final stage of the pipeline ensures the model remains performant over time by detecting data and target drift.

### 1. Reference vs. Current Data
The `monitor_model` component compares two datasets:
- **Reference Data**: The original training data (baseline).
- **Current Data**: New production data (or in this lab, a different slice of the processed data).

### 2. Monitoring Presets
The pipeline uses **Evidently AI** to generate a comprehensive report using three main presets:
- **Data Drift Preset**: Checks if the distribution of input features (e.g., temperature, humidity) has shifted.
- **Target Drift Preset**: Checks if the distribution of the target variable (`count`) has changed.
- **Data Quality Preset**: Checks for missing values, duplicates, and overall data integrity.

### 3. Output Formats
The component generates two types of outputs:
- **HTML Report**: A visual dashboard for humans to analyze the drift.
- **JSON Report**: A machine-readable file that can be used to trigger automated alerts or retraining pipelines.

### Why Monitoring Matters
If the "current data" shows significant drift compared to the "reference data," the model's predictions may no longer be reliable, signaling that it is time to trigger a new training run.
