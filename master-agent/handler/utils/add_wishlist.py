import boto3
import json
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from config.index import  USER_TABLE,CURRENT_ENV
import json
from decimal import Decimal


# Function to convert Decimal to native Python types
def decimal_to_native(obj):
    if isinstance(obj, Decimal):
        # Convert Decimal to float or int as needed
        return int(obj) if obj % 1 == 0 else float(obj)
    elif isinstance(obj, list):
        return [decimal_to_native(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: decimal_to_native(value) for key, value in obj.items()}
    else:
        return obj


# Initialize the DynamoDB client and Lambda client
dynamodb = boto3.resource('dynamodb',
            region_name = "ap-south-2" if CURRENT_ENV == "dev" else "ap-south-1"  # Specify the AWS region
        )
user_table = dynamodb.Table(USER_TABLE)

lambda_client = boto3.client(
    "lambda",
    region_name = "ap-south-2" if CURRENT_ENV == "dev" else "ap-south-1"  # Specify the AWS region
)



def add_wishlist(data, phone_number):
    try:
        print("add_wishlist 24",phone_number)
        print("add_wishlist 24",type(phone_number))
        # Step 1: Fetch the userId using the phone number from DynamoDB
        # user_params = {
        #     'TableName': USER_TABLE,
        #     'IndexName': 'number-index',
        #     'KeyConditionExpression': '#number = :number',
        #     'ExpressionAttributeNames': {
        #         '#number': 'number'
        #     },
        #     'ExpressionAttributeValues': {
        #         ':number': phone_number
        #     },
        #     'ProjectionExpression': 'userId'
        # }
        
        # Query DynamoDB
       # user_data = dynamodb.query(user_params)
        user_data_one = user_table.query(
            IndexName='number-index',
            KeyConditionExpression=Key('number').eq(phone_number),
            ProjectionExpression='userId,email'
        )
        
        print("user_Data",user_data_one)
        user_data = decimal_to_native(user_data_one)
        
        # Check if userId is found
        if 'Items' not in user_data or len(user_data['Items']) == 0:
            print(f"User not found for phone number: {phone_number}")
            return {'success': False, 'message': 'User not found.'}
        
        user_id = user_data['Items'][0]['userId']
        user_email = user_data['Items'][0]['email']
        print(f"Fetched userId: {user_id}")
        car = data[0]
        # Step 2: Prepare payload for Lambda function to upload car details
        payload = {
            'body':{
                'itemId':car["car_id"],
                'itemType':'car'
            },
            'user_email':user_email,
            'type':'wishlist',
        }
        print("payload",payload)
        
        # Step 3: Invoke the Lambda function
        lambda_response = lambda_client.invoke(
            FunctionName="wishlist",
            InvocationType='Event',  # Synchronous invocation
            LogType="Tail",
            Payload=json.dumps(payload)
        )
        print("lambda_response",lambda_response)
        
        # Parse the response from Lambda
        # response_payload = json.loads(lambda_response['Payload'].read().decode('utf-8'))
        # print("Lambda response:", response_payload)
        return True

    except ClientError as e:
        print(f"Error: {e}")
        return {'success': False, 'message': 'Failed to upload car details.'}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {'success': False, 'message': 'An unexpected error occurred.'}


# # Example usage
# if __name__ == "__main__":
#     car_data = {
#         'vehicle_number': 'GJ03NB1007',
#         'year': 2019,
#         'company': 'Honda',
#         'model': 'Amaze',
#         'variant': 'LX',
#         'price': 20000,
#         'odometer_reading': 6000,
#         'fuel_type': 'Diesel',
#         'color': 'Red'
#     }
#     phone_number = '+911234567890'
    
#     response = add_car(car_data, phone_number)
#     print("Car upload response:", response)
