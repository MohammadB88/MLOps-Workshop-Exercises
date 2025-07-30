# MLflow Installation with helm
In order to install mlflow on OpenShift using helm charts from bitnami, following steps are necessary:

1. Open a terminal on the bastian host or direct connect to a ``"web terminal"`` client on the openshift.

2. Add the bitnami charts as a repository:
```bash
helm repo add https://charts.bitnami.com/bitnami
```

you can check if the repository is correctly added:
```bash
helm repo list
helm rpeo update
```

2. Copy the values of the mlflow charts in a yaml file:
```bash
helm show values bitnami/mlflow > mlflow_values.yaml
```

2. Open the `mlflow_values.yaml` with editor (usually vim/vi):
```bash
vim mlflow_values.yaml
```

edit two parts:

The service type for tracking server is is `Loadbalancer`, which should be ClusterIP: 
```bash
LoadBalancer -> ClusterIP
```

We will later add a route to access the UI of the mlflow tracking server.

Disavle the authentification for tracking server:
```bash
enabled: true -> enabled: false
```

