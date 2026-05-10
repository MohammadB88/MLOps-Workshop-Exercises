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