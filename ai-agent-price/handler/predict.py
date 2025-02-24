# predict.py

import boto3
import logging
import pickle
import tempfile
from sklearn.preprocessing import StandardScaler
import numpy as np

from config.index import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_SESSION_TOKEN,
    REGION_NAME
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

S3_BUCKET = "car-price-data"
MODELS_PATH = "models_new/"


def get_s3_client():
    """
    Returns an S3 client with explicit AWS credentials from index.py.
    """
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_session_token=AWS_SESSION_TOKEN,
        region_name=REGION_NAME
    )


def load_label_encoders(s3_client, bucket, path):
    """
    Load label encoders from S3.
    """
    encoders = {}
    for column in ['Fuel Type', 'Location', 'Make', 'Model', 'Trim Level', 'Power Indicator']:
        file_name = f"{path}{column}_label_encoder.pkl"
        with tempfile.NamedTemporaryFile() as temp_file:
            s3_client.download_file(bucket, file_name, temp_file.name)
            with open(temp_file.name, "rb") as f:
                encoders[column] = pickle.load(f)
    logger.info("Label encoders loaded successfully from S3.")
    return encoders


def load_scaler(s3_client, bucket, path):
    """
    Load scaler from S3.
    """
    file_name = f"{path}scaler.pkl"
    with tempfile.NamedTemporaryFile() as temp_file:
        s3_client.download_file(bucket, file_name, temp_file.name)
        with open(temp_file.name, "rb") as f:
            scaler = pickle.load(f)
    logger.info("Scaler loaded successfully from S3.")
    return scaler


def preprocess_input_data(input_data, label_encoders, scaler):
    """
    Preprocess input data by applying label encoding and scaling.
    """
    categorical_columns = ['Fuel Type', 'Location', 'Make', 'Model', 'Trim Level', 'Power Indicator']

    # Apply label encoding
    for column in categorical_columns:
        input_data[column] = label_encoders[column].transform([input_data[column]])[0]

    # Add derived feature for Car Age
    current_year = 2024
    input_data['Car Age'] = current_year - input_data['Year']

    # Scale continuous features
    scaled_features = scaler.transform([[input_data['Kilometers Driven'], input_data['Car Age']]])
    input_data['Kilometers Driven'], input_data['Car Age'] = scaled_features[0]

    # Create a properly formatted feature vector
    processed_data = [
        input_data['Make'],
        input_data['Model'],
        input_data['Year'],  # Original year for compatibility
        input_data['Kilometers Driven'],
        input_data['Fuel Type'],
        input_data['Location'],
        input_data['Trim Level'],
        input_data['Power Indicator']
    ]

    logger.info(f"Processed data shape: {len(processed_data)} elements (1D vector).")
    return processed_data


def get_runtime_client():
    """
    Returns a SageMaker runtime client with explicit AWS credentials from index.py.
    """
    return boto3.client(
        "sagemaker-runtime",
        region_name=REGION_NAME,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_session_token=AWS_SESSION_TOKEN
    )


def predict_price(input_data: dict, endpoint_name: str, s3_client, bucket, path):
    """
    Preprocess input data, send it to the endpoint, and get predictions.
    """
    # Load encoders and scaler
    label_encoders = load_label_encoders(s3_client, bucket, path)
    scaler = load_scaler(s3_client, bucket, path)

    # Preprocess input data
    processed_data = preprocess_input_data(input_data, label_encoders, scaler)

    # Convert the data to a CSV line format
    csv_line = ",".join(map(str, processed_data)).strip()
    logger.info(f"CSV line for the endpoint: {csv_line}")

    # Invoke endpoint
    client = get_runtime_client()
    logger.info(f"Invoking endpoint {endpoint_name} with processed data")

    response = client.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType="text/csv",
        Body=csv_line
    )

    response_body = response["Body"].read().decode("utf-8").strip()
    logger.info(f"Endpoint raw response: {response_body}")

    try:
        return float(response_body)
    except ValueError:
        logger.error(f"Unexpected response format: {response_body}")
        raise


def main():
    # Example input
    input_data = {
        'Make': 'Audi',
        'Model': 'Q3',
        'Year': 2018,
        'Kilometers Driven': 41560,
        'Fuel Type': 'Diesel',
        'Location': 'Madhapur',
        'Trim Level': 'Base',
        'Power Indicator': 'Standard'
    }

    # Replace with the name of your deployed endpoint
    endpoint_name = "testv2endpoint"

    # Create S3 client
    s3_client = get_s3_client()

    # Predict price
    try:
        predicted_price = predict_price(input_data, endpoint_name, s3_client, S3_BUCKET, MODELS_PATH)
        print(f"Predicted Price: {predicted_price:.2f} Rs")
    except Exception as e:
        logger.error(f"Failed to predict price: {e}")


if __name__ == "__main__":
    main()







# import boto3
# import json
# import logging

# from config.index import (
#     AWS_ACCESS_KEY_ID,
#     AWS_SECRET_ACCESS_KEY,
#     AWS_SESSION_TOKEN,
#     REGION_NAME
# )

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# def get_runtime_client():
#     """
#     Returns a SageMaker runtime client with explicit AWS credentials from index.py.
#     """
#     return boto3.client(
#         "sagemaker-runtime",
#         region_name=REGION_NAME,
#         aws_access_key_id=AWS_ACCESS_KEY_ID,
#         aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#         aws_session_token=AWS_SESSION_TOKEN
#     )


# def predict_price(input_data: dict, endpoint_name: str) -> float:
#     """
#     Sends raw input data to an Autopilot endpoint (CSV format).
#     """
#     csv_line = (
#         f"{input_data.get('Make','')},"
#         f"{input_data.get('Model','')},"
#         f"{input_data.get('Year','')},"
#         f"{input_data.get('Kilometers Driven','')},"
#         f"{input_data.get('Fuel Type','')},"
#         f"{input_data.get('Location','')},"
#         f"{input_data.get('Trim Level','')},"
#         f"{input_data.get('Power Indicator','')}"
#     )

#     client = get_runtime_client()
#     logger.info(f"Invoking endpoint {endpoint_name} with CSV: {csv_line}")

#     response = client.invoke_endpoint(
#         EndpointName=endpoint_name,
#         ContentType="text/csv",
#         Body=csv_line
#     )

#     response_body = response["Body"].read().decode("utf-8").strip()
#     logger.info(f"Endpoint raw response: {response_body}")

#     # Try parse float
#     try:
#         pred_val = float(response_body)
#         return pred_val
#     except ValueError:
#         pass

#     # Maybe JSON
#     try:
#         result = json.loads(response_body)
#         logger.info(f"Parsed JSON: {result}")
#         if (
#             isinstance(result, dict) and 
#             "predictions" in result and
#             len(result["predictions"]) > 0
#         ):
#             # e.g. { "predictions": [ { "predicted_label": 1234.56 } ] }
#             pred = (
#                 result["predictions"][0].get("predicted_label") or
#                 result["predictions"][0].get("predicted_value")
#             )
#             return float(pred)
#     except json.JSONDecodeError:
#         pass

#     raise ValueError(f"Response is neither float nor recognized JSON: {response_body}")



# def main():
#     # Example input
#     input_data = {
#         'Make': 'Audi',
#         'Model': 'Q3',
#         'Year': 2018,
#         'Kilometers Driven': 41560,
#         'Fuel Type': 'Diesel',
#         'Location': 'Madhapur',
#         'Trim Level': 'Base',
#         'Power Indicator': 'Standard'
#     }

#     # Replace with the name of your deployed endpoint
#     endpoint_name = "testv2endpoint"

#     # Make prediction
#     predicted_price = predict_price(input_data, endpoint_name)
#     print(f"Predicted Price: {predicted_price:.2f} Rs")


# if __name__ == "__main__":
#     main()
