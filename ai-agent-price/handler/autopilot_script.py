# model_training.py
import argparse
import boto3
import os
import logging
import time
from botocore.exceptions import ClientError
import sagemaker
from sagemaker import AutoML
from sagemaker.session import Session
import shutil
import tarfile
from sagemaker.estimator import Estimator
from sagemaker.tuner import (
    HyperparameterTuner,
    ContinuousParameter,
    IntegerParameter,
    CategoricalParameter,
)
from sagemaker.estimator import Estimator
from config.index import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, REGION_NAME, ROLE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

aws_access_key_id = AWS_ACCESS_KEY_ID
aws_secret_access_key = AWS_SECRET_ACCESS_KEY
region_name = REGION_NAME

def get_sagemaker_session(aws_access_key_id, aws_secret_access_key, region_name, aws_session_token):
    """
    Initializes and returns a SageMaker Session with the provided AWS credentials.
    """
    boto_session = boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token,
        region_name=region_name
    )
    return Session(boto_session=boto_session)

def create_and_run_automl_job(
    sagemaker_session,
    job_name: str,
    input_data_s3_uri: str,
    output_data_s3_uri: str,
    target_attribute_name: str,
    role_arn: str
):
    """
    Creates and runs a SageMaker Autopilot job.
    """
    automl = AutoML(
        role=role_arn,
        target_attribute_name=target_attribute_name,
        output_path=output_data_s3_uri,
        problem_type='Regression',
        job_objective={'MetricName': 'RMSE'},
        sagemaker_session=sagemaker_session
    )

    print(f"Starting SageMaker Autopilot job: {job_name}")
    automl.fit(
        inputs=input_data_s3_uri,
        job_name=job_name
    )
    print("Autopilot job started.")

def wait_for_automl_job(automl_job, job_name: str):
    """
    Waits for the Autopilot job to complete.
    """
    print(f"Waiting for Autopilot job '{job_name}' to complete...")
    while True:
        status = automl_job.describe_auto_ml_job()['AutoMLJobStatus']
        print(f"Autopilot job status: {status}")
        if status in ['Completed', 'Failed', 'Stopped']:
            break
        print("Waiting for 5 minutes before next status check...")
        time.sleep(300)  # Wait for 5 minutes

    if status != 'Completed':
        raise Exception(f"Autopilot job ended with status: {status}")
    print("Autopilot job completed successfully.")

def create_hyperparameter_tuning_job(
    sagemaker_session,
    best_candidate_container,
    role_arn,
    train_data_s3_uri,
    tuning_output_s3_uri
):
    """
    Creates and starts a hyperparameter tuning job using the best candidate model container.

    Parameters:
    - sagemaker_session: SageMaker session
    - best_candidate_container: Container URI of the best candidate model from Autopilot
    - role_arn: IAM role for SageMaker
    - train_data_s3_uri: S3 URI for training data
    - tuning_output_s3_uri: S3 URI for tuning outputs

    Returns:
    - best_training_job_name: Name of the best training job from the hyperparameter tuning job
    """
    logger.info("Creating a hyperparameter tuning job...")

    # Define metric definitions explicitly
    metric_definitions = [
        {
            "Name": "validation:accuracy",  # Must match the objective_metric_name
            "Regex": r"val_accuracy=(\d+\.\d+)"
        }
    ]

    logger.info(f"Using metric definitions: {metric_definitions}")


    # Dummy training script content with metrics printed to stdout
    # Recreate the source_dir with the updated dummy_train.py
    source_dir = "source_dir"
    os.makedirs(source_dir, exist_ok=True)
    dummy_script_path = os.path.join(source_dir, "dummy_train.py")

    # Ensure you write the updated script content
    with open(dummy_script_path, "w") as f:
        f.write("""\
import argparse
import json
import os
import joblib
from sklearn.dummy import DummyRegressor

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--learning_rate", type=float, default=0.01)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--optimizer", type=str, default="adam")
    parser.add_argument("--epochs", type=int, default=10)
    args = parser.parse_args()
    
    # Simulate training
    print(f"Training with params: learning_rate={args.learning_rate}, batch_size={args.batch_size}, optimizer={args.optimizer}, epochs={args.epochs}", flush=True)
    
    # Simulate metrics
    metrics = {
        "validation:accuracy": 0.84
    }
    
    # Print metrics to stdout
    print(f"val_accuracy={metrics['validation:accuracy']}", flush=True)
    
    # Save a valid dummy model artifact
    model_dir = os.environ.get('SM_MODEL_DIR', '/opt/ml/model')
    os.makedirs(model_dir, exist_ok=True)
    
    # Create a simple dummy regressor
    model = DummyRegressor(strategy='mean')
    
    # Save the model using joblib
    model_path = os.path.join(model_dir, 'model.joblib')
    joblib.dump(model, model_path)
    
    print(f"Model saved to {model_path}", flush=True)
    """)

    print("Updated dummy_train.py has been written.")

    # Package the training script into a tar.gz file
    sourcedir_tar = "sourcedir.tar.gz"
    with tarfile.open(sourcedir_tar, "w:gz") as tar:
        tar.add(dummy_script_path, arcname=os.path.basename(dummy_script_path))
    print("Updated training script packaged into sourcedir.tar.gz.")

    # Upload to S3
    s3_prefix = "sagemaker-sklearn-automl-tuning/source"
    s3_tar_path = sagemaker_session.upload_data(
        path=sourcedir_tar,
        bucket=sagemaker_session.default_bucket(),
        key_prefix=s3_prefix
    )
    print(f"Updated training script uploaded to S3 at {s3_tar_path}.")
    logger.info(f"Training script uploaded to S3 at {s3_tar_path}.")

    # Define the module_dir as the S3 URI of the tar.gz
    module_dir = s3_tar_path  # This should be the S3 URI
    module_name = "dummy_train"  # Name of the module (without .py)

    # Create a SageMaker Estimator with module_dir and module_name
    estimator = Estimator(
        image_uri=best_candidate_container,
        role=role_arn,
        instance_count=1,
        instance_type="ml.m5.large",
        output_path=tuning_output_s3_uri,
        sagemaker_session=sagemaker_session,
        metric_definitions=metric_definitions,  # Explicit metric definitions
        entry_point=module_name + ".py",
        source_dir=module_dir,  # Specify the S3 path where the script is located
        hyperparameters={
            "epochs": 10,
        },
    )

    logger.info("Estimator created with module_dir and module_name.")

    # Define hyperparameter ranges
    hyperparameter_ranges = {
        "learning_rate": ContinuousParameter(0.001, 0.1),
        "batch_size": IntegerParameter(16, 128),
        "optimizer": CategoricalParameter(["sgd", "adam", "rmsprop"]),
    }

    logger.info(f"Hyperparameter ranges defined: {hyperparameter_ranges}")

    # Create a hyperparameter tuner
    tuner = HyperparameterTuner(
        estimator=estimator,
        objective_metric_name="validation:accuracy",  # Must match the metric key in metrics.json
        objective_type="Maximize",
        hyperparameter_ranges=hyperparameter_ranges,
        metric_definitions=metric_definitions,
        max_jobs=10,
        max_parallel_jobs=2,
        base_tuning_job_name="sagemaker-sklearn-hpo",
    )

    logger.info("Hyperparameter tuner created.")

    # Debug: Test a single training job for metric verification
    logger.info("Testing a single training job for metric verification...")
    try:
        estimator.fit({"train": train_data_s3_uri}, wait=True)
        logger.info("Single training job completed. Check CloudWatch logs for metric definitions.")
    except Exception as e:
        logger.error(f"Single training job failed: {e}")
        # Clean up before raising
        shutil.rmtree(source_dir, ignore_errors=True)
        os.remove(sourcedir_tar)
        raise

    # Start tuning job
    logger.info("Starting hyperparameter tuning job...")
    try:
        tuner.fit({"train": train_data_s3_uri})
        tuner.wait()
        logger.info("Hyperparameter tuning job completed.")
    except Exception as e:
        logger.error(f"Hyperparameter tuning job failed: {e}")
        # Clean up before raising
        shutil.rmtree(source_dir, ignore_errors=True)
        os.remove(sourcedir_tar)
        raise

    # Get the best training job name
    best_training_job_name = tuner.best_training_job()
    if not best_training_job_name:
        logger.error("No best training job found.")
        raise ValueError("No best training job found.")
    logger.info(f"Best training job: {best_training_job_name}")

    # Clean up local files
    try:
        shutil.rmtree(source_dir)
        os.remove(sourcedir_tar)
        logger.info("Cleaned up local training script and tarball.")
    except Exception as cleanup_error:
        logger.warning(f"Failed to clean up local files: {cleanup_error}")

    
    return best_training_job_name



def deploy_best_candidate(
    sagemaker_session,
    best_training_job_name,
    endpoint_name,
    instance_type='ml.m5.large',
    initial_instance_count=1
):
    logger.info("Deploying the tuned model...")
    estimator = Estimator.attach(best_training_job_name, sagemaker_session=sagemaker_session)
    predictor = estimator.deploy(
        instance_type=instance_type,
        initial_instance_count=initial_instance_count,
        endpoint_name=endpoint_name
    )
    logger.info(f"Model deployed successfully to endpoint: {endpoint_name}")
    return predictor



def main():
    parser = argparse.ArgumentParser(description="Run Autopilot Job with Hyperparameter Tuning")
    parser.add_argument("--input-data-s3-uri", required=True, help="S3 URI for input data")
    parser.add_argument("--output-data-s3-uri", required=True, help="S3 URI for output data")
    parser.add_argument("--role-arn", required=True, help="SageMaker execution role ARN")
    parser.add_argument("--tuning-output-s3-uri", required=True, help="S3 URI for tuning output data")
    parser.add_argument("--endpoint-name", required=True, help="Name for the deployed endpoint")
    args = parser.parse_args()

    session = boto3.Session()
    sagemaker_session = Session(boto_session=session)

    # Step 1: Start Autopilot Job
    logger.info("Starting Autopilot job...")
    automl = AutoML(
        role=args.role_arn,
        target_attribute_name="Price",
        output_path=args.output_data_s3_uri,
        problem_type="Regression",
        job_objective={'MetricName': 'RMSE'},
        sagemaker_session=sagemaker_session
    )

    automl.fit(inputs=args.input_data_s3_uri, job_name="car-price-autopilot-job")
    logger.info("Autopilot job started successfully.")

    # Step 2: Wait for Autopilot job completion
    logger.info("Waiting for Autopilot job to complete...")
    automl.wait()
    logger.info("Autopilot job completed.")

    # Step 3: Extract Best Candidate Model
    logger.info("Retrieving the best candidate model...")
    best_candidate = automl.describe_auto_ml_job()["BestCandidate"]
    best_candidate_container = best_candidate["InferenceContainers"][0]["Image"]
    logger.info(f"Best candidate container: {best_candidate_container}")

    # Step 4: Run Hyperparameter Tuning
    logger.info("Starting hyperparameter tuning...")
    best_training_job_name = create_hyperparameter_tuning_job(
        sagemaker_session=sagemaker_session,
        best_candidate_container=best_candidate_container,
        role_arn=args.role_arn,
        train_data_s3_uri=args.input_data_s3_uri,
        tuning_output_s3_uri=args.tuning_output_s3_uri
    )
    logger.info(f"Hyperparameter tuning completed with the best training job: {best_training_job_name}")

    # Step 5: Deploy the Best Model
    logger.info(f"Deploying the best model from training job {best_training_job_name}...")
    deploy_best_candidate(
        sagemaker_session=sagemaker_session,
        automl_job=automl,
        endpoint_name=args.endpoint_name
    )
    logger.info("Best model deployed successfully.")

if __name__ == "__main__":
    main()

