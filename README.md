<!-- # MLOps-Workshop-Exercises

This repository contains all exercise descriptions for my MLOps Workshop, utilizing the Red Hat demo environment. The exercises are build with MkDocs and published to Githun pages. 

The Workshop can be found at this link: https://mohammadb88.github.io/MLOps-Workshop-Exercises/

**There is a Roadmap for this project:** [Roadmap](./ROADMAP.md) -->

<!-- # MLOps Workshop - From Development to Production -->
<!-- # Production MLOps Workshop: From Jupyter to Kubernetes -->
# Production MLOps Workshop: From Laptop to Cloud Native

[![GitHub Pages](https://img.shields.io/badge/docs-github_pages-blue)](https://mohammadb88.github.io/MLOps-Workshop-Exercises/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
<!-- [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md) -->
<!-- [![Stars](https://img.shields.io/github/stars/MohammadB88/MLOps-Workshop-Exercises?style=social)](https://github.com/MohammadB88/MLOps-Workshop-Exercises/stargazers) -->

 <!-- **Transform your machine learning models from Jupyter notebooks to production-ready systems.**

This comprehensive, hands-on workshop teaches you the essential practices, tools, and workflows for deploying and maintaining machine learning systems in production environments. -->

Learn to deploy, monitor, and maintain production ML systems through hands-on labs.

**The hard truth:** Building ML models is just small portion of the work. The rest is 
getting them to production and keeping them there. TODO: ADD PAPER about HIDDEN ... []()

Research shows that most ML projects struggle to reach production. 
TODO: [Gartner](GARTNER STUDIES) found that only 53% of AI projects make it from prototype to production, 
while 77% of businesses cite "business adoption" as a major challenge. The gap 
between ML development and production deployment remains one of the biggest 
challenges in modern AI.

This workshop teaches you how to bring the models from your laptop to a cloud native environment. In other words,  everything you need to be production-ready - experiment tracking, containerization, Kubernetes deployment, CI/CD automation, drift detection, and monitoring.

---

**What makes this different?**

- 🎯 **Production-first approach** - No toy examples, real deployment scenarios
- 🛠️ **Industry-standard tools** - MLflow, Docker, Kubernetes, Evidently
- 📈 **Progressive learning** - Beginner to Advanced in structured steps
<!-- - 🏢 **Enterprise-ready** - Learn patterns used by top tech companies
- 🤝 **Open & Free** - Community-driven, always accessible -->

---

## 🎯 What You'll Learn?

This workshop bridges the gap between machine learning development and production deployment. You'll gain practical experience with:

- **Experiment Tracking & Model Management** - Track experiments, version models, and manage the ML lifecycle
<!-- - **Data Version Control** - Handle large datasets and ensure reproducibility with DVC -->
- **Containerization & Orchestration** - Package models with Docker and deploy on Kubernetes/OpenShift
- **CI/CD for ML** - Automate testing, training, and deployment pipelines
- **Production Monitoring** - Detect data drift, monitor model performance, and trigger retraining
<!-- - **MLOps Best Practices** - Apply industry-standard patterns for scalable ML systems -->

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

---

## 📊 Repository Structure

```
MLOps-Workshop-Exercises/
├── README.md                          # Enhanced with introduction
├── ROADMAP.md                         # This file
├── CODE_OF_CONDUCT.md                 # TODO: Community standards 
├── CONTRIBUTING.md                    # TODO: Contribution guidelines
├── LICENSE                            # Project license
├── SECURITY.md                        # Security policy
├── mkdocs.yml                         # GitHub Pages main yaml file
├── docs/
│   ├── learning-materials/           # Theory and concepts
│   │   ├── 01-mlops-fundamentals.md
│   │   ├── 02-ml-lifecycle.md
│   │   ├── 03-experiment-tracking.md
│   │   ├── 04-model-deployment.md
│   │   ├── 05-monitoring-maintenance.md
│   │   ├── 06-data-versioning.md
│   │   ├── 07-cicd-for-ml.md
│   │   └── 08-llmops-intro.md
│   ├── environment-requirement/      # Setup guides (existing)
│   └── assets/                       # Images and resources
├── labs/                             # ??? Labs or Workshop Materials
│   ├── beginner/
│   │   ├── 01_wine_quality_TODO/
│   │   │   ├── ?notebook.ipynb
│   │   │   ├── ?solution.ipynb
│   │   │   └── ?data/
│   │   └── 02_bike_demand_forecasting/
│   │   │   ├── ?notebook.ipynb
│   │   │   ├── ?solution.ipynb
│   │   │   ├── tutorial.md
│   │   │   └── sample-data/
│   ├── intermediate/
│   │   ├── 01_bike_demand_forecasting_pipeline/
│   │   │   ├── README.md
│   │   │   ├── 01-data-prep.ipynb
│   │   │   ├── 02-training.ipynb
│   │   │   ├── 03-evaluation.ipynb
│   │   │   └── mlflow-setup.md
│   │   └── 02_CICD_pipeline_TODO/
│   │       ├── README.md
│   │       ├── api/
│   │       ├── Dockerfile
│   │       ├── k8s/
│   │       └── tests/
│   └── advanced/
│       ├── 01_TODO_cicd-ml-pipeline/
│       │   ├── README.md
│       │   ├── .github/workflows/
│       │   ├── tests/
│       │   └── scripts/
│       └── 02_TODO_monitoring-drift-detection/
│           ├── README.md
│           ├── monitoring-setup.ipynb
│           ├── evidently-config/
│           └── dashboards/
├── workshop_materials/               # Existing materials
└── sample-mkdocs/                    # MkDocs setup (existing)
```

---

## 📚 Workshop Structure

The workshop is organized into **three progressive skill levels**, each with focused learning materials and hands-on labs:

### 🟢 Beginner Level
*Start here if you're new to MLOps*
<!-- 
**Learning Materials:**
- MLOps fundamentals and lifecycle
- Experiment tracking concepts
- ???
- Introduction to data versioning -->

**Labs:**
1. **Wine Quality Classifier** - Train and track a simple ML model with MLflow
2. **Bike Sharing Forecast** - TODO
<!-- 2. **Data Versioning with DVC** - Version control for datasets and reproducibility -->

<!-- **Time Commitment:** ???4-6 hours -->

---

### 🟡 Intermediate Level
*Build production-ready ML pipelines*

<!-- **Learning Materials:**
- Model deployment strategies
- Containerization for ML
- REST API design for models -->

**Labs:**
1. **Bike Demand Forecasting Pipeline** - TODO: End-to-end pipeline with experiment tracking
2. **TODO** - TODO

<!-- **Time Commitment:** 8-10 hours -->

---

### 🔴 Advanced Level
*Implement enterprise MLOps practices*
<!-- 
**Learning Materials:**
- CI/CD for machine learning
- Model monitoring and drift detection
- Production best practices -->

**Labs:**
1. **TODO** - TODO

<!-- **Time Commitment:** 10-12 hours -->

---

## 🛠️ Technology Stack

This workshop uses industry-standard tools:

| Category | Tools |
|----------|-------|
| **Experiment Tracking** | MLflow |
| **Data Versioning** | ???DVC (Data Version Control) |
| **Containerization** | Docker |
| **Orchestration** | Kubernetes, OpenShift |
| **CI/CD** | ???GitHub Actions |
| **Monitoring** | Evidently, Prometheus, Grafana |
| **Model Serving** | ???FastAPI / Flask |
| **Languages** | Python, YAML |

---

## 🏃 Starting Point OR Where to Start?

<!-- ### 1. Clone the Repository

```bash
git clone https://github.com/MohammadB88/MLOps-Workshop-Exercises.git
cd MLOps-Workshop-Exercises
``` -->

<!-- ### 2. Set Up Your Environment??? -->
<!-- MAYBE just REFER to the Environment Section -->

<!-- ```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
``` -->

<!-- ### 3. Start with Beginner Labs

Navigate to the [learning materials](docs/learning-materials/) and begin with the fundamentals, then proceed to [Lab 1: Wine Quality Classifier](labs/beginner/01-wine-quality-basic/). -->
<!-- 
### 4.  -->
**To access the full documentation with interactive navigation, visit :**  [Main Page for MLOps Workshop](https://mohammadb88.github.io/MLOps-Workshop-Exercises/) 

<!-- for the complete workshop with interactive navigation. -->

---

## 📖 Documentation 

| Resource | Description |
|----------|-------------|
| [Learning Materials](docs/learning-materials/) | Theory, concepts, and best practices |
| [Beginner Labs](labs/beginner/) | Foundational MLOps skills |
| [Intermediate Labs](labs/intermediate/) | Production pipelines and deployment |
| [Advanced Labs](labs/advanced/) | CI/CD and monitoring |
| [Environment Setup](docs/environment-requirement/) | Installation and configuration guides |
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

<!-- ---

## 🤝 Contributing

We welcome contributions! Whether you want to:

- Fix a bug or typo
- Improve documentation
- Add a new lab or example
- Share your MLOps experience

Please read our [Contributing Guidelines](CONTRIBUTING.md) to get started.

### Ways to Contribute

- 🐛 **Report bugs** - Open an issue with details
- 💡 **Suggest features** - Share your ideas for improvements
- 📝 **Improve docs** - Help make content clearer
- 🧪 **Add labs** - Create new exercises and examples
- ⭐ **Star the repo** - Show your support! -->

<!-- ---

## 📣 Community

- **GitHub Discussions:** Ask questions, share experiences, get help
- **Issues:** Report bugs or request features
- **Pull Requests:** Contribute improvements -->

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

This workshop leverages the excellent work from:

<!-- - [MLflow](https://mlflow.org/) - Experiment tracking and model registry
- [DVC](https://dvc.org/) - Data version control
- [Evidently AI](https://www.evidentlyai.com/) - Model monitoring
- [Red Hat OpenShift](https://www.redhat.com/en/technologies/cloud-computing/openshift) - Kubernetes platform
- The open-source MLOps community -->

Special thanks to all [contributors](https://github.com/MohammadB88/MLOps-Workshop-Exercises/graphs/contributors) who have helped improve this workshop!

---

## 📞 Contact & Support

- **Author:** Mohammad Bahmani
- **GitHub:** [@MohammadB88](https://github.com/MohammadB88)
- **Workshop Site:** [https://mohammadb88.github.io/MLOps-Workshop-Exercises/](https://mohammadb88.github.io/MLOps-Workshop-Exercises/)

For questions or issues, please [open an issue](https://github.com/MohammadB88/MLOps-Workshop-Exercises/issues) on GitHub.

<!-- ---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=MohammadB88/MLOps-Workshop-Exercises&type=Date)](https://star-history.com/#MohammadB88/MLOps-Workshop-Exercises&Date) -->

---

<div align="center">

**Ready to master MLOps?** [Start Learning →](https://mohammadb88.github.io/MLOps-Workshop-Exercises/)

<!-- Made with ❤️ by the MLOps community -->

</div>
