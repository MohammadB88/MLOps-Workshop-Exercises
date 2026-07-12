# MLflow OAuth Proxy Architecture Diagram Prompt

Use this prompt with an AI diagram generator (e.g., Mermaid, PlantUML).

---

Create an architecture diagram for an MLflow deployment on OpenShift with the following setup:

The MLflow server runs as a **Deployment** in namespace `mlflow`. The pod contains two containers:
1. **MLflow container** (port 8443) — runs `mlflow server` with the `kubernetes-auth` app enabled (`MLFLOW_K8S_AUTH_AUTHORIZATION_MODE=self_subject_access_review`). Uses TLS certs from a shared secret `mlflow-tls`. Connects to a PVC for MLflow data (`/mlflow`).
2. **OAuth proxy container** (port 8444) — runs `ose-oauth-proxy` as a sidecar. It authenticates users via OpenShift OAuth using a pre-created `OAuthClient` resource (`mlflow-oauth-mlflow`). The proxy enforces a `SelfSubjectAccessReview` SAR check. Secrets for `client-secret` and `cookie-secret` come from a Kubernetes `Secret` (`mlflow-oauth-mlflow`).

Flow:
Browser -> HTTPS -> **OpenShift Route** (reencrypt TLS) -> **Service** (ClusterIP, port 8444) -> **OAuth proxy** (port 8444)
-> proxies authenticated requests via `--upstream=https://mlflow.mlflow.svc:8443` -> **MLflow container** (port 8443)

The MLflow server has `kubernetes-auth` authorization that does a Kubernetes `SelfSubjectAccessReview` on every API call using the caller's bearer token (forwarded by the OAuth proxy via `--pass-access-token`).

Also show:
- The `OAuthClient` cluster-scoped resource with its redirect URI pointing at the Route
- The `ServiceAccount` used by the pod
- The TLS cert coming from OpenShift service-ca-operator via annotation `service.beta.openshift.io/serving-cert-secret-name`

Output as a Mermaid.js diagram. Show the request flow step-by-step with numbered arrows.
