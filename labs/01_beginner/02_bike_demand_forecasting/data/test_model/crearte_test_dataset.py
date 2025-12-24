# Load the sample data CSV
test_model_path = "./data/test_model/"

sample_input = pd.read_csv(test_model_path + 'sample_input_data.csv')
# df = pd.read_csv("sample_input_data.csv")

# Define the subset of features expected by the model
model_features = [
    'temp', 'atemp', 'humidity', 'windspeed',
    'hour', 'weekday', 'season', 'holiday', 'workingday', 'weathersit'
]

# Extract the relevant subset and convert to JSON-like list of dicts
sample_X_input = sample_input[model_features]
sample_y_input = sample_input["count"]

json_input_list = sample_X_input.head(5).to_dict(orient='records')

print(json_input_list)

# Store the generated sample inference input
output_file  = f"{test_model_path}json_input_list.txt"
with open(output_file, "w") as f:
    for item in json_input_list:
        f.write(json.dumps(item) + "\n")

print(f"Saved to {output_file}")