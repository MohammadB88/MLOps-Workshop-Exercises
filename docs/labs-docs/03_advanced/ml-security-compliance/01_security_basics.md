# Exercise 1: Security Basics

## Objective

In this exercise, you will:
1. Set up encryption libraries for securing ML artifacts
2. Generate and manage encryption keys for model files
3. Encrypt and decrypt model artifacts programmatically
4. Compute and verify file hashes for integrity checks
5. Apply secure configuration management best practices

## Prerequisites

- Python 3.9+ installed
- The `cryptography` and `hashlib` libraries installed
- A trained model file (e.g., `model.pkl`) from a previous exercise
- Basic understanding of symmetric encryption concepts

## Step 1: Setting Up Encryption Libraries

First, install and import the necessary cryptographic libraries:

```python
import hashlib
import json
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

# Verify installation
print(f"Fernet ready: {Fernet is not None}")
```

## Step 2: Generating Encryption Keys

Create a key management function to generate and store encryption keys:

```python
KEY_FILE = "model_encryption.key"


def generate_key() -> bytes:
    """Generate a Fernet-compatible symmetric key."""
    key = Fernet.generate_key()
    return key


def save_key(key: bytes, path: str = KEY_FILE):
    """Persist key to disk with restricted permissions."""
    with open(path, "wb") as f:
        f.write(key)
    os.chmod(path, 0o600)  # Owner read/write only
    print(f"Key saved to {path}")


def load_key(path: str = KEY_FILE) -> bytes:
    """Load key from disk."""
    with open(path, "rb") as f:
        return f.read()


# Generate and save a key
key = generate_key()
save_key(key)
print(f"Key: {key.decode()[:20]}...")
```

## Step 3: Encrypting and Decrypting a Model File

Encrypt a trained model artifact so it can be stored or transmitted securely:

```python
def encrypt_file(input_path: str, output_path: str, key: bytes):
    """Encrypt a file using Fernet symmetric encryption."""
    fernet = Fernet(key)
    with open(input_path, "rb") as f:
        file_data = f.read()
    encrypted_data = fernet.encrypt(file_data)
    with open(output_path, "wb") as f:
        f.write(encrypted_data)
    print(f"Encrypted: {input_path} -> {output_path}")


def decrypt_file(input_path: str, output_path: str, key: bytes):
    """Decrypt a file using Fernet symmetric encryption."""
    fernet = Fernet(key)
    with open(input_path, "rb") as f:
        encrypted_data = f.read()
    decrypted_data = fernet.decrypt(encrypted_data)
    with open(output_path, "wb") as f:
        f.write(decrypted_data)
    print(f"Decrypted: {input_path} -> {output_path}")


# Example usage
# encrypt_file("model.pkl", "model.pkl.encrypted", key)
# decrypt_file("model.pkl.encrypted", "model_decrypted.pkl", key)
```

## Step 4: Computing and Verifying File Hashes

Use hashing to verify file integrity and detect tampering:

```python
def compute_file_hash(file_path: str, algorithm: str = "sha256") -> str:
    """Compute the hash of a file."""
    h = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_file_hash(file_path: str, expected_hash: str,
                     algorithm: str = "sha256") -> bool:
    """Verify a file matches an expected hash."""
    actual_hash = compute_file_hash(file_path, algorithm)
    is_valid = actual_hash == expected_hash
    print(f"Hash match: {is_valid}")
    return is_valid


# Compute hashes for a model and its encrypted version
original_hash = compute_file_hash("model.pkl")
encrypted_hash = compute_file_hash("model.pkl.encrypted")
print(f"SHA256 of model.pkl:        {original_hash}")
print(f"SHA256 of model.pkl.enc:    {encrypted_hash}")

# Verify integrity
assert verify_file_hash("model.pkl", original_hash)
```

## Step 5: Secure Configuration Management

Store sensitive configuration values like API endpoints and access keys securely:

```python
from cryptography.fernet import Fernet


class SecureConfig:
    """Manages sensitive configuration with in-memory encryption."""

    def __init__(self, key: bytes):
        self._fernet = Fernet(key)
        self._config: dict[str, bytes] = {}

    def set(self, key: str, value: str):
        """Store a value in encrypted form."""
        self._config[key] = self._fernet.encrypt(value.encode())

    def get(self, key: str) -> str:
        """Retrieve and decrypt a stored value."""
        if key not in self._config:
            raise KeyError(f"Key '{key}' not found")
        return self._fernet.decrypt(self._config[key]).decode()

    def list_keys(self) -> list[str]:
        """List stored configuration keys (not values)."""
        return list(self._config.keys())


# Example usage
config = SecureConfig(key)
config.set("MLFLOW_TRACKING_URI", "http://mlflow-server:5000")
config.set("MODEL_REGISTRY_URL", "https://registry.internal:443")

print(f"Stored keys: {config.list_keys()}")
print(f"Tracking URI: {config.get('MLFLOW_TRACKING_URI')}")
```

## Summary

In this exercise, you:
1. Set up `cryptography` and `hashlib` for encrypting ML artifacts
2. Generated and persisted symmetric encryption keys
3. Encrypted and decrypted model files using Fernet
4. Computed SHA-256 file hashes for integrity verification
5. Implemented a secure configuration manager for sensitive settings

---

<div style="display: flex; justify-content: flex-end;">
<a href="../02_governance_implementation/" class="md-button">Next →</a>
</div>
