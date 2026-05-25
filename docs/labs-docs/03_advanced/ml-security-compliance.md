# ML Security & Compliance Workshop

This advanced-level workshop covers security practices, governance frameworks, audit trails, and compliance requirements for production ML systems.

## Introduction

As machine learning systems move from experimentation to production, security and compliance become critical concerns. ML models introduce unique attack vectors—model poisoning, adversarial examples, data leakage—that traditional security practices don't fully address. At the same time, regulations like GDPR require organizations to provide explanations for automated decisions, maintain audit trails, and support data subject access requests.

In this workshop, you'll learn how to:


- Implement security controls for ML artifacts and pipelines
- Establish model governance frameworks with access control
- Build immutable audit trails for ML decision-making
- Generate compliance reports and model cards

## Overview of the Exercises

| Exercise | Topic | Key Skills |
|----------|-------|------------|
| 1 | Security Basics | Encryption, hashing, secure configuration |
| 2 | Governance Implementation | RBAC, model versioning, approval workflows |
| 3 | Audit Logging | Immutable logs, data provenance, querying |
| 4 | Compliance Reporting | GDPR, model cards, DSAR automation |

## Hands-On Sessions

Start with the security basics, then proceed through the exercises in order:

- [Exercise 1 - Security Basics](ml-security-compliance/01_security_basics.md)
- [Exercise 2 - Governance Implementation](ml-security-compliance/02_governance_implementation.md)
- [Exercise 3 - Audit Logging](ml-security-compliance/03_audit_logging.md)
- [Exercise 4 - Compliance Reporting](ml-security-compliance/04_compliance_reporting.md)

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
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.9+
- Basic understanding of MLflow and experiment tracking
- Familiarity with MLOps concepts from the beginner/intermediate workshops
- Access to an MLflow tracking server (for Exercise 2)

## Technologies Used

| Technology | Purpose |
|-----------|---------|
| [cryptography](https://cryptography.io/) | Encryption and hashing for ML artifacts |
| [MLflow](https://mlflow.org/) | Model registry, experiment tracking, governance |
| [Pandas](https://pandas.pydata.org/) | Data manipulation and report generation |
| [hashlib](https://docs.python.org/3/library/hashlib.html) | Secure hash generation for audit chains |
