# Import necessary modules and libraries
import os
import zipfile
import requests

import pandas as pd

import matplotlib.pyplot as plt
import seaborn as sns


##################################################################################################
# Download and extract the bike sharing dataset from UCI Machine Learning Repository
# This dataset contains hourly data of bike rentals in Washington, D.C. from 2011 to 2012
# It includes features such as temperature, humidity, wind speed, and weather conditions.
# Define URLs and paths
dataset_url = "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"
data_dir = "./data"
raw_dir = os.path.join(data_dir, "raw")

# Create directories if they don't exist
os.makedirs(raw_dir, exist_ok=True)

# Download the dataset
zip_path = os.path.join(raw_dir, "bike_sharing_dataset.zip")
if not os.path.exists(zip_path):
    response = requests.get(dataset_url)
    with open(zip_path, "wb") as f:
        f.write(response.content)
    print("Dataset downloaded successfully.")
else:
    print("Dataset already exists.")

# Extract the dataset
with zipfile.ZipFile(zip_path, "r") as zip_ref:
    zip_ref.extractall(raw_dir)
    print("Dataset extracted successfully.")

##################################################################################################
# Basic data preprocessing
# Load the dataset
hour_path = os.path.join(raw_dir, "hour.csv")
df = pd.read_csv(hour_path, header=0, sep=',', parse_dates=['dteday'], index_col='dteday')

# Display the first few rows
# df.head()

# Clean the dataset
# Convert categorical variables to appropriate types
# Check for missing values
missing_values = df.isnull().sum()
print("Missing values in each column:\n", missing_values)

# Rename columns
df.rename(columns={
    'yr': 'year',
    'mnth': 'month',
    'hr': 'hour',
    'hum': 'humidity',
    'cnt': 'count'
}, inplace=True)

# Display the first few rows of the processed dataset
# df.head()

# Plot some basic statistics about the dataset
# Set plot style
sns.set(style="whitegrid")
os.makedirs("plots", exist_ok=True)

# Distribution of bike rentals
plt.figure(figsize=(10, 6))
sns.histplot(df['count'], bins=30, kde=True)
plt.title("Distribution of Bike Rentals")
plt.xlabel("Count")
plt.ylabel("Frequency")
plt.savefig("plots/distribution_bike_rentals.png", dpi=300, bbox_inches='tight')  
# save plt.show()


# Bike rentals by hour
plt.figure(figsize=(12, 6))
sns.boxplot(x='hour', y='count', data=df)
plt.title("Bike Rentals by Hour")
plt.xlabel("Hour of the Day")
plt.ylabel("Count")
plt.savefig("plots/bike_rentals_by_hour.png", dpi=300, bbox_inches='tight')
# plt.show()

# Correlation heatmap
plt.figure(figsize=(10, 8))
corr = df[['temp', 'atemp', 'humidity', 'windspeed', 'count']].corr()
sns.heatmap(corr, annot=True, cmap='coolwarm')
plt.title("Correlation Heatmap")
plt.savefig("plots/correlation_heatmap.png", dpi=300, bbox_inches='tight')
# plt.show()

##################################################################################################
# Save the processed data to CSV files for each month
# This will create a separate CSV file for each month in the dataset
# Set the start date to the beginning of your data
start_date = df.index.min().replace(day=1, hour=0, minute=0, second=0)
end_date = df.index.max()

data_dir ="./data"
processed_dir = os.path.join(data_dir, "processed")

# Create directories if they don't exist
os.makedirs(processed_dir, exist_ok=True)

# Loop over 12 months
for i in range(12):
    month_start = start_date + pd.DateOffset(months=i)
    month_end = (month_start + pd.DateOffset(months=1)) - pd.Timedelta(seconds=1)
    
    monthly_data = df.loc[month_start:month_end]
    
    filename = f"{data_dir}/processed/data_{month_start.strftime('%Y_%m')}.csv"
    monthly_data.to_csv(filename)
    print(f"Saved {filename}")



##################################################################################################




##################################################################################################
