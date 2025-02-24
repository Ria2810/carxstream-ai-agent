import boto3
import logging
import sys
import time
from pipeline import get_pipeline  # Ensure this imports your updated pipeline.py
from botocore.exceptions import ClientError
from config.index import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_SESSION_TOKEN,
    REGION_NAME,
    ROLE_ARN
)

# ---------------------------------------------------------------------
# Configure Python logging
# ---------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def get_boto3_client(service_name, region):
    """
    Initializes a boto3 client with explicit credentials.

    Parameters:
    - service_name (str): AWS service name (e.g., 'sagemaker')
    - region (str): AWS region

    Returns:
    - boto3.client: Initialized boto3 client
    """
    return boto3.client(
        service_name,
        region_name=region,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_session_token=AWS_SESSION_TOKEN
    )

def validate_credentials():
    """
    Validates the provided AWS credentials by calling STS GetCallerIdentity.

    Exits the program if validation fails.
    """
    sts_client = get_boto3_client('sts', REGION_NAME)
    try:
        identity = sts_client.get_caller_identity()
        logger.info(f"Authenticated as: {identity['Arn']}")
    except ClientError as e:
        logger.error(f"Credential validation failed: {e}")
        sys.exit(1)

def upsert_pipeline(pipeline_definition, pipeline_name, role_arn, region):
    """
    Upsert the SageMaker pipeline using boto3 SageMaker client.

    Parameters:
    - pipeline_definition (str): The pipeline definition in JSON string format.
    - pipeline_name (str): Name of the pipeline.
    - role_arn (str): IAM role ARN.
    - region (str): AWS region.

    Returns:
    - str: PipelineArn of the created or updated pipeline.
    """
    client = get_boto3_client('sagemaker', region)

    try:
        logger.info(f"Attempting to create pipeline '{pipeline_name}'...")
        response = client.create_pipeline(
            PipelineName=pipeline_name,
            PipelineDefinition=pipeline_definition,
            PipelineDescription="Pipeline for Car Price Prediction",
            RoleArn=role_arn
        )
        pipeline_arn = response['PipelineArn']
        logger.info(f"Pipeline '{pipeline_name}' created successfully with ARN: {pipeline_arn}")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        if error_code == 'ValidationException' and 'already exists' in error_message:
            logger.info(f"Pipeline '{pipeline_name}' already exists. Attempting to update it...")
            response = client.update_pipeline(
                PipelineName=pipeline_name,
                PipelineDefinition=pipeline_definition,
                PipelineDescription="Pipeline for Car Price Prediction",
                RoleArn=role_arn
            )
            pipeline_arn = response['PipelineArn']
            logger.info(f"Pipeline '{pipeline_name}' updated successfully with ARN: {pipeline_arn}")
        else:
            logger.error(f"Failed to create or update the pipeline: {e}")
            sys.exit(1)

    return pipeline_arn

def start_pipeline_execution(pipeline_name, region, parameters):
    """
    Starts the execution of the specified SageMaker pipeline.

    Parameters:
    - pipeline_name (str): Name of the pipeline.
    - region (str): AWS region.
    - parameters (dict): Parameters to pass to the pipeline.

    Returns:
    - str: PipelineExecutionArn
    """
    client = get_boto3_client('sagemaker', region)

    try:
        logger.info("Starting pipeline execution...")
        response = client.start_pipeline_execution(
            PipelineName=pipeline_name,
            PipelineParameters=[
                {"Name": key, "Value": value} for key, value in parameters.items()
            ]
        )
        execution_arn = response['PipelineExecutionArn']
        logger.info(f"Pipeline execution started: {execution_arn}")
        return execution_arn
    except ClientError as e:
        logger.error(f"Pipeline execution failed: {e}")
        sys.exit(1)

def wait_for_execution(client, execution_arn, delay=30, max_attempts=60):
    """
    Polls the pipeline execution status until it is in a terminal state.

    Parameters:
    - client (boto3.client): Initialized boto3 SageMaker client.
    - execution_arn (str): ARN of the pipeline execution.
    - delay (int): Seconds between polling attempts.
    - max_attempts (int): Maximum number of polling attempts.

    Returns:
    - tuple: (Final status, Failure reason if any)
    """
    terminal_states = ['Succeeded', 'Failed', 'Stopped']
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.describe_pipeline_execution(
                PipelineExecutionArn=execution_arn
            )
            status = response['PipelineExecutionStatus']
            logger.info(f"Attempt {attempt}/{max_attempts}: Pipeline execution status: {status}")
            if status in terminal_states:
                failure_reason = response.get('FailureReason', 'No failure reason provided.')
                return status, failure_reason
            else:
                time.sleep(delay)
        except ClientError as e:
            logger.error(f"Error describing pipeline execution: {e}")
            time.sleep(delay)
    logger.error("Pipeline execution did not complete within the expected time.")
    sys.exit(1)

def main():
    # Validate AWS credentials
    validate_credentials()

    # Configuration parameters
    region = REGION_NAME
    role_arn = ROLE_ARN
    pipeline_name = "CarPricePipeline"
    default_bucket = "car-price-data"

    # Parameters to pass to the pipeline
    pipeline_parameters = {
        "InputBucket": default_bucket,
        "InputPrefix": "raw_data/",
        "MergedDataPrefix": "merged_data/",
        "IngestionDataPrefix": "ingestion_data/",
        "ProcessedDataPrefix": "processed_data/",
        "OutputDataPrefix": "autopilot_output/",
        "RoleArn": role_arn
    }

    # Initialize SageMaker Pipeline
    pipeline = get_pipeline(region=region, role=role_arn, default_bucket=default_bucket)

    # Get the pipeline definition as JSON
    pipeline_definition_json = pipeline.definition()

    # Upsert (create or update) the pipeline
    pipeline_arn = upsert_pipeline(pipeline_definition_json, pipeline_name, role_arn, region)

    # Start pipeline execution with parameters
    execution_arn = start_pipeline_execution(pipeline_name, region, pipeline_parameters)

    # Wait for pipeline execution to complete
    client = get_boto3_client('sagemaker', region)
    final_status, failure_reason = wait_for_execution(client, execution_arn)

    # Handle the final status
    if final_status == 'Succeeded':
        logger.info("Pipeline executed successfully.")
    elif final_status == 'Failed':
        logger.error(f"Pipeline execution failed. Reason: {failure_reason}")
    elif final_status == 'Stopped':
        logger.warning("Pipeline execution was stopped.")
    else:
        logger.warning(f"Pipeline execution ended with unexpected status: {final_status}")

if __name__ == "__main__":
    main()
