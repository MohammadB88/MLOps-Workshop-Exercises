# Production MLOps Workshop: From Laptop to Cloud Native

![MLOps Overview](docs/assets/github_banner_mlops.png)

[![GitHub Pages](https://img.shields.io/badge/docs-github_pages-blue)](https://mohammadb88.github.io/MLOps-Workshop-Exercises/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
 [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md) 
<!-- [![Stars](https://img.shields.io/github/stars/MohammadB88/MLOps-Workshop-Exercises?style=social)](https://github.com/MohammadB88/MLOps-Workshop-Exercises/stargazers) -->

 <!-- **Transform your machine learning models from Jupyter notebooks to production-ready systems.**

This comprehensive, hands-on workshop teaches you the essential practices, tools, and workflows for deploying and maintaining machine learning systems in production environments. -->

Learn to deploy, monitor, and maintain production ML systems through hands-on labs.

**The hard truth:** Building ML models is just a small portion of the work. The rest is getting them to production and keeping them there.

Research shows that most ML projects struggle to reach production. Only 53% of AI projects make it from prototype to production, while 77% of businesses cite "business adoption" as a major challenge. The gap between ML development and production deployment remains one of the biggest challenges in modern AI.

This workshop teaches you how to bring models from your laptop to a cloud-native environment. You'll learn everything needed to be production-ready - experiment tracking, containerization, Kubernetes deployment, pipeline automation, drift detection, and monitoring.

---

**What makes this different?**

- 🎯 **Production-first approach** - Real deployment scenarios on OpenShift/Kubernetes
- 🛠️ **Industry-standard tools** - MLflow, Kubeflow, Evidently, FastAPI, vLLM
- 📈 **Progressive learning** - Beginner to Intermediate in structured steps
- 🤖 **LLMOps included** - Modern LLM fine-tuning and deployment practices
- 🏢 **Enterprise-ready** - Designed for Red Hat OpenShift AI environment

---

## 🎯 What You'll Learn?

This workshop bridges the gap between machine learning development and production deployment. You'll gain practical experience with:

- **Experiment Tracking & Model Management** - Track experiments, version models, and manage the ML lifecycle with MLflow
- **Containerization & Orchestration** - Package models with Docker/Containerfile and deploy on Kubernetes/OpenShift
- **Pipeline Automation** - Build end-to-end ML pipelines with Kubeflow Pipelines
- **Production Monitoring** - Detect data drift and monitor model performance with Evidently AI
- **Model Serving** - Deploy models as REST APIs with FastAPI and vLLM
- **LLMOps Fundamentals** - Fine-tune LLMs with LoRA/QLoRA, version, and deploy to production

---

## 🚀 Who Is This For?

This workshop is designed for :

- **Data Scientists** transitioning to production ML systems
- **ML Engineers** looking to formalize MLOps practices
- **DevOps Engineers** expanding into ML operations
<!-- - **Software Engineers** working with ML teams
- **Students & Researchers** interested in production ML -->

### Prerequisites

- **Basic Python programming** (comfortable with Pandas, NumPy, scikit-learn)
- **Fundamental ML knowledge** (training/testing splits, model evaluation)
- **Git basics** (clone, commit, push/pull)
- **Docker fundamentals** (containers, images) - helpful but not required
- **Kubernetes basics** - helpful but not required
- **Jupyter Notebook experience** - for working with lab notebooks

---

## 📊 Repository Structure

```
MLOps-Workshop-Exercises/
├── .agents/skills/                    # Agent skill definitions
│   ├── ml-pipeline-workflow/
│   └── mlops-engineer/
├── docs/                              # Zensical documentation
│   ├── index.md                       # Home page
│   ├── mlops-overview.md              # MLOps theory overview
│   ├── workshop-overview.md           # Workshop structure
│   ├── environment-requirement.md
│   ├── redhat-demo-environment.md
│   ├── mlflow-installation.md
│   ├── helm-installation.md
│   ├── git-cheatsheet.md
│   ├── theory/introduction.md
│   ├── labs-docs/
│   │   ├── bike-demand-forecasting.md
│   │   ├── bike-demand-forecasting-pipeline.md
│   │   ├── wine-quality-classifier.md
│   │   ├── llm-instruction-tuning.md
│   │   ├── snippets/abbreviations.md
│   │   ├── tasks/                     # Task 1-9 guides
│   │   ├── 01_beginner/bike-forecasting/       # 9 step-by-step guides
│   │   ├── 02_intermediate/llm-instruction-tuning/  # 6 step-by-step guides
│   │   └── 03_advanced/
│   │       ├── kubeflow-advanced/     # 5 step-by-step guides
│   │       └── ml-security-compliance/ # 4 step-by-step guides
│   └── assets/                        # Images, CSS, JS
├── environment_preparations/
│   ├── helm_installtion.sh
│   ├── mlflow_installation.sh
│   ├── mlflow_odh_installation.sh
│   └── mlflow_route.ymal
├── labs/
│   ├── 01_beginner/
│   │   ├── bike_demand_forecasting/
│   │   │   ├── notebooks/                 # 6 Jupyter notebooks
│   │   │   │   └── data/test_model/       # Test datasets
│   │   │   ├── models/                    # FastAPI + Containerfile + k8s
│   │   │   └── models_cors/               # CORS-enabled variant
│   │   └── wine_quality_TODO/             # Placeholder for next lab
│   ├── 02_intermediate/
│   │   ├── bike_demand_forecasting_pipeline/  # Kubeflow pipeline
│   │   │   ├── pipeline_bike_sharing.py       # 6 components
│   │   │   ├── serve.py                       # FastAPI serving
│   │   │   ├── Containerfile                  # ubi9/python-311
│   │   │   ├── requirements.txt
│   │   │   ├── test_process_dataset.py        # Unit test
│   │   │   ├── k8s/deployment.yaml            # Deployment + Service
│   │   │   └── data/                          # raw/, processed/, test_model/
│   │   ├── llm_instruction_tuning/
│   │   │   ├── Dockerfile
│   │   │   ├── environment.yml                # Conda env definition
│   │   │   ├── requirements.txt
│   │   │   ├── README.md
│   │   │   ├── data/                          # Training datasets
│   │   │   ├── models/                        # Merged model output
│   │   │   ├── notebooks/             # 6 Jupyter notebooks
│   │   │   ├── scripts/               # mlflow_register.py, test_client.py, build_and_push.sh
│   │   │   └── k8s/                   # deployment.yaml, service.yaml
│   │   └── archive/bike_demand_forecasting_pipeline/  # Old 4-component version
│   └── 03_advanced/
│       ├── kubeflow_advanced/
│       │   ├── README.md
│       │   ├── requirements.txt
│       │   ├── scripts/pipeline_helpers.py
│       │   └── notebooks/            # 5 notebooks
│       └── ml_security_compliance/
│           ├── README.md
│           ├── requirements.txt
│           ├── scripts/audit_logger.py
│           └── notebooks/            # 4 notebooks
├── zensical.toml                     # Zensical site config
├── requirements.txt                  # Root: zensical==0.0.43
├── LICENSE                           # MIT License
├── README.md                         # Project overview
├── ROADMAP.md                        # Enhancement roadmap
├── SECURITY.md                       # Security policy
├── CLAUDE.md                         # AI assistant instructions
└── skills-lock.json                  # Agent skill registry
```

---

## 🛠️ Technology Stack

This workshop uses industry-standard tools:

| Category | Tools |
|----------|-------|
| **Experiment Tracking** | MLflow |
| **Containerization** | Docker, Containerfile |
| **Orchestration** | Kubernetes, OpenShift, Kubeflow Pipelines |
| **Monitoring** | Evidently AI |
| **Model Serving** | FastAPI, vLLM |
| **ML Frameworks** | scikit-learn, Hugging Face Transformers |
| **LLM Training** | PEFT (LoRA/QLoRA), bitsandbytes |
| **Documentation** | MkDocs Material Theme |
| **Languages** | Python, YAML |

---

## 📖 Documentation

| Resource | Description |
|----------|-------------|
| [Workshop Site](https://mohammadb88.github.io/MLOps-Workshop-Exercises/) | Full interactive documentation |
| [MLOps Overview](docs/mlops-overview.md) | MLOps theory and concepts |
| [Bike Forecasting Lab](docs/labs-docs/bike-demand-forecasting.md) | Beginner lab: 9 step-by-step guides |
| [Wine Quality Classifier](docs/labs-docs/wine-quality-classifier.md) | Beginner lab (placeholder) |
| [Bike Forecasting Pipeline](docs/labs-docs/bike-demand-forecasting-pipeline.md) | Intermediate Kubeflow pipeline lab |
| [LLM Instruction Tuning](docs/labs-docs/llm-instruction-tuning.md) | Intermediate LLMOps lab: 6 step-by-step guides |
| [Kubeflow Advanced](docs/labs-docs/03_advanced/kubeflow-advanced.md) | Advanced KFP lab: 5 step-by-step guides |
| [ML Security & Compliance](docs/labs-docs/03_advanced/ml-security-compliance.md) | Advanced security lab: 4 step-by-step guides |

---

## 🌟 Key Features

✅ **Hands-On Learning** - Every concept is reinforced with practical exercises

✅ **Production-Focused** - Real-world tools and deployment scenarios

✅ **Progressive Difficulty** - Structured path from basics to advanced

✅ **Open Source** - Free to use, modify, and contribute

✅ **Industry Tools** - Learn the same tools used by top tech companies

✅ **Comprehensive Documentation** - Clear guides and troubleshooting tips

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
Our community standards are outlined in the [Code of Conduct](CODE_OF_CONDUCT.md).

---

## 🙏 Acknowledgments

This workshop leverages the excellent work from:

- [MLflow](https://mlflow.org/) - Experiment tracking and model registry
- [Kubeflow](https://www.kubeflow.org/) - Pipeline orchestration
- [Evidently AI](https://www.evidentlyai.com/) - Model monitoring and drift detection
- [Hugging Face](https://huggingface.co/) - Transformers and PEFT libraries
- [vLLM](https://vllm.ai/) - Optimized LLM serving
- [Red Hat OpenShift](https://www.redhat.com/en/technologies/cloud-computing/openshift) - Kubernetes platform
- The open-source MLOps community

Special thanks to all [contributors](https://github.com/MohammadB88/MLOps-Workshop-Exercises/graphs/contributors) who have helped improve this workshop!

---

## 📞 Contact & Support

- **Author:** Mohammad Bahmani
- **GitHub:** [@MohammadB88](https://github.com/MohammadB88)
- **Workshop Site:** [https://mohammadb88.github.io/MLOps-Workshop-Exercises/](https://mohammadb88.github.io/MLOps-Workshop-Exercises/)

For questions or issues, please [open an issue](https://github.com/MohammadB88/MLOps-Workshop-Exercises/issues) on GitHub.

---

<div align="center">

**Ready to master MLOps?** [Start Learning →](https://mohammadb88.github.io/MLOps-Workshop-Exercises/)

</div>
