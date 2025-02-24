import os
import pandas as pd
import numpy as np
import pickle
from sklearn.preprocessing import LabelEncoder, StandardScaler
import boto3

def get_s3_client(aws_access_key_id, aws_secret_access_key, region_name, aws_session_token):
    """
    Initializes and returns a Boto3 S3 client using environment variables for credentials.
    """
    return boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token,
        region_name=region_name
    )

def preprocess_data(
    local_raw_data_path: str,
    local_processed_data_path: str,
    bucket_name: str = None,
    processed_data_key: str = None,
    s3_client=None
):
    """
    Reads the raw data from local path, performs cleaning & feature engineering,
    and saves the processed data locally. Also uploads it to S3 if specified.
    """
    # 1. Read data
    print("Reading raw data...")
    data = pd.read_csv(local_raw_data_path)

    # 2. Data Cleaning
    print("Cleaning data...")
    data['Kilometers Driven'] = (
        data['Kilometers Driven']
        .str.replace(',', '')
        .str.replace(' KMs', '')
        .astype(float)
    )
    data['Location'] = data['Location'].str.replace(', Hyderabad', '').str.strip()
    data['Price'] = data['Price'].replace({'Crore': '0000000'}, regex=True)
    data['Price'] = pd.to_numeric(data['Price'], errors='coerce')
    data = data.dropna(subset=['Price'])

    # 3. Create new features
    print("Creating new features...")
    current_year = 2024
    data['Car Age'] = current_year - data['Year']

    # Standardize fuel type
    data['Fuel Type'] = data['Fuel Type'].apply(lambda x: 'Diesel' if 'diesel' in str(x).lower() else 'Petrol')

    # Extract trim level and power indicator
    data['Trim Level'] = data['Variant'].apply(lambda x: 'Luxury' if 'Luxury' in str(x) else 'Base')
    data['Power Indicator'] = data['Variant'].apply(lambda x: '4MATIC' if '4MATIC' in str(x) else 'Standard')

    # Drop unnecessary columns
    data = data.drop(columns=['Title', 'Year', 'Variant'])

    # 4. Encode categorical variables
    print("Encoding categorical variables...")
    os.makedirs("models_new", exist_ok=True)
    label_encoders = {}
    categorical_columns = ['Fuel Type', 'Location', 'Make', 'Model', 'Trim Level', 'Power Indicator']
    for column in categorical_columns:
        le = LabelEncoder()
        data[column] = le.fit_transform(data[column].astype(str))
        label_encoders[column] = le

    # Save label encoders locally and upload to S3
    for column, encoder in label_encoders.items():
        local_encoder_path = f"models_new/{column}_label_encoder.pkl"
        with open(local_encoder_path, "wb") as f:
            pickle.dump(encoder, f)
        if bucket_name and s3_client:
            s3_client.upload_file(local_encoder_path, bucket_name, f"models_new/{column}_label_encoder.pkl")
            print(f"Uploaded {column}_label_encoder.pkl to s3://{bucket_name}/models_new/")

    # 5. Scale continuous features
    print("Scaling continuous features...")
    scaler = StandardScaler()
    data[['Kilometers Driven', 'Car Age']] = scaler.fit_transform(data[['Kilometers Driven', 'Car Age']])

    # Save scaler locally and upload to S3
    local_scaler_path = "models_new/scaler.pkl"
    with open(local_scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    if bucket_name and s3_client:
        s3_client.upload_file(local_scaler_path, bucket_name, "models_new/scaler.pkl")
        print(f"Uploaded scaler.pkl to s3://{bucket_name}/models_new/")

    # 6. Log-transform the target variable
    data['Price'] = np.log1p(data['Price'])

    # 7. Save processed data locally
    print("Saving processed data...")
    os.makedirs(os.path.dirname(local_processed_data_path), exist_ok=True)
    data.to_csv(local_processed_data_path, index=False)

    # 8. Upload processed data to S3
    if bucket_name and processed_data_key and s3_client:
        print(f"Uploading processed data to s3://{bucket_name}/{processed_data_key}...")
        s3_client.upload_file(local_processed_data_path, bucket_name, processed_data_key)
        print("Processed data uploaded successfully.")

    print("Data preprocessing completed.")
