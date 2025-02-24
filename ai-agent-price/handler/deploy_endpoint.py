# deploy_endpoint.py

import argparse
import sys
import logging
import boto3
import uuid
from sagemaker import Session
from sagemaker.automl.automl import AutoML
from config.index import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_SESSION_TOKEN,
    REGION_NAME,
    ROLE_ARN
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_unique_name(base_name, suffix='', max_length=32, use_uuid=True):
    """
    Generates a unique name by appending a UUID to the base name.
    Ensures the total length does not exceed max_length characters.
    """
    if use_uuid:
        unique_id = uuid.uuid4().hex[:6]
        # Calculate maximum length for base name considering suffix and unique_id
        if suffix:
            max_base_length = max_length - len(suffix) - 1 - len(unique_id)  # 1 for hyphen
        else:
            max_base_length = max_length - len(unique_id) - 1  # 1 for hyphen
        truncated_base = base_name[:max_base_length]
        if suffix:
            unique_name = f"{truncated_base}-{unique_id}{suffix}"
        else:
            unique_name = f"{truncated_base}-{unique_id}"
    else:
        unique_name = base_name[:max_length]
    return unique_name

def validate_name(name, name_type):
    """
    Validates that the name meets SageMaker constraints.
    """
    if not (1 <= len(name) <= 32):
        logger.error(f"{name_type} '{name}' length is {len(name)}, which is outside the allowed range (1-32).")
        sys.exit(1)
    import re
    pattern = r'^[a-zA-Z0-9\-]+$'
    if not re.match(pattern, name):
        logger.error(f"{name_type} '{name}' contains invalid characters. Only letters, numbers, and hyphens are allowed.")
        sys.exit(1)

def deploy_best_candidate(
    sagemaker_session,
    automl_job,
    job_name: str,
    endpoint_name: str,
    instance_type: str = 'ml.m5.large',
    initial_instance_count: int = 1
):
    """
    Deploys the best candidate from the Autopilot job to a SageMaker endpoint.
    """
    print("Retrieving the best candidate...")
    best_candidate = automl_job.describe_auto_ml_job()['BestCandidate']
    best_candidate_name = best_candidate['CandidateName']
    print(f"Best candidate: {best_candidate_name}")

    print(f"Deploying the best candidate '{best_candidate_name}' to endpoint '{endpoint_name}'...")
    predictor = automl_job.deploy(
        endpoint_name=endpoint_name,
        instance_type=instance_type,
        initial_instance_count=initial_instance_count
    )
    print(f"Model deployed to endpoint '{endpoint_name}'.")
    return predictor

def main():
    parser = argparse.ArgumentParser(description="Deploy SageMaker Autopilot Best Candidate to Endpoint")
    parser.add_argument("--job-name", required=True, help="Name of the Autopilot job")
    parser.add_argument("--endpoint-name", required=True, help="Desired name for the SageMaker endpoint")
    parser.add_argument("--instance-type", default="ml.m5.large", help="Instance type for deployment")
    parser.add_argument("--initial-instance-count", type=int, default=1, help="Initial instance count for deployment")
    parser.add_argument("--use-uuid", action='store_true', help="Append a UUID to the endpoint name for uniqueness")
    args = parser.parse_args()

    # Generate a unique endpoint name ensuring it does not exceed 32 characters
    unique_endpoint_name = generate_unique_name(args.endpoint_name, suffix='', max_length=32, use_uuid=args.use_uuid)
    validate_name(unique_endpoint_name, "EndpointName")
    logger.info(f"Endpoint name to be used: {unique_endpoint_name}")

    # Initialize SageMaker session
    try:
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            sagemaker_session = Session(
                boto3.Session(
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                    aws_session_token=AWS_SESSION_TOKEN,
                    region_name=REGION_NAME
                )
            )
            logger.info("Initialized SageMaker session with explicit AWS credentials.")
        else:
            # Use default credentials (IAM roles)
            sagemaker_session = Session()
            logger.info("Initialized SageMaker session with default IAM role credentials.")
    except Exception as e:
        logger.error(f"Failed to initialize SageMaker session: {e}")
        sys.exit(1)

    # Initialize AutoML object
    try:
        automl_job = AutoML.attach(args.job_name, sagemaker_session=sagemaker_session)
        logger.info(f"Attached to AutoML job '{args.job_name}'.")
    except Exception as e:
        logger.error(f"Failed to attach to AutoML job '{args.job_name}': {e}")
        sys.exit(1)

    # Deploy the best candidate
    deploy_best_candidate(
        sagemaker_session=sagemaker_session,
        automl_job=automl_job,
        endpoint_name=unique_endpoint_name,
        instance_type=args.instance_type,
        initial_instance_count=args.initial_instance_count
    )

    logger.info(f"Endpoint '{unique_endpoint_name}' deployed successfully.")

if __name__ == "__main__":
    main()
