# 📌 Project Roadmap

This roadmap outlines the planned features and improvements for the project.

## ✅ Completed

- [x] Initial project setup
- [x] Documentations about MLOps are added


## 🚧 In Progress

- [ ] Add a CD pipeline to package the trained model, generate the image, and update the deployment
    - [ ] Data Scientists indicate the model version and pipeline should take the model directly from the remote MLflow server
    - [ ] first version could be that to define the model loading (ENV for model Version and MLflow-Server) in the Containerfile
    - [ ] Create the Container-Image and the model_api_app to accept the mlflow and model version as ENV-Variable, then I do not have to build the image each time
- [ ] 
- [ ] 

## 🗓️ Upcoming

- [ ] Implement API-endpoints from other model providers like watsonx.ai, NVIDIA NIM, ...

