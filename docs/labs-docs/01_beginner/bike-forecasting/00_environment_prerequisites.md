# Exercise 0: Environment and Prerequisites

## Objective
In this lab, we will:

* make ourselves familiar with the environment
* clone the repository containing the workshop materials

!!! tip "MLOps Perspective"
    Why this matters in an MLOps workflow: Setting up a reproducible environment is the foundation of any MLOps pipeline.

## Prerequisites

- Access to an OpenShift AI JupyterLab environment

## Step 1: Access the Environment
You will be provided a link and necessary credentials to an OpenShift AI instance with a ready workbench including *JupyterLab*. 

## Step 2: Clone the Repository

Choose one of the following methods:

### Option A: HTTPS URL

Go to the original GitHub repository page and copy the the URL of the repo:

![Clone Repo Github](../../../assets/images/clone_repo_github.png)

#### Open the created workbench
At the left panel, you can click on git-icon shown in the below image and select `Clone a Repository`.

![Clone Repo](../../../assets/images/clone_repo.png)
<!-- 
Copy the URL of the original repo  repository:

![Clone Repo Github](../../../assets/images/clone_repo_github.png) -->

paste the copied URL from original repo and click on ``clone`` to download the code inside the jupyterlab:

![Clone Repo - add url](../../../assets/images/clone_repo_url.png)

Go to the path `MLOps-Workshop-Exercises/workshop_materials/`, where you find the workshop materials.

### Option B: SSH URL
In case you are going to clone the repo from a terminal, use below instructions:

#### Generate an SSH key
Run the following command in your terminal:

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

#### Copy your public SSH key
Copy the entire output (starts with ssh-ed25519) of this command.
```bash
cat ~/.ssh/id_ed25519.pub (i.g. cat /opt/app-root/src/.ssh/id_rsa.pub)
```

#### Add the SSH Key to your GitHub Account
- Go to GitHub > Settings > SSH and GPG keys.
- Click "New SSH key".
- Paste your copied key and give it a descriptive title.

#### Clone the repo using SSH-URL and stored SSH-Key
Copy the URL of the repository
![Clone Repo SSH Github](../../../assets/images/clone_repo_ssh_github.png)

and use `git` to download the code:
```bash
git clone git@github.com:your-username/your-forked-repo.git
```

## Summary

In this exercise, you:

1. Accessed the OpenShift AI JupyterLab environment
2. Cloned the workshop repository using HTTPS or SSH
3. Verified the repository structure and workshop materials

---

