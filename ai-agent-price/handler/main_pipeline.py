import os
import logging
from datetime import datetime
import uuid
from merge_script import merge_files
from sagemaker.automl.automl import AutoML
from data_ingestion import ingest_data, get_s3_client
from data_preprocessing import preprocess_data
from autopilot_script import get_sagemaker_session, create_and_run_automl_job, wait_for_automl_job, create_hyperparameter_tuning_job, deploy_best_candidate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def generate_unique_name(base_name="price-auto-ml", max_length=32):
    separator = "-"
    timestamp = datetime.now().strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:6]
    base_name_max = max_length - len(separator) * 2 - len(timestamp) - len(unique_id)
    if len(base_name) > base_name_max:
        base_name = base_name[:base_name_max]
    return f"{base_name}{separator}{timestamp}{separator}{unique_id}"

def main():
    try:
        # Fetch parameters from environment variables
        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        region_name = os.getenv("REGION_NAME")
        role_arn = os.getenv("ROLE_ARN")
        aws_session_token = os.getenv("AWS_SESSION_TOKEN")
        bucket_name = os.getenv("BUCKET_NAME")
        raw_data_prefix = os.getenv("RAW_DATA_PREFIX")
        merged_data_prefix = os.getenv("MERGED_DATA_PREFIX")
        ingestion_data_prefix = os.getenv("INGESTION_DATA_PREFIX")
        processed_data_prefix = os.getenv("PROCESSED_DATA_PREFIX")
        autopilot_output_prefix = os.getenv("AUTOPILOT_OUTPUT_PREFIX")
        tuning_output_prefix = os.getenv("TUNING_OUTPUT_PREFIX")

        # Derived S3 paths
        merged_data_key = f"{merged_data_prefix}merged_data.csv"
        ingested_data_key = f"{ingestion_data_prefix}ingested_data.csv"
        processed_data_key = f"{processed_data_prefix}processed_data.csv"
        input_data_s3_uri = f"s3://{bucket_name}/{processed_data_key}"
        tuning_output_s3_uri = f"s3://{bucket_name}/{tuning_output_prefix}"
        output_data_s3_uri = f"s3://{bucket_name}/{autopilot_output_prefix}"

        # Local paths
        local_merged_data_path = "data/merged_data.csv"
        local_ingested_data_path = "data/ingested_data.csv"
        local_processed_data_path = "data/processed_data.csv"

        # Autopilot configuration
        automl_job_name = generate_unique_name()
        endpoint_name = generate_unique_name(base_name="price-auto-ml-endpoint")
        target_attribute_name = "Price"

        # Initialize S3 client
        s3_client = get_s3_client(aws_access_key_id, aws_secret_access_key, region_name, aws_session_token)

        # Step 1: Merge Data
        logger.info("=== Step 1: Merging Data ===")
        merge_files(
            input_bucket=bucket_name,
            input_prefix=raw_data_prefix,
            output_bucket=bucket_name,
            output_prefix=merged_data_prefix
        )

        # Step 2: Data Ingestion
        logger.info("\n=== Step 2: Data Ingestion ===")
        ingest_data(
            bucket_name=bucket_name,
            raw_data_key=merged_data_key,
            local_raw_data_path=local_ingested_data_path,
            s3_client=s3_client
        )

        # Step 3: Data Preprocessing
        logger.info("\n=== Step 3: Data Preprocessing ===")
        preprocess_data(
            local_raw_data_path=local_ingested_data_path,
            local_processed_data_path=local_processed_data_path,
            bucket_name=bucket_name,
            processed_data_key=processed_data_key,
            s3_client=s3_client
        )

        # Step 4: Model Training with SageMaker Autopilot
        logger.info("\n=== Step 4: Model Training with SageMaker Autopilot ===")
        sagemaker_session = get_sagemaker_session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
            aws_session_token=aws_session_token
        )
        create_and_run_automl_job(
            sagemaker_session=sagemaker_session,
            job_name=automl_job_name,
            input_data_s3_uri=input_data_s3_uri,
            output_data_s3_uri=output_data_s3_uri,
            target_attribute_name=target_attribute_name,
            role_arn=role_arn
        )

        # Wait for Autopilot job to complete
        automl_job = AutoML.attach(automl_job_name, sagemaker_session=sagemaker_session)
        wait_for_automl_job(automl_job, automl_job_name)

        try: 
            best_candidate = automl_job.describe_auto_ml_job()["BestCandidate"]
            logger.info(f"Best Candidate {best_candidate}")
            best_candidate_container = best_candidate["InferenceContainers"][0]["Image"]
            logger.info(f"Best Candidate Container: {best_candidate_container}")
            logger.info("Starting hyperparameter tuning...")
            best_training_job_name = create_hyperparameter_tuning_job(
                sagemaker_session=sagemaker_session,
                best_candidate_container=best_candidate_container,
                role_arn=role_arn,
                train_data_s3_uri=input_data_s3_uri,
                tuning_output_s3_uri=tuning_output_s3_uri
            )
            logger.info(f"Hyperparameter tuning completed with the best training job: {best_training_job_name}")
        except Exception as e:
            logger.error(f"Model training or hyperparameter tuning failed: {e}")
    # Deploy the best candidate
    
        try:
            # Step 5: Deploy the Tuned Model
            logger.info("\n=== Step 5: Deploying the Tuned Model ===")
            deploy_best_candidate(
                sagemaker_session=sagemaker_session,
                best_training_job_name=best_training_job_name,
                endpoint_name=endpoint_name,
                instance_type='ml.m5.large',
                initial_instance_count=1
            )
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            
            logger.info("\n=== Pipeline Execution Completed Successfully ===")

    except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            raise e


if __name__ == "__main__":
    main()
