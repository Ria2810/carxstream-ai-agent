import logging
import os
import sys
import subprocess
import json
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.parameters import ParameterString
from config.index import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, REGION_NAME, ROLE, AWS_SESSION_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_pipeline(region=None, role=None, default_bucket=None):
    logger.info("Initializing pipeline parameters...")

    # Define pipeline parameters
    aws_access_key_param = ParameterString(name="AWSAccessKeyId", default_value="")
    aws_secret_access_key_param = ParameterString(name="AWSSecretAccessKey", default_value="")
    region_name_param = ParameterString(name="RegionName", default_value=region)
    role_arn_param = ParameterString(name="RoleArn", default_value=role)
    aws_session_token_param = ParameterString(name="AWSSessionToken", default_value="")
    bucket_name_param = ParameterString(name="BucketName", default_value=default_bucket)
    raw_data_prefix_param = ParameterString(name="RawDataPrefix", default_value="raw_data/")
    merged_data_prefix_param = ParameterString(name="MergedDataPrefix", default_value="merged_data/")
    ingestion_data_prefix_param = ParameterString(name="IngestionDataPrefix", default_value="ingestion_data/")
    processed_data_prefix_param = ParameterString(name="ProcessedDataPrefix", default_value="processed_data/")
    autopilot_output_prefix_param = ParameterString(name="AutopilotOutputPrefix", default_value="autopilot_output/")
    tuning_output_prefix_param = ParameterString(name="TuningOutputPrefix", default_value="tuning_output/")

    pipeline = Pipeline(
        name="CarPricePipeline",
        parameters=[
            aws_access_key_param,
            aws_secret_access_key_param,
            region_name_param,
            role_arn_param,
            aws_session_token_param,
            bucket_name_param,
            raw_data_prefix_param,
            merged_data_prefix_param,
            ingestion_data_prefix_param,
            processed_data_prefix_param,
            autopilot_output_prefix_param,
            tuning_output_prefix_param,
        ],
        steps=[],
    )
    logger.info("Pipeline initialized.")
    return pipeline


def execute_pipeline(parameters):
    """Execute the main_pipeline.py script with the given parameters."""
    try:
        logger.info("Executing main_pipeline.py with provided parameters...")

        # Pass the parameters as environment variables
        env_vars = os.environ.copy()
        env_vars.update({
            "AWS_ACCESS_KEY_ID": parameters["AWSAccessKeyId"],
            "AWS_SECRET_ACCESS_KEY": parameters["AWSSecretAccessKey"],
            "AWS_SESSION_TOKEN": parameters["AWSSessionToken"],
            "REGION_NAME": parameters["RegionName"],
            "ROLE_ARN": parameters["RoleArn"],
            "BUCKET_NAME": parameters["BucketName"],
            "RAW_DATA_PREFIX": parameters["RawDataPrefix"],
            "MERGED_DATA_PREFIX": parameters["MergedDataPrefix"],
            "INGESTION_DATA_PREFIX": parameters["IngestionDataPrefix"],
            "PROCESSED_DATA_PREFIX": parameters["ProcessedDataPrefix"],
            "AUTOPILOT_OUTPUT_PREFIX": parameters["AutopilotOutputPrefix"],
            "TUNING_OUTPUT_PREFIX": parameters["TuningOutputPrefix"],
        })

        # Use the current Python interpreter to run the main_pipeline script
        result = subprocess.run(
            [sys.executable, "handler/main_pipeline.py"],
            capture_output=True,
            text=True,
            env=env_vars,
        )

        logger.info(result.stdout)
        if result.returncode != 0:
            logger.error(result.stderr)
            raise Exception("main_pipeline.py execution failed.")
        logger.info("main_pipeline.py executed successfully.")
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise e


if __name__ == "__main__":
    aws_access_key_id = AWS_ACCESS_KEY_ID
    aws_secret_access_key = AWS_SECRET_ACCESS_KEY
    region_name = REGION_NAME
    role_arn = ROLE
    aws_session_token = AWS_SESSION_TOKEN

    # S3 Configuration
    bucket_name = "car-price-data"
    raw_data_prefix = "raw_data/"
    merged_data_prefix = "merged_data/"
    ingestion_data_prefix = "ingestion_data/"
    processed_data_prefix = "processed_data/"
    autopilot_output_prefix = "autopilot_output/"
    tuning_output_prefix = "tuning_output/"

    pipeline = get_pipeline(region=region_name, role=role_arn, default_bucket=bucket_name)

    parameters = {
        "AWSAccessKeyId": aws_access_key_id,
        "AWSSecretAccessKey": aws_secret_access_key,
        "RegionName": region_name,
        "RoleArn": role_arn,
        "AWSSessionToken": aws_session_token,
        "BucketName": bucket_name,
        "RawDataPrefix": raw_data_prefix,
        "MergedDataPrefix": merged_data_prefix,
        "IngestionDataPrefix": ingestion_data_prefix,
        "ProcessedDataPrefix": processed_data_prefix,
        "AutopilotOutputPrefix": autopilot_output_prefix,
        "TuningOutputPrefix": tuning_output_prefix,
    }

    # Execute the pipeline
    execute_pipeline(parameters)






















# # main_pipeline.py

# import os
# import sys
# import time
# import logging
# from datetime import datetime
# import uuid

# from data_ingestion import ingest_data, get_s3_client
# from merge_script import merge_files
# from data_preprocessing import preprocess_data  # <-- We won't import or use custom preprocessing
# from autopilot_script import (
#     create_and_run_automl_job,
#     wait_for_automl_job,
#     deploy_best_candidate,
#     get_sagemaker_session
# )
# from predict import predict_price
# from config.index import (
#     AWS_ACCESS_KEY_ID,
#     AWS_SECRET_ACCESS_KEY,
#     REGION_NAME,
#     ROLE_ARN,
#     AWS_SESSION_TOKEN
# )

# from sagemaker.automl.automl import AutoML

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s %(levelname)s %(message)s',
#     handlers=[logging.StreamHandler()]
# )
# logger = logging.getLogger(__name__)

# def generate_unique_name(base_name="price-auto-ml", max_length=32):
#     separator = "-"
#     timestamp = datetime.now().strftime("%Y%m%d")
#     unique_id = uuid.uuid4().hex[:6]
#     base_name_max = max_length - len(separator)*2 - len(timestamp) - len(unique_id)
#     if len(base_name) > base_name_max:
#         base_name = base_name[:base_name_max]
#     unique_name = f"{base_name}{separator}{timestamp}{separator}{unique_id}"
#     return unique_name

# def main():
#     # -------------------------------------------------------------------------
#     # AWS Configuration
#     # -------------------------------------------------------------------------
#     aws_access_key_id = AWS_ACCESS_KEY_ID
#     aws_secret_access_key = AWS_SECRET_ACCESS_KEY
#     region_name = REGION_NAME
#     role_arn = ROLE_ARN
#     aws_session_token = AWS_SESSION_TOKEN

#     # -------------------------------------------------------------------------
#     # S3 Configuration
#     # -------------------------------------------------------------------------
#     bucket_name = "car-price-data"
#     raw_data_key = "raw_data"  
#     merge_key = "merged_data"

#     # Local path to your raw data (if you need to upload from local)
#     local_raw_data_path = "data/Hyderabad_Ct_scrapedData.csv"

#     # Autopilot Job Configuration
#     automl_job_name = generate_unique_name()
#     endpoint_name = generate_unique_name(base_name="CarPriceEndpoint")

#     target_attribute_name = "Price"

#     # Initialize S3 client
#     s3_client = get_s3_client(
#         aws_access_key_id,
#         aws_secret_access_key,
#         region_name,
#         aws_session_token
#     )

#     logger.info("====Merge request====")
#     try:
#         merge_files(
#             input_bucket=bucket_name, 
#             input_prefix=raw_data_key, 
#             output_bucket=bucket_name, 
#             output_prefix= merge_key)
#     except Exception as e:
#         logger.error(f"Data Merging failed: {e}")
#         sys.exit(1)

#     # -------------------------------------------------------------------------
#     # Step 1: Data Ingestion (Optional if your data is already in S3)
#     # -------------------------------------------------------------------------

#      # Autopilot will handle data transformations internally, so no separate processed key is needed.
#     merged_data_key = "merged_data/merged_data.csv"

#     logger.info("=== Step 1: Data Ingestion ===")
#     try:
#         ingest_data(
#             bucket_name=bucket_name,
#             raw_data_key=merged_data_key,
#             local_raw_data_path=local_raw_data_path,
#             s3_client=s3_client
#         )
#     except Exception as e:
#         logger.error(f"Data ingestion failed: {e}")
#         sys.exit(1)

#     # -------------------------------------------------------------------------
#     # Step 2: Skip Custom Data Preprocessing
#     # -------------------------------------------------------------------------
#     # We rely on Autopilot's built-in preprocessing. 
#     # Comment out or remove your custom preprocess call:
#     #
#     preprocess_data(
#           local_raw_data_path=local_raw_data_path,
#           local_processed_data_path="data/processed_data.csv",
#           bucket_name=bucket_name,
#           processed_data_key="processed_data/processed_data.csv",
#           s3_client=s3_client
#       )

#     # -------------------------------------------------------------------------
#     # Step 3: Model Training with SageMaker Autopilot
#     # -------------------------------------------------------------------------
#     logger.info("=== Step 2 (Updated): Model Training with SageMaker Autopilot ===")
#     try:
#         sagemaker_session = get_sagemaker_session(
#             aws_access_key_id=aws_access_key_id,
#             aws_access_key_secret=aws_secret_access_key,
#             aws_session_token=aws_session_token,
#             region_name=region_name
#         )
#         processed_key = "processed_data/processed_data.csv"
#         input_data_s3_uri = f"s3://{bucket_name}/{processed_key}"
#         output_data_s3_uri = f"s3://{bucket_name}/autopilot_output/"

#         # Create and run Autopilot job (pointing directly to raw_data in S3)
#         create_and_run_automl_job(
#             sagemaker_session=sagemaker_session,
#             job_name=automl_job_name,
#             input_data_s3_uri=input_data_s3_uri,
#             output_data_s3_uri=output_data_s3_uri,
#             target_attribute_name=target_attribute_name,
#             role_arn=role_arn
#         )
#     except Exception as e:
#         logger.error(f"Autopilot job creation failed: {e}")
#         sys.exit(1)

#     # Wait for Autopilot job to complete
#     try:
#         automl_job = AutoML.attach(automl_job_name, sagemaker_session=sagemaker_session)
#         wait_for_automl_job(automl_job, automl_job_name)
#     except Exception as e:
#         logger.error(f"Autopilot job failed: {e}")
#         sys.exit(1)

#     # Deploy the best candidate
#     try:
#         deploy_best_candidate(
#             sagemaker_session=sagemaker_session,
#             automl_job=automl_job,
#             job_name=automl_job_name,
#             endpoint_name=endpoint_name,
#             instance_type='ml.m5.large',
#             initial_instance_count=1
#         )
#     except Exception as e:
#         logger.error(f"Deployment failed: {e}")
#         sys.exit(1)

#     # -------------------------------------------------------------------------
#     # Step 4: Make a Prediction
#     # -------------------------------------------------------------------------
#     logger.info("=== Step 3 (Updated): Making a Prediction ===")
#     try:
#         # Just provide raw data in the same format as your CSV's column headings.
#         # Autopilot's deployed model will apply the transformations automatically.
#         predicted_price = predict_price(
#             input_data={
#                 'Make': 'Audi',
#                 'Model': 'Q3',
#                 'Year': 2018,
#                 'Kilometers Driven': '41,560',  # or numeric if you already pass as float
#                 'Fuel Type': 'Diesel',
#                 'Location': 'Madhapur',
#                 'Trim Level': 'Base',
#                 'Power Indicator': 'Standard',
#                 # Make sure the keys match the CSV's column names
#             },
#             endpoint_name=endpoint_name,
#             bucket_name=bucket_name,
#             models_folder="models_new",
#             aws_access_key_id=aws_access_key_id,
#             aws_secret_access_key=aws_secret_access_key,
#             aws_session_token=aws_session_token,
#             region_name=region_name
#         )
#         logger.info(f"Predicted Price: {predicted_price:.2f} Rs")
#     except Exception as e:
#         logger.error(f"Prediction failed: {e}")
#         sys.exit(1)

#     logger.info("=== Pipeline Execution Completed Successfully ===")

# if __name__ == "__main__":
#     main()

















