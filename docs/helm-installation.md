# Helm Installation

Helm is a package manager for Kubernetes that helps you define, install, and upgrade applications or components to be deployed on Kubernetes. For more details, visit the official Helm website: https://helm.sh.

One can install Helm by following these steps, according to the official Helm documentation ([install guide](https://helm.sh/docs/intro/install/)):

Download the Helm installation script from the official Helm GitHub repository.
```bash
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-4
```

Make the downloaded script executable so it can be run.
```bash
chmod 700 get_helm.sh
```

Run the installation script to install Helm on your machine.
```bash
./get_helm.sh
```
