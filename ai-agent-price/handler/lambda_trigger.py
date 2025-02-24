# lambda_handler.py

import json
import os
import boto3

from config.index import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_SESSION_TOKEN,
    REGION_NAME
)

from predict import predict_price  # We'll import our custom prediction function

def lambda_handler(event, context):
    """
    A combined Lambda handler that:
    1) Detects if the event is from S3 (ObjectCreated) -> triggers the SageMaker Pipeline.
    2) Detects if the event is from API Gateway -> performs inference using predict.py
       without re-triggering the pipeline.
    """

    # Check if this is an S3 event (object upload)
    if "Records" in event and event["Records"]:
        # S3 events usually have structure event["Records"][0]["s3"]["object"]["key"], etc.
        # We'll assume it's the S3 -> new CSV file -> start pipeline scenario
        return handle_s3_event(event)

    # Else, assume it's an API Gateway event
    # e.g., { "resource": "/", "path": "/", "httpMethod": "POST", ... }
    if "httpMethod" in event:
        return handle_api_request(event)

    # If it's something else
    return {
        "statusCode": 400,
        "body": json.dumps("Unrecognized event format.")
    }

def handle_s3_event(event):
    """
    Called when there's a new object in S3. Triggers the SageMaker Pipeline.
    """
    print("Handling S3 event for pipeline trigger:", json.dumps(event))

    sagemaker_client = boto3.client(
        "sagemaker",
        region_name=REGION_NAME,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_session_token=AWS_SESSION_TOKEN
    )

    pipeline_name = os.environ.get("PIPELINE_NAME", "CarPricePipeline")
    input_bucket = os.environ.get("INPUT_BUCKET", "car-price-data")
    input_prefix = os.environ.get("INPUT_PREFIX", "raw_data/")
    output_prefix = os.environ.get("OUTPUT_PREFIX", "autopilot_output/")
    instance_type = os.environ.get("INSTANCE_TYPE", "ml.m5.large")
    max_candidates = os.environ.get("MAX_CANDIDATES", "5")

    response = sagemaker_client.start_pipeline_execution(
        PipelineName=pipeline_name,
        PipelineParameters=[
            {"Name": "InputBucket", "Value": input_bucket},
            {"Name": "InputPrefix", "Value": input_prefix},
            {"Name": "OutputPrefix", "Value": output_prefix},
            {"Name": "InstanceType", "Value": instance_type},
            {"Name": "MaxCandidates", "Value": max_candidates}
        ]
    )

    pipeline_execution_arn = response["PipelineExecutionArn"]
    print("Started pipeline execution:", pipeline_execution_arn)

    return {
        "statusCode": 200,
        "body": json.dumps(
            f"S3 Event -> Pipeline triggered successfully! Execution ARN: {pipeline_execution_arn}"
        )
    }

def handle_api_request(event):
    """
    Called when there's an API Gateway event. 
    We want to perform inference with predict.py instead of triggering the pipeline.
    """
    http_method = event["httpMethod"]

    # We might handle GET vs. POST differently.
    # For GET, perhaps just a "health check" or a sample message.
    if http_method == "GET":
        return {
            "statusCode": 200,
            "body": json.dumps("Hello from GET! Call POST with a JSON payload for predictions.")
        }

    # For POST, parse the JSON body to get the input data for prediction
    if http_method == "POST":
        try:
            body = event.get("body", "{}")
            # If it's a JSON string, parse it
            data = json.loads(body)
            # We expect data to be something like:
            # {
            #   "Make": "Audi",
            #   "Model": "Q3",
            #   ...
            # }

            endpoint_name = os.environ.get("ENDPOINT_NAME", "CarPriceEndpoint")
            predicted_price = predict_price(data, endpoint_name)

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Prediction success",
                    "input": data,
                    "predicted_price": predicted_price
                })
            }

        except Exception as e:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "message": "Prediction failed",
                    "error": str(e)
                })
            }

    # Otherwise, method not supported
    return {
        "statusCode": 405,
        "body": json.dumps(f"Method {http_method} not supported.")
    }
