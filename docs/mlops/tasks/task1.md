# Taks 1: Clone the Repository & Load and Explore the Data
In this task, we will clone the repository containing the workshop materials and explore the dataset for bike sharing company.

### 1. Fork the Repository
- Go to the original GitHub repository page.
- Click the **"Fork"** button in the top-right corner to create your own copy of the repo.

### 2. Generate an SSH Key
Run the following command in your terminal:

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### 3. Copy Your Public SSH Key
Copy the entire output (starts with ssh-ed25519) of this command.
```bash
cat ~/.ssh/id_ed25519.pub (i.g. cat /opt/app-root/src/.ssh/id_rsa.pub)
```

### 4. Add the SSH Key to GitHub
- Go to GitHub > Settings > SSH and GPG keys.
- Click "New SSH key".
- Paste your copied key and give it a descriptive title.

### 5. Clone Your Fork Using SSH
Clone the repository you forked in the first step.
```bash
git clone git@github.com:your-username/your-forked-repo.git
```


### 5. Download the Dataset into the Notebook 
The Data for bike sharing company can be found under this link. 

```bash
DATASET_URL: https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip
```

Please copy and paste this link into the appropriate section of the first Jupyter Notebook (`01_data_exploration.ipynb`).

Next, follow the Markdown instructions and execute each code cell to explore, clean, and preprocess the dataset. The final cleaned dataset will be saved in the
`data/processed` directory.
