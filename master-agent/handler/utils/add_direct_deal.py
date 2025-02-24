import boto3
import json
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from config.index import  CARS_TABLE, ELK_AGENT_ENGINE, USER_TABLE,CURRENT_ENV,STEP_FUNC_ARN_DEV, STEP_FUNC_ARN_PROD
import json
from decimal import Decimal
from utils.elastic import client
from elasticsearch import NotFoundError



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



dynamodb = boto3.resource('dynamodb',
            region_name = "ap-south-2" if CURRENT_ENV == "dev" else "ap-south-1"
)
user_table = dynamodb.Table(USER_TABLE)
cars_table = dynamodb.Table(CARS_TABLE)

lambda_client = boto3.client(
    "lambda",
    region_name = "ap-south-2" if CURRENT_ENV == "dev" else "ap-south-1"  # Specify the AWS region
)

step_functions = boto3.client(
    "stepfunctions",
    region_name = "ap-south-2" if CURRENT_ENV == "dev" else "ap-south-1"  # Specify the AWS region
)



def add_direct_deal(data, phone_number):
    try:
        print("add_car 24",phone_number)
        print("add_car 24",type(phone_number))
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
            'carId':car["car_id"],
            'number':phone_number,
            'email':user_email,
            'type':'direct_deal'
        }
        print("payload",payload)
        
        # Step 3: Invoke the Lambda function
        lambda_response = lambda_client.invoke(
            FunctionName="cars",
            InvocationType='Event',  # Synchronous invocation
            LogType="Tail",
            Payload=json.dumps(payload)
        )
        
        # Parse the response from Lambda
        #response_payload = json.loads(lambda_response['Payload'].read().decode('utf-8'))
        print("Direct deal Lambda response:", lambda_response)
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
def start_convo(car_id,phone_number):
    print("start_convo",car_id,phone_number)
    
    cars_data = cars_table.get_item(Key={'carId': car_id}, ProjectionExpression='seller_id')

        
   
        
    cars_data_final = decimal_to_native(cars_data)
    print('cars_data',cars_data_final)
    print('seller_id',type(cars_data_final['Item']['seller_id']))
    # Perform the search
    response = client.search(
        index="users_dev" if CURRENT_ENV == "dev" else "users" ,  # Replace with your index name
        body={
            "query": {
                "term": {  # Use "match" if analyzing text
                    "userId": cars_data_final['Item']['seller_id']
                }
            },
            "_source": ["number"]  # Fetch only the phoneNumber field
        }
    )
    seller_number=""
# Extract phone number from the response
    if response['hits']['hits']:
        print("asda",response['hits']['hits'])
        seller_number = response['hits']['hits'][0]['_source']['number']
        print(f"Phone Number: {phone_number}")
    else:
        print("No user found with the given userId!")
        
    # Get the current UTC time
    current_time = datetime.utcnow()

    # Add 5 minutes
    future_time = current_time + timedelta(minutes=5)

    # Format the result in ISO format
   # Format the result in ISO 8601 with the 'Z' marker for UTC
    iso_time = future_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    print("iso_time",iso_time)

    buyer_response = client.update(
                index=ELK_AGENT_ENGINE,
                id=phone_number,
                body={
                    "doc": {
                       "convoId": seller_number
                    }
                }
            )
    print("updated elastic buyer",buyer_response)
    try:
        seller_response = client.update(
            index=ELK_AGENT_ENGINE,
            id=seller_number,
            body={
                "doc": {
                    "convoId": phone_number
                }
            }
        )
        print("updated elastic seller",seller_response)
    except NotFoundError:
        # If the document doesn't exist, create it manually
        # seller_response = client.index(
        #     index=ELK_AGENT_ENGINE,
        #     id=seller_number,
        #     body={
        #         "convoId": phone_number
        #     }
        # )
        current_time = datetime.now()  # Get the current UTC time
        iso_time = current_time.isoformat()
        print("Adding new document...")
        new_user = {
                        "number": seller_number,
                        "messages": [],
                        "createdAt": iso_time,
                        "updatedAt": iso_time,
                        "24hWindowActive": False,
                        "last_customer_message_time": iso_time,
                        "convoId":phone_number
                    }
        print("new_user", new_user)

        response = client.index(index=ELK_AGENT_ENGINE, id=seller_number, body=new_user)
        print("Seller agent created successfully.")   


    #Whatsapp-Connect
    # Start the Step Function execution
    response = step_functions.start_execution(
        stateMachineArn=STEP_FUNC_ARN_DEV if CURRENT_ENV == "dev" else STEP_FUNC_ARN_PROD,
        input=json.dumps({
            "type": "whatsapp_connect",
            "car_id": car_id,
            "buyer": phone_number,
            "seller":seller_number,
            "timestamp": iso_time,
            "subtype":"connect"
        })
    )
    
    
    lambda_response = lambda_client.invoke(
            FunctionName="whatsapp",
            InvocationType='Event',  # Synchronous invocation
            LogType="Tail",
            Payload=json.dumps({
                "type": "whatsapp_connect",
                "seller":seller_number,
                "buyer": phone_number,
                "car_id": car_id
            })
    )
    
    
    print("whatsapplambda response",lambda_response)
    
    return {'success': True, 'message': 'You are now connected to seller'}

    
    
    
def end_convo(phone_number):
    print("end_convo")


    convo_exists=False
    user_doc = client.get(
            index=ELK_AGENT_ENGINE,
            id=phone_number,
            _source_includes=['convoId']
    )
    
    print("user_doc",user_doc)
    
    if 'convoId' in user_doc['_source'] and user_doc['_source']['convoId'] != '':
        convo_exists=True
        user_response = client.update(
                    index=ELK_AGENT_ENGINE,
                    id=phone_number,
                    body={
                        "doc": {
                        "convoId": ""
                        }
                    }
        )
        print("removed person convo")
        person_response = client.update(
                    index=ELK_AGENT_ENGINE,
                    id=user_doc['_source']['convoId'],
                    body={
                        "doc": {
                        "convoId": ""
                        }
                    }
        )
        print("removed 2ndperson convo")
        
    return convo_exists,user_doc['_source']['convoId']

    
    
        
    
     
  
    
def send_convo(phone_number):
    user_doc = client.get(
            index=ELK_AGENT_ENGINE,
            id=phone_number,
            _source_includes=['convoId']
    )
    
    
    # Check if 'convoId' exists in the returned document
    if 'convoId' in user_doc['_source'] and user_doc['_source']['convoId'] != '':
        current_time = datetime.now()  # Get the current UTC time
        iso_time = current_time.isoformat()  # Get the ISO format timestamp for Elasticsearch
        result = True,user_doc['_source']["convoId"]
        message_source="whatsapp"
        update_script = """
            // Update the 'updatedAt' field if the timestamp is provided
            if (params.updatedAt != null) {
                ctx._source.updatedAt = params.updatedAt;
            }

            // Ensure 'last_message_source' is set
            if (params.source != null) {
                ctx._source.last_message_source = params.source;
            }

       

            // Calculate if the 24-hour window is active based on the last customer message time
            if (ctx._source.containsKey('last_customer_message_time') && params.updatedAt != null) {
                if (params.source == "whatsapp") {
                    // Use DateTimeFormatter to parse the timestamp with microseconds
                    def formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSSSSS");
                    def last_message_time = LocalDateTime.parse(ctx._source.last_customer_message_time, formatter);
                    def current_time = System.currentTimeMillis(); // Get current time in milliseconds

                    // Calculate the time difference in milliseconds
                    def last_message_time_in_millis = last_message_time.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli();
                    def time_difference = current_time - last_message_time_in_millis;

                    // Check if the 24-hour window has expired
                    def window_expired = time_difference > (24 * 60 * 60 * 1000); // 24 hours in milliseconds
                    ctx._source['24hWindowActive'] = !window_expired;  // Only update if it's whatsapp
                }
            }

            // Initialize 'last_message_time' if the message is from WhatsApp
            if (params.source == "whatsapp" && params.updatedAt != null) {
                ctx._source.last_message_time = params.updatedAt;
            }

            // Initialize '24hWindowActive' if it does not exist, but for all message sources (initialize as true for WhatsApp)
            if (!ctx._source.containsKey('24hWindowActive')) {
                ctx._source['24hWindowActive'] = (params.source == "whatsapp") ? true : false;  // true for WhatsApp, false for others
            }
        """

        # Add the current message timestamp and other params to the script
        response = client.update(
                index=ELK_AGENT_ENGINE,
                id=phone_number,
                body={
                    "script": {
                        "source": update_script,
                        "params": {
                            "updatedAt": iso_time,
                            "source": message_source  # Can be "App", "Web", or "WhatsApp"
                        }
                    },
                    "upsert": {
                    "updatedAt": iso_time,
                    "last_customer_message_time": iso_time, 
                    "last_message_source": message_source 
                }
            }
        )
    else:
        result = False, ""
        

    return result
    