import boto3
import json
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from config.index import CARS_TABLE, ELK_CAR_ENGINE, S3_DEV_URL, S3_PROD_URL, USER_TABLE,CURRENT_ENV,DEV_URL, PROD_URL,S3_BUCKET_NAME
import json
from decimal import Decimal
import uuid
import time
from utils.elastic import client



s3 = boto3.client('s3',
            region_name = "ap-south-2" if CURRENT_ENV == "dev" else "ap-south-1"
    )

# Regular expression to match the VIN
vin_pattern = r"VIN:\s*([A-Z0-9]+)"


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
            region_name = "ap-south-2" if CURRENT_ENV == "dev" else "ap-south-1"
)
user_table = dynamodb.Table(USER_TABLE)
cars_table = dynamodb.Table(CARS_TABLE)

lambda_client = boto3.client(
    "lambda",
    region_name = "ap-south-2" if CURRENT_ENV == "dev" else "ap-south-1"
)



def get_car_by_id(carId):
    cars_data = cars_table.get_item(Key={'carId': carId}, ProjectionExpression='attributes,vin')
        
    print('cars_data',cars_data)
        
    cars_data_final = decimal_to_native(cars_data)
    
    return cars_data_final['Item']


def add_car(data, phone_number,user_role):
    try:
        print("add_car 24",phone_number)
        print("add_car 24",type(phone_number))
        # Step 1: Fetch the userId using the phone number from DynamoDB
        # user_params = {
        #     'TableName': SUBSCRIPTIONS_TABLE,
        #     'Key': {
        #         'subType': phone_number  # Replace with the appropriate primary key and value
        #     },
        #     'ProjectionExpression': 'userId'
        # }
        
        # #Query DynamoDB
        # user_data = dynamodb.query(user_params)
       

        cars_data_one = cars_table.query(
            IndexName='vin-index',
            KeyConditionExpression=Key('vin').eq(data['vehicle_number']),
            ProjectionExpression='carId'
        )
        
        
          # Check if userId is found
        if 'Items' not in cars_data_one or len(cars_data_one['Items']) == 1:
            print(f"Car Already exists: {data['vehicle_number']}")
            return {'success': False, 'message': f"Sorry this car with {data['vehicle_number']} vehicle number already exists"}, ""


        print("line 85 add car",phone_number)
       
        user_data_one = user_table.query(
            IndexName='number-index',
            KeyConditionExpression=Key('number').eq(phone_number),
            ProjectionExpression='userId'
        )
        
        print("user_Data",user_data_one)
        user_data = decimal_to_native(user_data_one)
        
        # Check if userId is found
        if 'Items' not in user_data or len(user_data['Items']) == 0:
            print(f"User not found for phone number: {phone_number}")
            return {'success': False, 'message': f"Sorry this your account is not registered with us.\nPlease signup first"},""
        
        user_id = user_data['Items'][0]['userId']
        print(f"Fetched userId: {user_id}")
        car_id = str(uuid.uuid4()) + str(int(time.time()))
        # Step 2: Prepare payload for Lambda function to upload car details
        payload = {
            'userId': user_id,
            'vin': data['vehicle_number'],
            'year': data['year'],
            'make': data['company'],
            'model': data['model'],
            'trim': data['variant'],
            'vehicle_type': 'car',
            'price': data['price'],
            'odometer': data['odometer_reading'],
            'FuelType': data['fuel_type'],
            'exterior_color': data['color'],
            'type': 'car_upload',
            'carId': car_id
        }
        
        
        # Step 3: Invoke the Lambda function
        lambda_response = lambda_client.invoke(
            FunctionName=CARS_TABLE,
            InvocationType='Event',
            LogType="Tail",
            Payload=json.dumps(payload)
        )
        print("add_car response",lambda_response)
        url=f"{DEV_URL if CURRENT_ENV == 'dev' else PROD_URL}cars/edit/{car_id}"

   
        # Parse the response from Lambda
        # response_payload = json.loads(lambda_response['Payload'].read().decode('utf-8'))
        # print("Lambda response:", response_payload)
        return {'success': True, 'message': 'Car Uploaded'}, url

    except ClientError as e:
        print(f"Error: {e}")
        return {'success': False, 'message': 'Failed to upload car details.'}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {'success': False, 'message': 'An unexpected error occurred.'}

def get_car_by_vin(vin):
    cars_data_one = cars_table.query(
            IndexName='vin-index',
            KeyConditionExpression=Key('vin').eq(vin),
            ProjectionExpression='carId'
        )
    cars_data = decimal_to_native(cars_data_one)
    return cars_data["Items"][0]["carId"]
        
        # Check if userId is found
    # if 'Items' not in cars_data_one or len(cars_data_one['Items']) == 0:
    #     print(f"Car Already exists: {vin}")
    #     return {'success': False, 'message': f"Sorry this car with {data['vehicle_number']} vehicle number already exists"}, ""


    # print("line 85 add car",phone_number)
    

def get_user_cars(phone_number):
    print("get_user_cars 134",phone_number)

    phone_number = str(phone_number)
    user_data_one = user_table.query(
        IndexName='number-index',
        KeyConditionExpression=Key('number').eq(phone_number),
        ProjectionExpression='userId,lastAddedVIN,#role',
        ExpressionAttributeNames={
        '#role': 'role'
    }
    )

    print("user_Data",user_data_one)
    user_data = decimal_to_native(user_data_one)

    # Check if userId is found
    if 'Items' not in user_data or len(user_data['Items']) == 0:
        print(f"User not found for phone number: {phone_number}")
        return None
    user_id = user_data['Items'][0]['userId']

    print(f"Fetched userdetails: {user_id}")    
    
    cars_data_one=None
   
    cars_data_one = cars_table.query(
        IndexName='seller_id-index',
        KeyConditionExpression=Key('seller_id').eq(user_id),
        ProjectionExpression='carId,vin,attributes.make,attributes.model,attributes.#trim,attributes.#year',
         ExpressionAttributeNames={
        '#trim': 'trim',
        "#year":"year"
        }
    )

    print("user_Data",cars_data_one)
    cars_data = decimal_to_native(cars_data_one)

    print(f"Fetched cars: {cars_data['Items']}") 

    if len(cars_data['Items']) == 0: 
        return None   

    return cars_data['Items']
    
        
        
    
    
    
def remove_car(vehicle_number,phone_number):
    print("remove_car",vehicle_number,phone_number)
    cars_data_one = cars_table.query(
        IndexName='vin-index',
        KeyConditionExpression=Key('vin').eq(vehicle_number),
        ProjectionExpression='carId,seller_id'
    )
        
        
    # Check if car is found
    if 'Items' not in cars_data_one or len(cars_data_one['Items']) == 0:
            print(f"Car Doesn't exists: {vehicle_number}")
            return {'success': False, 'message': f"Sorry this car with {vehicle_number} vehicle number doesn't exists"}
    
    
    print("cars_Data",cars_data_one)
    cars_data = decimal_to_native(cars_data_one)
    seller_id = cars_data['Items'][0]['seller_id']
    carId = cars_data['Items'][0]['carId']
    
    user_data_one = user_table.query(
        IndexName='number-index',
        KeyConditionExpression=Key('number').eq(phone_number),
        ProjectionExpression='userId,lastAddedVIN,#role',
        ExpressionAttributeNames={
        '#role': 'role'
    }
    )

    print("user_Data",user_data_one)
    user_data = decimal_to_native(user_data_one)
    
    user_id = user_data['Items'][0]['userId']

    print(f"Fetched userdetails: {user_id}")  
    

    # Check if userId is found
    if 'Items' not in user_data or len(user_data['Items']) == 0:
        print(f"User not found for phone number: {user_id}")
        return {'success': False, 'message': f"Sorry this your account is not registered with us.\nPlease signup first"}

    print(f"userId is sellerId {user_id == seller_id} {user_id} {seller_id}")  
    # Check if userId and seller_id is same or not
    if seller_id != user_id:
        print(f"Car is not of same seller: {user_id} {seller_id}")
        return {'success': False, 'message': f"Sorry unable to find car.Please add a car first"}


      
     # Step 2: Prepare payload for Lambda function to upload car details
    payload = {
        'carId': carId,
        'type': 'delete_car',
    }
        
        
        # Step 3: Invoke the Lambda function
    lambda_response = lambda_client.invoke(
        FunctionName=CARS_TABLE,
        InvocationType='Event',
        LogType="Tail",
        Payload=json.dumps(payload)
    )
    print("delete_car response",lambda_response)


   
    # Parse the response from Lambda
    # response_payload = json.loads(lambda_response['Payload'].read().decode('utf-8'))
    # print("Lambda response:", response_payload)
    return {'success': True, 'message': 'We have succesfully removed your car from our CarXstream'}





def add_car_images(data,phone_number):

    try:
        # Find VIN
        car_id = data["carId"]
        
        cars_data = cars_table.get_item(Key={'carId': car_id}, ProjectionExpression='seller_id,images,thumbnail,vin')
        
        print('cars_data',cars_data)
        
        cars_data_final = decimal_to_native(cars_data)
        s3_folder=f"documents/users/{phone_number}/images/"
        s3response = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=s3_folder)
        
        
        # List of file keys in the folder
        file_keys = [item['Key'] for item in s3response['Contents']]
            
        print("Files found in the folder:", file_keys)
        
        if len(file_keys) ==0:
            return {'success': False, 'message': 'No images has been uploaded yet'}


        images = [] 
        # Target folder for new uploads
        # new_s3_folder = f"documents/users/{cars_data_final['Item']['seller_id']}/processed_images/"
        new_s3_folder = f"carimages/{cars_data_final['Item']['vin']}/"

        for key in file_keys:
            # Define new key for uploaded file
            new_key = key.replace(s3_folder, new_s3_folder)

            # Copy object to new folder
            s3.copy_object(
                Bucket=S3_BUCKET_NAME,
                CopySource={'Bucket': S3_BUCKET_NAME, 'Key': key},
                Key=new_key
            )
            
            # Append the new URL to the images list
            if CURRENT_ENV == "dev":
                images.append({'url': S3_DEV_URL + new_key, 'validated': False})
            else:
                images.append({'url': S3_PROD_URL + new_key, 'validated': False})


            
        print('images',images)    
        
        if len(images) == 0:
            return {'success': True, 'message': 'We have succesfully uplaoded images'}
            
        
        
        # dynamodb_response = cars_table.update_item(
        #     Key={'carId': car_id},
        #     UpdateExpression="""
        #         SET 
        #             photos = list_append(if_not_exists(photos, :empty_list), :new_urls),
        #             thumbnail = :thumbnail
        #     """,
        #     ConditionExpression="attribute_not_exists(thumbnail) OR thumbnail = :empty_string",
        #     ExpressionAttributeValues={
        #         ':empty_list': [],
        #         ':new_urls': images,
        #         ':thumbnail': images[0]['url'],
        #         ':empty_string': ""  # Checks for empty string
        #     },
        #     ReturnValues="UPDATED_NEW"
        # )
        dynamodb_response = cars_table.update_item(
        Key={'carId': car_id},
        UpdateExpression="""
            SET 
                photos = list_append(if_not_exists(photos, :empty_list), :new_urls),
                thumbnail = :thumbnail
        """,
        ExpressionAttributeValues={
            ':empty_list': [],
            ':new_urls': images,
            ':thumbnail': images[0]['url'],  # Always set the thumbnail to the first image URL
        },
        ReturnValues="UPDATED_NEW"
    )

        
        print("DynamoDB update successful:", dynamodb_response['Attributes'])
        
        
        car_doc = client.get(
            index=ELK_CAR_ENGINE,
            id=car_id,
            _source_includes=['image']
        )
        thumbnail = car_doc['_source'].get('image', "")
        
        if thumbnail == "":
            response = client.update(
                index=ELK_CAR_ENGINE,
                id=car_id,
                body={
                    "doc": {
                        "thumbnail": images[0]['url']
                    }
                }
            )
            print("updated elastic thumbnail",response)
        
        for key in file_keys:
        # Define the new key for the archived file
            archived_key = "archived/" + s3_folder + key.split('/')[-1]

            # Copy the file to the archived location
            s3.copy_object(
                Bucket=S3_BUCKET_NAME,
                CopySource={'Bucket': S3_BUCKET_NAME, 'Key': key},
                Key=archived_key
            )

            # Delete the original file
            s3.delete_object(Bucket=S3_BUCKET_NAME, Key=key)
            print(f"Moved {key} to {archived_key}")
        
                # Delete the files
        # delete_response = s3.delete_objects(
        #         Bucket=S3_BUCKET_NAME,
        #         Delete={'Objects': [{'Key': key} for key in file_keys]}
        # )
        # print("Files deleted:", delete_response)

        return {'success': True, 'message': 'We have succesfully uploaded your car'}
    
    except Exception as e:
        print("add image error",e)
        return {'success': True, 'message': 'Looks like something went wrong.Please try again'}
        


def add_car_offer(vin,price,phone_number):

    cars_data_one = cars_table.query(
            IndexName='vin-index',
            KeyConditionExpression=Key('vin').eq(vin),
            ProjectionExpression='carId'
    )
    
    
        # Check if car is found
    if 'Items' not in cars_data_one or len(cars_data_one['Items']) == 0:
            print(f"Car Doesn't exists: {vin}")
            return {'success': False, 'message': f"Sorry this car with {vin} vehicle number doesn't exists",'offerId':''}
    
    

    cars_data = decimal_to_native(cars_data_one)
    print("cars_Data",cars_data_one)
    user_data_one = user_table.query(
            IndexName='number-index',
            KeyConditionExpression=Key('number').eq(phone_number),
            ProjectionExpression='email'
        )
        
    print("user_Data",user_data_one)
    user_data = decimal_to_native(user_data_one)
    #{"id":"67617715-213b-4b14-98de-0a24c4417f641723138715043","text":"I'd like to offer ₹12000 for this vehicle.","message":"asdad"}
    payload = {
        'id': cars_data["Items"][0]["carId"],
        'type': 'make_offer',
        'buyerId':user_data["Items"][0]["email"],
        'text':f"I'd like to offer {price} for this vehicle",
        "message":""
    }
     # Step 3: Invoke the Lambda function
    lambda_response = lambda_client.invoke(
            FunctionName="offer",
            InvocationType='RequestResponse',
            LogType="Tail",
            Payload=json.dumps(payload)
    )
    print("add_offer response",lambda_response)
    
    #Parse the response from Lambda
    response_payload = json.loads(lambda_response["Payload"].read())
    print("Make offer Response Payload:", response_payload)

    body = json.loads(response_payload.get("body", "{}"))
  
    return {'success': True, 'message':'Your offer has been proposed to seller','offerId':body.get("id")}    
