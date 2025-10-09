# 7: Model Deploymet - Deploy on OpenShift Cluster

## Objective
In this lab, we will:

* deploy the containerized model API onto OpenShift cluster
* create necessary Kubernetes resources (i.e deployments, services, and routes)

ensuring the model is accessible and scalable in a production-like environment.

## Guide

### Step 1 - Go to the OpenShift Console
Find your porject (e.g. `user1`) in the openshift console.
💡 **Note:** Please make sure that you are in your given project.

### Step 2 - Create a Deployment Using the Built Image
From the left pannel go to `Workloads -> Deployment` and create a new deployment. 

💡 **Note One:** Please set the link to the image from the last task. It could also be found in the created ``ImageStream``.

💡 **Note Two:** Make sure that you set the currect values for the environment variables (e.g. `MLFLOW_TRACKING_URI`, `MODEL_NAME`, `MODEL_VERSION`) and replace the placeholders.

💡 **Note Three:** ``MODEL_VERSION`` is already set to ``1``, but if you have more that 1 version and you want to deploy that, please change the value for variable ``MODEL_VERSION`` accordingly.

💡 **Note Four:** `MLFLOW_TRACKING_URI` is the same server you have set in step 3 & 4.

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

### Step 3 - Service: Expose the API Endpoint internally 
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

### Step 4 - Route (Optional): Expose the API Endpoint externally
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

✅ **Now with a model to deploy, we see how to prepare the deployment files and dependencies in a container, in the next exercise** [Model Deploymet - Testing Model Endpoint-API](./08_test_model_endpoint.md).

