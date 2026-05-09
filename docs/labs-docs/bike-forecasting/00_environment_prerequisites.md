# 0: Environment and Prerequisites

## Objective
In this lab, we will:

* make ourselves familiar with the environment
* clone the repository containing the workshop materials

## Guide

### Step 1 - Access the Environment
<<<<<<< HEAD:docs/labs-docs/bike-forecasting/00_environment_prerequisites.md
You will be provided a link and necessary credentials to an OpenShift AI instance with a ready workbench including *JupyterLab*. 

### Step 2a - Clone the Repository - HTTPs-URL

Go to the original GitHub repository page and copy the the URL of the repo:

![Clone Repo Github](../../assets/images/clone_repo_github.png)

#### Open the created workbench
At the left panel, you can click on git-icon shown in the below image and select `Clone a Repository`.

![Clone Repo](../../assets/images/clone_repo.png)
<!-- 
Copy the URL of the original repo  repository:

![Clone Repo Github](../../assets/images/clone_repo_github.png) -->

paste the copied URL from original repo and click on ``clone`` to download the code inside the jupyterlab:

![Clone Repo - add url](../../assets/images/clone_repo_url.png)

Go to the path `MLOps-Workshop-Exercises/workshop_materials/`, where you find the workshop materials.


### Step 2b - Clone the Repository - SSH-URL
In case you are going to clone the repo from a terminal, use below instructions:

#### Generate an SSH key
=======
TODO

### Step 2 - Fork the Repository
- Go to the original GitHub repository page.
- Click the **"Fork"** button in the top-right corner to create your own copy of the repo.

### Step 3 - Clone the Repository - HTTPs-URL

### Open the created workbench
At the left panel, you can click on git-icon shown in the below image and select `Clone a Repository`.

![Clone Repo](images/clone_repo.png)

Copy the URL of the forked repository:

![Clone Repo Github](images/clone_repo_github.png)

and click on clone to download the code:

![Clone Repo - add url](images/clone_repo_url.png)

Go to the path `MLOps-Workshop-Exercises/workshop_materials/`, where you find the workshop materials.

✅ **At this point, we are ready to go to the next exercise** [Load, Extract, and Clean the Data](./01_load_extract_clean_data.md).


# ----------------------------------------------------------------------------------
### In case you are going to clone the repo from a terminal, use below instructions
### Step 4 - Clone the Repository - SSH-URL
# ----------------------------------------------------------------------------------

### Generate an SSH key
>>>>>>> main:docs/mlops/bike-sharing/00_environment_prerequisites.md
Run the following command in your terminal:

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

<<<<<<< HEAD:docs/labs-docs/bike-forecasting/00_environment_prerequisites.md
#### Copy your public SSH key
=======
### Copy your public SSH key
>>>>>>> main:docs/mlops/bike-sharing/00_environment_prerequisites.md
Copy the entire output (starts with ssh-ed25519) of this command.
```bash
cat ~/.ssh/id_ed25519.pub (i.g. cat /opt/app-root/src/.ssh/id_rsa.pub)
```

<<<<<<< HEAD:docs/labs-docs/bike-forecasting/00_environment_prerequisites.md
#### Add the SSH Key to your GitHub Account
=======
### Add the SSH Key to your GitHub Account
>>>>>>> main:docs/mlops/bike-sharing/00_environment_prerequisites.md
- Go to GitHub > Settings > SSH and GPG keys.
- Click "New SSH key".
- Paste your copied key and give it a descriptive title.

<<<<<<< HEAD:docs/labs-docs/bike-forecasting/00_environment_prerequisites.md
#### Clone the repo using SSH-URL and stored SSH-Key
Copy the URL of the repository
![Clone Repo SSH Github](../../assets/images/clone_repo_ssh_github.png)
=======
### Clone your Fork Using SSH-URL and Stored SSH-Key
Copy the URL of the forked repository
![Clone Repo SSH Github](images/clone_repo_ssh_github.png)
>>>>>>> main:docs/mlops/bike-sharing/00_environment_prerequisites.md

and use `git` to download the code:
```bash
git clone git@github.com:your-username/your-forked-repo.git
```

<<<<<<< HEAD:docs/labs-docs/bike-forecasting/00_environment_prerequisites.md
✅ **At this point, we are ready to go to the next exercise** [Load, Extract, and Clean the Data](./01_load_extract_clean_data.md).



=======
>>>>>>> main:docs/mlops/bike-sharing/00_environment_prerequisites.md
