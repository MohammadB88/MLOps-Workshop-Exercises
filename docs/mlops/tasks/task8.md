# Model & Data Monitoring
In this task, you'll implement basic monitoring to track your model’s performance and input data quality over time. This includes observing metrics such as prediction accuracy, data drift, and request volume to ensure the deployed model remains reliable and continues to perform well in a real-world environment.


The steps in this task will be caried out in the fourth notebook: `04_model_monitoring.ipynb`


load reference and current data

set the 

### 4. Set the Model Deployment Endpoint
In the notebook, the ``MODEL_API_SERVICE`` should be replaced with the service url we created in step 2. This url can be found, when going to the ``Networking -> Service -> bike-model-api-svc``. It is shown under the ``Hostname`` and end with ``svc.cluster.local``.


create reports for data and model drift using evidently
