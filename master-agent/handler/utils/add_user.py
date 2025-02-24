import boto3
import json
from botocore.exceptions import ClientError
from config.index import CURRENT_ENV

# Initialize the Lambda client
lambda_client = boto3.client(
    "lambda",
    region_name = "ap-south-2" if CURRENT_ENV == "dev" else "ap-south-1"  # Specify the AWS region
)

def add_user(phone_number):
    try:
        print(f"Adding user with phone number: {phone_number}")

        # Define the user data to be sent as the payload
        user_data = {
            "type": "lambda",
            "deviceTokens": [],
            "role": "user",
            "dealerName": "",
            "number": phone_number
        }

        # Set up parameters for invoking the Lambda function
        params = {
            'FunctionName': 'auth',  # Replace with your Lambda function name
            'InvocationType': 'Event',  # Synchronous invocation
            'Payload': json.dumps(user_data),
            'LogType':"Tail"# Convert the payload to a JSON string
        }

        # Invoke the Lambda function
        response = lambda_client.invoke(**params)
        print("lambda_user",response)

        # Parse the response from the invoked Lambda
        #response_payload = json.loads(response['Payload'].read().decode('utf-8'))
        #print("Response from auth:", response_payload)
        return True

    except ClientError as e:
        print(f"ClientError: {e}")
        return {'error': str(e)}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {'error': str(e)}

