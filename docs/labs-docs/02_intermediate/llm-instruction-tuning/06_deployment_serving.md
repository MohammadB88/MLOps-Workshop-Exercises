# Exercise 6: Deployment & Serving on OpenShift

In this exercise, you will deploy your fine-tuned LLM to OpenShift/Kubernetes using vLLM for optimized serving. You'll learn how to containerize your model, configure resource limits, and test the deployed service.

## Learning Objectives

By the end of this exercise, you will be able to:
- Containerize a fine-tuned LLM with vLLM for serving
- Configure Kubernetes deployment manifests for LLM serving
- Set appropriate resource limits and requests for LLM workloads
- Test and validate the deployed LLM endpoint
- Understand LLM serving lifecycle management concepts

## Prerequisites

Before starting this exercise, ensure you have:
1. Completed Exercise 5: Model Versioning & Packaging
2. A merged model available in the MLflow model registry or local models directory
3. Access to an OpenShift/Kubernetes cluster
4. The `oc` or `kubectl` CLI tools configured

## Step 1: Review the Dockerfile

Let's first examine the Dockerfile that will be used to containerize our LLM serving application:

```dockerfile
# Dockerfile for LLMOps Instruction Tuning Workshop
# Optimized for vLLM serving with fine-tuned models

FROM quay.io/modh/runtime-images:runtime-datascience-ubi9-python-3.11-20250703

# Set working directory
WORKDIR /app

# Install system dependencies
RUN dnf install -y git && \
    dnf clean all

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY scripts/ /app/scripts/
COPY models/ /app/models/

# Expose port for vLLM server
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - vLLM server
CMD ["python", "-m", "vllm.entrypoints.openai.api_server", \
     "--model", "/app/models/merged_model", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--dtype", "auto", \
     "--max-model-len", "2048"]
```

Key points about this Dockerfile:
- Uses the Red Hat runtime datascience image as base
- Installs dependencies from requirements.txt
- Copies scripts and models directories
- Exposes port 8000 for the vLLM server
- Includes a health check endpoint
- Runs vLLM's OpenAI-compatible API server as the default command

## Step 2: Build and Push the Container Image

If you haven't already built and pushed your container image from Exercise 5, you can do so now:

```bash
# Build the Docker image
docker build -t llm-instruction-tuning:latest .

# Tag for your registry (replace with your registry path)
docker tag llm-instruction-tuning:latest <your-registry>/llm-instruction-tuning:latest

# Push to registry
docker push <your-registry>/llm-instruction-tuning:latest
```

In the OpenShift AI environment, you might use the integrated registry:
```bash
# Login to OpenShift registry
oc login <openshift-cluster>
docker login -u $(oc whoami) -p $(oc whoami -t) <image-registry-path>

# Build and push
docker build -t <image-registry-path>/llm-instruction-tuning:latest .
docker push <image-registry-path>/llm-instruction-tuning:latest
```

## Step 3: Examine the Kubernetes Manifests

Let's look at the Kubernetes deployment and service manifests:

### Deployment Manifest (`k8s/deployment.yaml`)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-instruction-tuning-deployment
  labels:
    app: llm-instruction-tuning
spec:
  replicas: 1
  selector:
    matchLabels:
      app: llm-instruction-tuning
  template:
    metadata:
      labels:
        app: llm-instruction-tuning
    spec:
      containers:
      - name: llm-server
        image: <your-registry>/llm-instruction-tuning:latest
        ports:
        - containerPort: 8000
        env:
        - name: MODEL_NAME
          value: "TinyLlama-1.1B-Chat-v1.0"
        resources:
          requests:
            memory: "8Gi"
            cpu: "2"
          limits:
            memory: "16Gi"
            cpu: "4"
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 120
          periodSeconds: 20
```

### Service Manifest (`k8s/service.yaml`)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: llm-instruction-tuning-service
  labels:
    app: llm-instruction-tuning
spec:
  selector:
    app: llm-instruction-tuning
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: ClusterIP
```

Key considerations in these manifests:
- Resource requests and limits are crucial for LLM workloads
- Readiness and liveness probes ensure the container is healthy
- The service exposes the deployment internally in the cluster
- For external access, you would typically create a Route (OpenShift) or Ingress (Kubernetes)

## Step 4: Deploy to OpenShift/Kubernetes

Now let's deploy our LLM serving application:

```bash
# Create a namespace for our workshop (optional)
oc new-project llm-workshop --display-name="LLM Instruction Tuning Workshop"

# Apply the Kubernetes manifests
oc apply -f k8s/deployment.yaml
oc apply -f k8s/service.yaml

# Check the status of our deployment
oc get deployments
oc get pods
oc get services
```

## Step 5: Access the LLM Endpoint

Once the deployment is running, you can access the LLM endpoint:

### Option 1: Port Forwarding (for testing)
```bash
# Port forward to access the service locally
oc port-forward service/llm-instruction-tuning-service 8000:80

# Now you can access the API at http://localhost:8000/v1/chat/completions
```

### Option 2: Create a Route (OpenShift) or Ingress (Kubernetes)
For OpenShift:
```bash
oc expose svc/llm-instruction-tuning-service --hostname=llm-workshop.<your-domain>
```

For Kubernetes:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: llm-instruction-tuning-ingress
spec:
  rules:
  - host: llm-workshop.<your-domain>
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: llm-instruction-tuning-service
            port:
              number: 80
```

## Step 6: Test the Deployed LLM

Now let's test our deployed LLM using the test client we created earlier:

```bash
# If using port forwarding
python scripts/test_client.py --endpoint http://localhost:8000/v1/chat/completions

# If using a route/ingress
python scripts/test_client.py --endpoint https://llm-workshop.<your-domain>/v1/chat/completions
```

You can also test directly with curl:
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "TinyLlama-1.1B-Chat-v1.0",
    "messages": [{"role": "user", "content": "What is MLOps?"}],
    "max_tokens": 100
  }'
```

## Step 7: Monitor and Manage the Deployment

### Checking Logs
```bash
oc logs -f deployment/llm-instruction-tuning-deployment
```

### Scaling the Deployment
```bash
# Scale to 2 replicas for higher availability
oc scale deployment/llm-instruction-tuning-deployment --replicas=2
```

### Updating the Model
When you have a new version of your model:
1. Build a new container image with the updated model
2. Update the image in the deployment manifest
3. Apply the updated manifest:
   ```bash
   oc apply -f k8s/deployment.yaml
   ```

### Resource Monitoring
Monitor resource usage to ensure your requests and limits are appropriate:
```bash
oc top pods
```

## Key Concepts: Kubernetes-native LLM Serving

### Why Resource Management is Critical for LLMs
LLM serving workloads have unique resource characteristics:
- High memory usage for model weights and KV cache
- Variable CPU usage depending on batch size and sequence length
- GPU acceleration benefits significantly (when available)
- Cold start times can be long due to model loading

### LLM Serving Lifecycle Management
1. **Deployment**: Initial rollout of the LLM serving application
2. **Scaling**: Adjusting replica count based on demand
3. **Updating**: Rolling updates with new model versions
4. **Monitoring**: Tracking latency, throughput, and resource utilization
5. **Rollback**: Reverting to previous versions if issues arise
6. **Decommissioning**: Removing old model versions from serving

### Best Practices for LLM Serving on Kubernetes
1. **Set appropriate resource requests/limits** based on profiling
2. **Use readiness/liveness probes** to ensure healthy instances
3. **Consider GPU node selection** when GPUs are available
4. **Implement proper logging and monitoring**
5. **Use blue/green or canary deployments** for zero-downtime updates
6. **Consider model sharding** for very large models that don't fit on a single GPU

## Summary

In this exercise, you learned how to:
1. Containerize a fine-tuned LLM with vLLM for serving
2. Create Kubernetes deployment and service manifests
3. Deploy to OpenShift/Kubernetes with appropriate resource management
4. Access and test the deployed LLM endpoint
5. Monitor and manage the LLM serving lifecycle

These skills are essential for production LLM deployments, where reliability, scalability, and efficient resource utilization are paramount.

## Next Steps

- Experiment with different resource configurations to optimize cost/performance
- Try implementing autoscaling based on metrics like request latency or queue depth
- Explore advanced serving techniques like model quantization or continuous batching
- Set up monitoring dashboards for your LLM serving metrics