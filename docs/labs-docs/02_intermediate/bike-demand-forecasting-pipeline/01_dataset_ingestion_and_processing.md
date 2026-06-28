# 01_dataset_ingestion_and_processing.md

## Dataset Ingestion and Processing

In this step, we automate the collection and preparation of the bike sharing dataset using two Kubeflow components: `get_dataset` and `process_dataset`.

### 1. Get Dataset Component
The `get_dataset` component handles the initial data acquisition.
- **Action**: Downloads the `bike+sharing+dataset.zip` from the UCI repository.
- **Validation**: Checks if the file exists and verifies that the expected columns (`instant`, `dteday`, `season`, etc.) are present.
- **Output**: Saves the raw `hour.csv` file for the next component.

### 2. Process Dataset Component
The `process_dataset` component transforms the raw data into a format suitable for distributed training.
- **Cleaning**: Renames columns for better readability (e.g., `yr` $\rightarrow$ `year`, `mnth` $\rightarrow$ `month`).
- **Splitting**: Splits the data into 12 monthly CSV files. This allows for easier data management and potential parallelization.
- **Output**: Packages all monthly CSVs into a ZIP archive to be passed to the training component.

### Verification
After running these components in the pipeline, you should see:
- A raw CSV artifact from the first step.
- A processed ZIP artifact containing 12 CSV files from the second step.
