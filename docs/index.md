# Welcome to the MLOps Workshop!

MLOps (Machine Learning Operations) is the practice of applying software engineering and DevOps principles to machine learning. Its goal is to make the creation, deployment, and operation of ML models smoother, more reliable, and scalable. Instead of treating models as one-off experiments, MLOps treats them as production systems that require automation, monitoring, and collaboration.

In this workshop, we focus on operationalizing the entire machine learning lifecycle—from preparing data and training models to versioning, testing, scalable deployment, and monitoring.

By bridging the gap between data scientists, ML engineers, and IT/DevOps teams, MLOps enables reproducible experiments, stable deployments, and ongoing improvement of ML solutions in real-world production environments.

<figure markdown>
  ![MLOps Workshop Logo](assets/images/mlops-workshop-logo.png#only-light){ width="350" }
  ![MLOps Workshop Logo](assets/images/mlops-workshop-logo.png#only-dark){ width="350" }
  <figcaption></figcaption>
</figure>

You will learn all about MLOps concepts, tools and principles:

<!-- * MLOps and highlight common challenges in operationalizing machine learning models. -->

* Define MLOps, its principles, and how it integrates machine learning, DevOps, and software engineering.

* Discuss challenges such as reproducibility, scalability, collaboration, and monitoring.

* Explore the ML lifecycle and its pain points in production environments (e.g., data drift, model degradation).

* Use MLflow for experiment tracking, registering models, and LLM performance testing.

* ???Package the model using as a REST API using tools like Flask or FastAPI.
      
* Deploy the registered model to a cloud native environment.

* Monitor the deployed model in production using Evidently to detect issues like data drift or performance degradation.

* Discuss strategies for retraining or updating models when Evidently detects issues, integrating this process into the MLOps pipeline.

Upon completing this lab, you will be equipped to apply MLOps principles and tools to bring machine learning models from your laptop to a cloud native environment.

## Lab Overview - TODO
- Beginner:
    * Wine Classifier
    * Bike Sharing
- Intermediate:
    * Pipeline for training and deployment
- Advanced:
    * LLMOps


## From other sources:

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