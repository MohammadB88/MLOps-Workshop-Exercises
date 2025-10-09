# Welcome to the MLOps Workshop!


MLOps (Machine Learning Operations) is a discipline that combines machine learning, software engineering, and DevOps practices to streamline the development, deployment, and maintenance of machine learning models in production. It focuses on automating and monitoring the entire ML lifecycle, from data preparation and model training to version control, testing, and scalable deployment. By fostering collaboration between data scientists, engineers, and IT teams, MLOps ensures models are reliable, reproducible, and capable of delivering business value in real-world environments.

<figure markdown>
  ![CC Logo](assets/images/mlops-workshop-logo.jpeg#only-light){ width="500" }
  ![CC Logo](assets/images/mlops-workshop-logo.jpeg#only-dark){ width="500" }
  <figcaption></figcaption>
</figure>

<!-- <figure markdown>
  ![CC Logo](assets/images/ansible-community-logo-black.png#only-light){ width="500" }
  ![CC Logo](assets/images/ansible-community-logo-white.png#only-dark){ width="500" }
  <figcaption></figcaption>
</figure> -->

You will learn all about MLOps tools and Principals in 5 steps:

1. Provide foundational knowledge about MLOps and highlight common challenges in operationalizing machine learning models.
      * Define MLOps, its principles, and how it integrates machine learning, DevOps, and software engineering.
      * Discuss challenges such as reproducibility, scalability, collaboration, and monitoring.
      * Explore the ML lifecycle and its pain points in production environments (e.g., data drift, model degradation).
  
2. Train a machine learning model as a baseline for deployment.
      * Load and preprocess a sample dataset (e.g., sklearn’s Iris or custom tabular data).
      * Train a model using a Python ML framework like Scikit-learn or TensorFlow.
      <!-- * Save the trained model and prepare it for tracking using tools like MLflow -->

3. Demonstrate how to use MLflow for experiment tracking and registering models.
      * Set up MLflow tracking server locally or in the cloud.
      * Log experiments: track metrics, parameters, and artifacts using MLflow's API.
      * Register the best-performing model in MLflow’s model registry and add metadata (version, tags, etc.).
      * Briefly explain the benefits of a centralized model registry for collaboration and version control.

4. Deploy the registered model to a production-like cluster environment.
      * Package the model as a REST API using tools like Flask or FastAPI.
      * Deploy the API to a cluster environment (e.g., Kubernetes)
      <!-- *  or Docker Swarm). -->
      <!-- * Automate deployment pipelines using CI/CD tools (e.g., GitHub Actions or Jenkins) and ensure the model is accessible to end-users or applications. -->

5. Monitor the deployed model in production using Evidently to detect issues like data drift or performance degradation.
      * Set up Evidently dashboards to track key metrics, including feature distribution, target drift, and prediction quality.
      * Simulate data drift by sending new datasets to the model’s API and analyze the impact using Evidently.
      <!-- * Discuss strategies for retraining or updating models when Evidently detects issues, integrating this process into the MLOps pipeline. -->

<!-- You’ll start off by writing your first Ansible playbook, work on Jinja templates, and implement higher-level Ansible roles. Next you’ll get started on automation controller, understand inventory and credential management, projects, job templates, surveys, workflows and more. -->

After finishing this lab you are ready to start using MLOps tools and principals to deploy your models in production.

## Time planning
TODO
The time required to do the workshops strongly depends on multiple factors: the length of the workshop. the number of participants, how familiar you are with Linux, Containers, and Kubernetes in general as well as topics like Data Engineering and Machine Learning.
<!-- how much discussions are done in between. -->

<!-- Having said that, the exercises themselves should take roughly 4-5 hours, not counting the projects.   -->

## Lab Overview
TODO
<!-- <figure markdown>
  ![ansible rhel lab diagram](rhel_lab_diagram.png){ loading=lazy }
  <figcaption></figcaption>
</figure> -->



### From other sources:

Machine learning models require extra consideration for monitoring models in production and retraining if the performance declines. 

The engineering practice of MLOps leverages three contributing disciplines: machine learning, software 
engineering (especially DevOps), and data engineering. The goal of MLOps is to bridge the gap between 
development (Dev) and operations (Ops) and create a repeatable process for training, deploying, 
monitoring, and updating machine learning models. 

MLOps provides tools and processes so that collaborators can contribute their part to achieve a seamless flow from model request to deploying models to solve business problems. 

Key components of the MLOps pipeline are: 
• Data management 
• Model development 
• Model deployment 
• Monitoring and optimization 
• Collaboration and governance


**HOW A USECASE FOR A MLOPS WORKSHOP SHOULD LOOKE LIKE:**

An insurance company has data on their customers that includes customer information, policies, and 
claims. The policies include a risk factor calculated using an age-old formula. They want to know if they 
can improve on it by adding information such as accidents in the Chicago area.  
The goal is not necessarily to provide a new model to replace the old model but to show how IBM watsonx 
platform can facilitate MLOps.  
The project covers five parts.  
1. Preparing data: exploring the data, adding new data, preparing the data for training 
2. Developing the model: developing the model via AutoAI, Jupyter notebook, SPSS flow 
3. Deploying the model: via UI and Jupyter notebooks 
4. Monitoring the model via OpenScale and AI Factsheets 
5. Automating the MLOps lifecycle 