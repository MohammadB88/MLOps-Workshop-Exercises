# Model Deploymet - Deploy on OpenShift Cluster
In this task, you'll deploy your containerized model API to an OpenShift cluster. This involves creating the necessary Kubernetes resources (such as deployments and services), exposing the API endpoint, and ensuring your model is accessible and scalable in a production-like environment.

We will test the deployment by sending a batch inferencing request using the Test Dataset to verify the model's functionality.

The steps in this task will be caried out in the third notebook: `03_model_deployment.ipynb`

### 1. Go the to the OpenShift Console
Find your porject (e.g. `user1`) in the openshift console.

### 2. Create a Deployment Using the Built Image
From the left pannel go to `Workloads -> Deployment` and create a new deployment. 

```bash
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bike-model-api
  labels:
    app: bike-model-api
spec:
  replicas: 1
  selector:
    matchLabels:
      app: bike-model-api
  template:
    metadata:
      labels:
        app: bike-model-api
    spec:
      containers:
        - name: bike-model-container
          image: IMAGE_URL_FROM_IMAGE_STREAM  # It can be found on the imagestream page in OpenShift
          ports:
            - containerPort: 8000
          env:
            - name: MLFLOW_TRACKING_URI
              value: "MLFLOW_REMOTE_TRACKING_SERVER"
            - name: MODEL_NAME
              value: "MODEL_NAME" # f"BikeSharingModel_{PARTICIPANT_FIRSTNAME}"
            - name: MODEL_VERSION
              value: "1"  # Or leave it empty for latest Production version
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
```

💡 **Note One:** Please set the link to the image from the last task. It could also be found in the created ``ImageStream``.

💡 **Note Two:** Make sure that you set the currect values for the environment variables (e.g. `MLFLOW_TRACKING_URI`, `MODEL_NAME`, `MODEL_VERSION`) and replace the placeholders.

``MODEL_VERSION`` is already set to ``1``, but if you have more that 1 version and you want to deploy that, please change the value for variable ``MODEL_VERSION`` accordingly.

`MLFLOW_TRACKING_URI` is the same server you have set in step 3 & 4.

### 3. Service: Expose the API Endpoint internally 
Create a service to expose your API internally for applications on the same cluster:

From the left pannel go to `Network -> Service` and create a new service. 
```bash
apiVersion: v1
kind: Service
metadata:
  name: bike-model-api-svc
spec:
  selector:
    app: bike-model-api
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: ClusterIP
```

Now, the model is reachable only from inside the cluster!

### 4. Route (Optional): Expose the API Endpoint externally
Deploy this resource **ONLY and ONLY** if you want to make your model accessible outside the OpenShift cluster.
From the left pannel go to `Network -> Route` and create a new route.
```bash
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: bike-model-api-route
spec:
  port:
    targetPort: 8000 
  to:
    kind: Service
    name: bike-model-api-svc
  tls:
    termination: edge  # or passthrough, depending on your needs
    insecureEdgeTerminationPolicy: Redirect  # Redirect HTTP to HTTPS
```

### 5. Prepare the Test Data
A sample test dataset (e.g., a few rows of processed features) is already created for you in CSV or JSON format that matches the model’s input schema: ``workshop_materials/bike_demand_forecasting/data/test_model``.

Run the cells in the notebook to take this test dataset and create the inference request.

### 6. Set the Model Deployment Endpoint
In the notebook, the ``MODEL_API_SERVICE`` should be replaced with the service url we created in step 3. This url can be found, when going to the ``Networking -> Service -> bike-model-api-svc``. It is shown under the ``Hostname`` and end with ``svc.cluster.local``.

### 7. Simple and Batch Inferencing
As you follow the instruction in the notebook to send requests to test the model endpoint, you see that the prediction is returned for all the test data stored in the sample dataset.

Finally, a script is provided to visualize the ``Actual vs Predicted Counts`` for sample inputs.
