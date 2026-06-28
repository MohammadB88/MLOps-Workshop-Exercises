# MLflow Installation with helm
In order to install mlflow on OpenShift using helm charts from bitnami, following steps are necessary:

1. Open a terminal on the bastian host or direct connect to a ``"web terminal"`` client on the openshift.

2. Create a namespace/project ``mlflow` in the cluster:
```bash
oc new-project mlflow 
```

3. Add the bitnami charts as a repository:
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
```

you can check if the repository is correctly added:
```bash
helm repo list
helm rpeo update
```

4. Copy the values of the mlflow charts in a yaml file:
```bash
helm show values bitnami/mlflow > mlflow_values.yaml
```

5. Open the `mlflow_values.yaml` with editor (usually vim/vi):
```bash
vim mlflow_values.yaml
```

edit some parts:

The service type for tracking server is is `LoadBalancer`, which should be ClusterIP (Search for ``"LoadBalancer"`` in the values file you just generated):
```bash
LoadBalancer -> ClusterIP
```

We will later add a route to access the UI of the mlflow tracking server.

Disable the authentification for tracking server (Search for ``"username: user"`` in the values file you just generated):
```bash
enabled: true -> enabled: false
username: user
```

Due to change in bitnami policy for its images and charts, we need to pull the images from another repository.

So these repositories should be changed to find the images in  `bitnamilegacy` instead of `bitnami`:

```bash
repository: bitnamil/mlflow -> bitnamilegacy/mlflow

repository: bitnamil/os-shell -> bitnamilegacy/os-shell

repository: bitnami/git -> bitnamilegacy/git
```

**Workaround for now:** In addition, we will disable the ``postgresql`` and `minio`:

```bash
postgresql:
  enabled: false

minio:
  enabled: false
```

6. Install the MLflow using helm charts and these values:
```bash
helm install mlflow bitnami/mlflow --namespace mlflow --values mlflow_values.yaml
```


