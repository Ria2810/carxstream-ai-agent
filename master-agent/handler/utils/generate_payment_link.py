from decimal import Decimal
import boto3
import json
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from config.index import  SUBSCRIPTIONS_TABLE, USER_TABLE,CURRENT_ENV,CARS_TABLE
import json
from decimal import Decimal

dynamodb = boto3.resource('dynamodb',
        region_name = "ap-south-2" if CURRENT_ENV == "dev" else "ap-south-1" # Specify the AWS region
)
subscription_table = dynamodb.Table(SUBSCRIPTIONS_TABLE)
user_table = dynamodb.Table(USER_TABLE)
cars_table = dynamodb.Table(CARS_TABLE)

lambda_client = boto3.client(
    "lambda",
    region_name = "ap-south-2" if CURRENT_ENV == "dev" else "ap-south-1"  # Specify the AWS region
)



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





def generate_payment_link(amount, vehicle_number,user_role,phone_number,source):
    try:
        print("generate_payment_link amount",amount)
        print("generate_payment_link vehicle number",vehicle_number)
        # Step 1: Fetch the userId using the phone number from DynamoDB
        subType="dealer" if user_role == "dealer" else "car"
        subscription_params = {
            'TableName': SUBSCRIPTIONS_TABLE,
            'Key': {
                'subType': subType
            }
        }
        #print("subscription_params",subscription_params)
        
        subscription_data = subscription_table.get_item(**subscription_params)
        
       # print("subscription_data",subscription_data)
        
        amount_type=""
        # Assuming 'nestedObjectList' is the list you want to search through and match price
        if "Item" in subscription_data and "list" in subscription_data["Item"]:
            nested_list = subscription_data["Item"]["list"]
            print("nested_list",nested_list)
            # Iterate over the list to find the price match
            for obj in nested_list:
                if 'amount' in obj and obj['amount'] == Decimal(amount):  # Replace desired_price with the price you're looking for
                    #print("Match found:", obj)
                    amount_type = obj['type']
                else:
                    print("No match for this object:", obj)
        else:
            print("No nested list found in subscription data")
        # get user data      
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
        
        
         # get cars data      
        cars_data_one = cars_table.query(
            IndexName='vin-index',
            KeyConditionExpression=Key('vin').eq(vehicle_number),
            ProjectionExpression='carId'
        )
        
        print("cars_Data",cars_data_one)
        car_data = decimal_to_native(cars_data_one)
        
        # Check if carId is found
        if 'Items' not in car_data or len(car_data['Items']) == 0:
            print(f"car not found for phone number: {phone_number}")
            return {'success': False, 'message': 'car not found.'}
        
        car_id = car_data['Items'][0]['carId']
        print(f"Fetched carId: {car_id}")

        if amount_type:
            # Step 2: Prepare payload for Lambda function to upload car details
            payload = {
                'body':{
                    'type': amount_type,
                    'subType':  subType,
                    'itemType': 'car',
                    'carId': car_id,
                    'source': 'agent'
                },
                'email':user_email,
                'type':'payment',
            }
            print("payload",payload)
            # Add condition to modify body
            if source == "app":  # Replace 'condition' with your actual condition
                payload['body']['mobile'] = 'true' 

            
            # Step 3: Invoke the Lambda function
            lambda_response = lambda_client.invoke(
                FunctionName="payments",
                InvocationType='RequestResponse',  # Synchronous invocation
                Payload=json.dumps(payload)
            )
            print("lambda_response",lambda_response)
            
            #Parse the response from Lambda
            response_payload = json.loads(lambda_response["Payload"].read())
            print("Sell Tool Response Payload:", response_payload)

            body = json.loads(response_payload.get("body", "{}"))
            response = {
                'success': True,
                'message': "Please initiate the payment here to upgrade your car",
                'url': body.get('url', ''),
                'checksum': body.get('checksum', ''),
                'base64Encoded': body.get('base64Encoded', ''),
                'carId':car_id,
                'packageId': body.get("id",'')
            }
            return response
        else: 
            return  {'success': False, 'message': f"Sorry couldn't upgrade your car"}

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