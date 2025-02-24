# data_ingestion.py

import os
import boto3

def get_s3_client(aws_access_key_id, aws_secret_access_key, region_name, aws_session_token):
    """
    Initializes and returns a Boto3 S3 client with the provided AWS credentials.
    """
    return boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token,
        region_name=region_name
    )

def ingest_data(bucket_name: str, raw_data_key: str, local_raw_data_path: str, s3_client):
    """
    Downloads raw data (Excel) from S3 to the local machine.
    """
    os.makedirs(os.path.dirname(local_raw_data_path), exist_ok=True)
    print(f"Downloading raw data from s3://{bucket_name}/{raw_data_key} ...")
    s3_client.download_file(bucket_name, raw_data_key, local_raw_data_path)
    print("Download complete.")
