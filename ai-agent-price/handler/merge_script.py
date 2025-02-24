import boto3
import argparse
import pandas as pd
import os
import logging
from io import BytesIO  # Import BytesIO
from config.index import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_SESSION_TOKEN,
    REGION_NAME,
    ROLE
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def merge_files(input_bucket, input_prefix, output_bucket, output_prefix):
    logger.info("Starting file merge process...")
    
    # Initialize S3 client with explicit credentials
    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_session_token=AWS_SESSION_TOKEN,
        region_name=REGION_NAME
    )
    
    # List all files in the input directory with .csv, .xlsx, .xls extensions
    response = s3.list_objects_v2(Bucket=input_bucket, Prefix=input_prefix)
    if 'Contents' not in response:
        logger.error("No objects found in the specified S3 path.")
        raise FileNotFoundError("No objects found in the specified S3 path.")
        
    valid_extensions = ('.csv', '.xlsx', '.xls')
    files = [content['Key'] for content in response.get('Contents', []) if content['Key'].lower().endswith(valid_extensions)]

    if not files:
        logger.error("No supported files found to merge.")
        raise FileNotFoundError("No supported files found to merge.")

    logger.info(f"Found {len(files)} files to process.")

    # Download and merge files
    dataframes = []
    for file_key in files:
        logger.info(f"Downloading {file_key} from S3...")
        obj = s3.get_object(Bucket=input_bucket, Key=file_key)
        file_extension = os.path.splitext(file_key)[1].lower()
        
        if file_extension == '.csv':
            try:
                df = pd.read_csv(obj['Body'])
                logger.info(f"Successfully read CSV file: {file_key}")
            except Exception as e:
                logger.error(f"Error reading CSV file {file_key}: {e}")
                continue
        elif file_extension in ['.xlsx', '.xls']:
            try:
                # Wrap the StreamingBody in BytesIO to enable seeking
                excel_buffer = BytesIO(obj['Body'].read())
                df = pd.read_excel(excel_buffer)
                logger.info(f"Successfully read Excel file: {file_key}")
            except Exception as e:
                logger.error(f"Error reading Excel file {file_key}: {e}")
                continue
        else:
            logger.warning(f"Unsupported file type for {file_key}. Skipping.")
            continue
        
        dataframes.append(df)
    
    if not dataframes:
        logger.error("No dataframes were created from the downloaded files.")
        raise ValueError("No dataframes to merge.")

    logger.info("Merging files...")
    try:
        merged_df = pd.concat(dataframes, ignore_index=True)
        logger.info(f"Merged DataFrame shape: {merged_df.shape}")
    except Exception as e:
        logger.error(f"Error merging dataframes: {e}")
        raise e

    # Convert merged DataFrame to CSV in-memory
    try:
        csv_buffer = BytesIO()
        merged_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)  # Reset buffer pointer to the beginning
        logger.info("Merged data converted to CSV format in-memory.")
    except Exception as e:
        logger.error(f"Error converting merged DataFrame to CSV: {e}")
        raise e

    # Define the S3 key for the merged CSV
    merged_file_key = os.path.join(output_prefix, "merged_data.csv").replace("\\", "/")  # Ensure Unix-style path

    # Upload the merged CSV to the output S3 bucket
    try:
        logger.info(f"Uploading merged CSV to s3://{output_bucket}/{merged_file_key}...")
        s3.put_object(Bucket=output_bucket, Key=merged_file_key, Body=csv_buffer.getvalue())
        logger.info("Merged CSV uploaded successfully.")
    except Exception as e:
        logger.error(f"Error uploading merged CSV to S3: {e}")
        raise e

def main():
    parser = argparse.ArgumentParser(description="Merge files for Car Price Prediction")
    parser.add_argument("--input-bucket", required=True, help="S3 bucket where raw data is stored")
    parser.add_argument("--input-prefix", required=True, help="S3 prefix for raw data")
    parser.add_argument("--output-bucket", required=True, help="S3 bucket to save the merged CSV")
    parser.add_argument("--output-prefix", required=True, help="S3 prefix (folder path) to save the merged CSV")
    args = parser.parse_args()

    merge_files(args.input_bucket, args.input_prefix, args.output_bucket, args.output_prefix)

    logger.info("merge_script.py completed successfully.")

if __name__ == "__main__":
    main()