# ML Security & Compliance

An advanced MLOps lab covering security threats, model governance, audit logging, and regulatory compliance for machine learning systems.

## Learning Objectives

- Identify and mitigate ML-specific security threats (model poisoning, adversarial examples, data leakage)
- Apply encryption and hashing to protect ML artifacts
- Implement role-based access control (RBAC) for model registries
- Manage model versioning and approval workflows with stage transitions
- Build audit trails for ML system accountability
- Understand GDPR compliance requirements (Right to Explanation, Right to Erasure)
- Generate Model Cards and compliance reports

## Prerequisites

- Python 3.9+
- Jupyter Notebook or Jupyter Lab
- MLflow tracking server (local or remote)
- Basic understanding of MLOps concepts
- Familiarity with scikit-learn and pandas

## Directory Structure

```
ml_security_compliance/
├── notebooks/
│   ├── 01_security_basics.ipynb
│   ├── 02_governance_implementation.ipynb
│   ├── 03_audit_logging.ipynb
│   └── 04_compliance_reporting.ipynb
├── scripts/
│   └── audit_logger.py
├── README.md
└── requirements.txt
```

## Exercise Descriptions

### 01 - Security Basics
Introduction to ML security threats. Covers file hashing for integrity verification, symmetric encryption of model artifacts, and secure configuration management with environment variables.

### 02 - Governance Implementation
Model governance framework with MLflow. Covers experiment tagging, RBAC simulation, model registry stage transitions (Staging → Production), and approval workflows.

### 03 - Audit Logging
Building an audit trail for ML systems. Covers event logging with timestamps, filtered queries, JSON/CSV export, and immutable hash-chained audit logs.

### 04 - Compliance Reporting
GDPR and regulatory compliance. Covers Right to Explanation (feature importance), Data Subject Access Request (DSAR) simulation, Model Card generation, and compliance report templates.

## Technologies Used

| Technology | Purpose |
|------------|---------|
| Python cryptography | Fernet symmetric encryption |
| hashlib | SHA-256 file hashing |
| MLflow | Model registry, experiment tracking, stage transitions |
| pandas / numpy | Data handling and simulation |
| JSON | Audit log and report serialization |

## Usage

```bash
pip install -r requirements.txt
jupyter lab
```

Open notebooks in order: `01_security_basics.ipynb` through `04_compliance_reporting.ipynb`.
