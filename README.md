# Production MLOps Workshop: From Laptop to Cloud Native

[![GitHub Pages](https://img.shields.io/badge/docs-github_pages-blue)](https://mohammadb88.github.io/MLOps-Workshop-Exercises/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
<!-- [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md) -->
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
├── README.md                          # This file
├── ROADMAP.md                         # Project roadmap
├── LICENSE                            # MIT License
├── SECURITY.md                        # Security policy
├── zensical.toml                      # Zensical configuration
├── requirements.txt                   # Python dependencies
├── CLAUDE.md                          # AI assistant instructions
├── docs/
│   ├── index.md                       # Documentation homepage
│   ├── labs-docs/                     # Lab guides
│   │   ├── bike-demand-forecasting.md
│   │   ├── bike-forecasting/          # Step-by-step guides
│   │   ├── llm-instruction-tuning.md
│   │   └── llm-instruction-tuning/    # LLMOps step-by-step guides
│   ├── environment-requirement.md     # Environment setup
│   ├── git-cheatsheet.md              # Git reference
│   ├── helm-installation.md           # Helm installation guide
│   └── assets/                        # Images, CSS, JS
├── labs/
│   ├── 01_beginner/
│   │   └── 02_bike_demand_forecasting/
│   │       ├── notebooks/              # 6 Jupyter notebooks
│   │       ├── models/                 # FastAPI app, Containerfile
│   │       ├── data/                   # Gitignored
│   │       └── requirements.txt
│   └── 02_intermediate/
│       ├── 01_bike_demand_forecasting_pipeline/
│       │   ├── pipeline_bike_sharing.py  # Kubeflow pipeline
│       │   └── requirements.txt
│       └── 02_llm_instruction_tuning/
│           ├── notebooks/              # 6 Jupyter notebooks
│           ├── scripts/                # Helper scripts
│           ├── k8s/                    # Kubernetes manifests
│           ├── data/                   # Gitignored
│           ├── models/                 # Gitignored
│           ├── Dockerfile
│           └── requirements.txt
└── environment_preparations/           # Setup scripts and configs
```

---

## 📚 Workshop Structure

The workshop is organized into **two progressive skill levels**, each with focused learning materials and hands-on labs:

### 🟢 Beginner Level
*Start here if you're new to MLOps*

**Lab: Bike Demand Forecasting**
- **01 Data Exploration** - Load and explore UCI bike sharing dataset
- **02 Data Preparation** - Clean, preprocess, and split data
- **03 Model Training** - Train Random Forest with hyperparameter tuning
- **04 Model Registration** - Register best model in MLflow
- **05 Model Testing** - Test registered model via REST API
- **06 Model Monitoring** - Set up Evidently for drift detection

**Time Commitment:** 4-6 hours

---

### 🟡 Intermediate Level
*Build production-ready ML pipelines*

**Lab 1: Bike Demand Forecasting Pipeline**
- End-to-end Kubeflow pipeline with MLflow tracking
- Automated data processing and model training
- Hyperparameter optimization and model registration

**Lab 2: LLMOps Instruction Tuning**
- **01 Setup & Exploration** - Load base model (TinyLlama/Phi-2)
- **02 Data Preparation** - Format instruction dataset, tokenize
- **03 LoRA Tuning** - Train with LoRA/QLoRA, MLflow tracking
- **04 Evaluation** - Perplexity, qualitative assessment
- **05 Versioning & Packaging** - Register in MLflow, merge weights, containerize
- **06 Deployment & Serving** - Deploy to OpenShift/Kubernetes with vLLM

**Time Commitment:** 8-12 hours

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

## 🏃 Getting Started

**To access the full documentation with interactive navigation, visit:** [MLOps Workshop](https://mohammadb88.github.io/MLOps-Workshop-Exercises/)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/MohammadB88/MLOps-Workshop-Exercises.git
cd MLOps-Workshop-Exercises

# Install documentation dependencies
pip install -r requirements.txt

# Serve documentation locally
zensical serve
```

### Running the Labs

**Beginner Lab (Bike Demand Forecasting):**
```bash
cd labs/01_beginner/02_bike_demand_forecasting
pip install -r requirements.txt
jupyter lab
```

**Intermediate Lab (LLM Instruction Tuning):**
```bash
cd labs/02_intermediate/02_llm_instruction_tuning
pip install -r requirements.txt
jupyter lab
```

---

## 📖 Documentation

| Resource | Description |
|----------|-------------|
| [Workshop Site](https://mohammadb88.github.io/MLOps-Workshop-Exercises/) | Full interactive documentation |
| [Bike Forecasting Guide](docs/labs-docs/bike-demand-forecasting.md) | Beginner lab overview |
| [LLM Instruction Tuning](docs/labs-docs/llm-instruction-tuning.md) | Intermediate LLMOps lab |
| [Environment Setup](docs/environment-requirement.md) | Installation and configuration |
| [Git Cheatsheet](docs/git-cheatsheet.md) | Git reference guide |
| [Roadmap](ROADMAP.md) | Future plans and improvements |

<!-- ---

## 🎓 Learning Path

We recommend following this learning path:

```
1. Read MLOps Fundamentals → 2. Complete Beginner Labs
                    ↓
3. Study Deployment Concepts → 4. Complete Intermediate Labs
                    ↓
5. Learn CI/CD & Monitoring → 6. Complete Advanced Labs
                    ↓
         7. Build Your Own MLOps Project!
``` -->

<!-- **Estimated Total Time:** 25-30 hours for complete workshop -->

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
