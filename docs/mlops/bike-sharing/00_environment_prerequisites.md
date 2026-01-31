# 0: Environment and Prerequisites

## Objective
In this lab, we will:

* make ourselves familiar with the environment
* clone the repository containing the workshop materials

## Guide

### Step 1 - Access the Environment
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
Run the following command in your terminal:

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### Copy your public SSH key
Copy the entire output (starts with ssh-ed25519) of this command.
```bash
cat ~/.ssh/id_ed25519.pub (i.g. cat /opt/app-root/src/.ssh/id_rsa.pub)
```

### Add the SSH Key to your GitHub Account
- Go to GitHub > Settings > SSH and GPG keys.
- Click "New SSH key".
- Paste your copied key and give it a descriptive title.

### Clone your Fork Using SSH-URL and Stored SSH-Key
Copy the URL of the forked repository
![Clone Repo SSH Github](images/clone_repo_ssh_github.png)

and use `git` to download the code:
```bash
git clone git@github.com:your-username/your-forked-repo.git
```

