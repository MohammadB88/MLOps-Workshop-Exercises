# Forecasting Bike-Sharing Demand and Monitoring Model Performance

<!-- ![docs\assets\images\bike_sharing_logo.png](docs\assets\images\bike_sharing_logo.png) -->

<figure markdown>
  ![bike sharing logo](../assets/images/bike_sharing_logo.png#only-light){ width="300" }
  ![bike sharing logo](../assets/images/bike_sharing_logo.png#only-dark){ width="300" }
  <figcaption></figcaption>
</figure>


## 🚲 Introduction

In urban environments, bike-sharing systems have emerged as a sustainable and efficient mode of transportation. Accurately predicting bike rental demand is crucial for optimizing operations, ensuring bike availability, and enhancing user satisfaction.

This documentation presents a comprehensive approach to developing and deploying a machine learning model for bike-sharing demand forcasting. Drawing inspiration from [Analytics Vidhya's end-to-end case study](https://www.analyticsvidhya.com/blog/2023/05/end-to-end-case-study-bike-sharing-demand-prediction/), we delve into data preprocessing, feature engineering, model training, and evaluation. 

Beyond model development, maintaining performance in a production environment is vital. Models can degrade over time due to changing data patterns, a phenomenon known as concept drift. To address this, we incorporate monitoring strategies inspired by [Evidently AI's tutorial on production model analytics](https://www.evidentlyai.com/blog/tutorial-1-model-analytics-in-production). This includes setting up regular performance checks and generating interactive reports to detect issues proactively.

By following this guide, you'll gain insights into building a robust machine learning pipeline for bike-sharing demand prediction and implementing effective monitoring to ensure sustained model performance in real-world applications.

## Overview of the Problem
A company operates a bike-sharing platform and wants to understand and predict bike demand on an hourly basis. To support this, a dataset has been provided containing hourly records enriched with contextual features such as weather, season, and the day of the week.

The goal is to analyze this dataset and develop a machine learning model that can forecast hourly demand for bikes. This problem simulates a real-world scenario where the company only has access to historical data from January and February. Using this limited data, we train a **Random Forest Regressor** to predict future demand.

This setup reflects several practical challenges faced in deploying and maintaining models in production:

- **Data availability and delay:** Usage data may be stored locally and only synced with a central database weekly or even monthly, making real-time monitoring and updates difficult.

- **Gradual model decay:** As time progresses, patterns in user behavior or external conditions (e.g., weather, seasonality) may change. Since the model is trained only on winter data (January and February), its performance may gradually deteriorate as new, unseen seasonal patterns emerge. This phenomenon—where a model's predictive quality declines over time—is known as gradual model decay.
 
Understanding and mitigating this decay is crucial for maintaining reliable predictions in production.

### Data and Considered Featurers
We see the considered features in the below image ([How to break a model in 20 days!](https://www.evidentlyai.com/blog/tutorial-1-model-analytics-in-production)):

<figure markdown>
  ![bike sharing features](../assets/images/bike_sharing_features.png#only-light){ width="500" }
  ![bike sharing features](../assets/images/bike_sharing_features.png#only-dark){ width="500" }
  <figcaption></figcaption>
</figure>

Here is a list of features that we condsider when training the model:

- hour - hourly  
- weekday - day of the week
- weather situation (weathersit) - 
    - 1: Clear, Few clouds, Partly cloudy, Partly cloudy
    - 2: Mist + Cloudy, Mist + Broken clouds, Mist + Few clouds, Mist
    - 3: Light Snow, Light Rain + Thunderstorm + Scattered clouds, Light Rain + Scattered clouds
    - 4: Heavy Rain + Ice Pallets + Thunderstorm + Mist, Snow + Fog 
- temp - temperature in Celsius 
- atemp - "feels like" temperature in Celsius
- humidity - relative humidity
- windspeed - wind speed
- season -  
    - 1 = spring
    - 2 = summer
    - 3 = fall
    - 4 = winter 
- holiday - whether the day is a holiday
- workingday - whether the day is a working day (i.e., not a weekend or holiday)
- count - total number of rentals (target variable)

### Model: Random Forest Regressor 
The **Random Forest Regressor** is an ensemble machine learning model that builds multiple decision trees and averages their predictions to improve accuracy and reduce overfitting. Each tree is trained on a random subset of the data and features, which introduces diversity and helps generalize better to unseen data. By aggregating the outputs of many weak learners (trees), the model provides robust and stable regression predictions.

It offers a variety of hyperparameters that one can tune to adjust and potentially improve the model’s performance. 
For this example, we only play with two of these hyperparameters:

- ``n_estimators``:  Number of decision trees that the model builds (i.e 50, 100, 150, 200)

- ``max_depth``: Maximum depth of each tree (i.e 5, 10, 15, 20)

## Directory Structure

The bike_demand_forecasting project is organized into modular folders for clarity and workflow. It includes raw and processed datasets under data/, Jupyter notebooks for each MLOps stage in notebooks/, trained models in models/, and generated analysis or drift reports in reports/—supporting a full ML lifecycle.

```
bike_demand_forecasting/
├── 01_data_exploration.ipynb
├── 02_model_training.ipynb
├── 03_model_deployment.ipynb
├── 04_model_monitoring.ipynb
├── data/
│   ├── raw/
│   ├── processed/
│   └── test_model/
├── models/
└── reports/
bike_demand_forecasting_pipeline/
├── pipeline_bike_sharing.py
└── reports/
```

## Prerequisites

### Environment
You can use your own *JupyterLab* environment.

Otherwise, use the provided *JupyterLab* environment, which comes pre-configured and ready to use. Log in to this environment with *username* and *password* provided during the workshop.

## 📘 Hands-On Sessions
To build a strong foundation in MLOps, participants will begin by executing each stage of the machine learning workflow manually. This hands-on approach helps solidify the concepts and understand how data and models progress through the pipeline.

💡 **Note One:** Workshop materials for **tasks 1 to 7** are stored under the path: ``"workshop_materials/bike_demand_forecasting"``

💡 **Note Two:** Workshop materials for **tasks 8** are stored under the path: ``"workshop_materials/bike_demand_forecasting_pipeline"``

* [Task 1 - Clone the repository & Load and explore the data](tasks/task1.md)
* [Task 2 - Data Preparations for Model Training](tasks/task2.md)
* [Task 3 - Model Training & Experiment Tracking](tasks/task3.md)
* [Task 4 - Review the Experiments & Select the Best Model](tasks/task4.md)
* [Task 5 - Model Deploymet - Containerize the Endpoint-API](tasks/task5.md)
* [Task 6 - Model Deploymet - Deploy on OpenShift Cluster](tasks/task6.md)
* [Task 7 - Model & Data Monitoring](tasks/task7.md)
* [Task 8 - Automating the Workflow with ***Kubeflow Pipelines***](tasks/task8_kubeflow.md)
* [Task 9 - Automating the Workflow with ***Elyra Pipelines***](tasks/task9_elyra.md)


