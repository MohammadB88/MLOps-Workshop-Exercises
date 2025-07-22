# Automating the Workflow with Kubeflow Pipelines
##### (Kubeflow Pipeline - Reading Data & Model Training, Tracking & Registering)

Using Kubeflow Pipelines, you'll automate the end-to-end workflow for reading data, training a model, tracking experiments, and registering the trained model. This ensures your ML process is reproducible and scalable, with automatic logging of parameters, metrics, and artifacts.

Once the model is successfully registered, it will be automatically deployed to the OpenShift cluster as a new version of the prediction API. This enables continuous delivery of improved models with minimal manual intervention, ensuring your production environment always runs the best-performing version.

TODO

Set the Model Parameter n_estimator, ...

RUN the pipeline

Look up the MLflow GUI and see the second registered model

Edit the deployment to load the second registered model

Just see the logs for the pod with which the new model is deployed.