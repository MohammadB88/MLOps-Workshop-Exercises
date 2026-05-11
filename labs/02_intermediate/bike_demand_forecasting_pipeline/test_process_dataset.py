"""
Unit tests for the process_dataset component
"""
import os
import tempfile
import zipfile
import pandas as pd
from pipeline_bike_sharing import process_dataset

def test_process_dataset():
    """Test the process_dataset component with sample data"""
    # Create sample data
    sample_data = pd.DataFrame({
        'instant': [1, 2, 3, 4],
        'dteday': ['2011-01-01', '2011-01-02', '2011-02-01', '2011-02-02'],
        'season': [1, 1, 2, 2],
        'yr': [0, 0, 0, 0],
        'mnth': [1, 1, 2, 2],
        'hr': [0, 1, 0, 1],
        'holiday': [0, 0, 0, 0],
        'weekday': [5, 6, 5, 6],
        'workingday': [0, 0, 0, 0],
        'weathersit': [1, 1, 1, 1],
        'temp': [0.1, 0.2, 0.3, 0.4],
        'atemp': [0.1, 0.2, 0.3, 0.4],
        'hum': [0.1, 0.2, 0.3, 0.4],
        'windspeed': [0.1, 0.2, 0.3, 0.4],
        'casual': [1, 2, 3, 4],
        'registered': [10, 20, 30, 40],
        'cnt': [11, 22, 33, 44]
    })
    
    # Create temporary input file
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp_input:
        sample_data.to_csv(tmp_input.name, index=False)
        input_path = tmp_input.name
    
    # Create temporary output file
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_output:
        output_path = tmp_output.name
    
    try:
        # Set environment variables
        os.environ['DATASET_URL'] = 'https://example.com/dataset.zip'
        
        # Run the component
        process_dataset(input_path, output_path)
        
        # Verify output exists
        assert os.path.exists(output_path), "Output zip file was not created"
        
        # Verify zip file is not empty
        assert os.path.getsize(output_path) > 0, "Output zip file is empty"
        
        # Verify we can extract files from the zip
        with zipfile.ZipFile(output_path, 'r') as zipf:
            file_list = zipf.namelist()
            assert len(file_list) > 0, "Zip file contains no files"
            
            # Check that we have CSV files
            csv_files = [f for f in file_list if f.endswith('.csv')]
            assert len(csv_files) > 0, "Zip file contains no CSV files"
            
            # Try to read one of the CSV files
            with zipf.open(csv_files[0]) as csvfile:
                df = pd.read_csv(csvfile)
                assert not df.empty, "Extracted CSV file is empty"
                assert 'year' in df.columns, "Year column not found in processed data"
                assert 'month' in df.columns, "Month column not found in processed data"
                assert 'count' in df.columns, "Count column not found in processed data"
        
        print("All tests passed!")
        
    finally:
        # Clean up temporary files
        if os.path.exists(input_path):
            os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)

if __name__ == "__main__":
    test_process_dataset()