import json
from config.index import S3_URL
from utils.add_direct_deal import end_convo
from utils.chat import add_payment_message
from utils.get_all_chat_messages import get_all_chat_messages
from utils.process_message import process_message
from utils.check_message import check_message


def lambda_handler(event, context):
    try:
        
        print("event",event)
        if  'httpMethod' in event and event['httpMethod'] == 'OPTIONS':
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST,GET,PATCH,PUT,OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type"
                }
            }
        # Determine the source of the event
        lambda_source = "whatsapp"
        if "requestContext" in event:
            lambda_source = "API Gateway"
            print("Event from API Gateway")
        else:
            print("Event from whatsapp")

     
        print("Lambda Source:", lambda_source)
        
        
         # Get the path
        path = event.get('requestContext', {}).get('resourcePath') or event.get('path')

        # Query parameters for GET requests
        query_params = event.get('queryStringParameters', {})

        print("Path:", path)
        print("Query Parameters:", query_params)
        
     

        if path == "/agent/chat/all":
            response = get_all_chat_messages(query_params)
            print("Response:", json.dumps(response, indent=2))
            return response        
        

        
        
           # Parse the body
        body = json.loads(event["body"]) if "body" in event else event

        print("Body:", body)

       
        if body.get('type') == "payment":
            print("body payment", body)    
            number= body.get("number")
            message= body.get("message")
            package_id=body.get("packageId")
            
            resp=add_payment_message(phone_number=number,message=message,package_id=package_id)
            return resp
        elif body.get('type') == "whatsapp_connect":
            print("body payment", body)    

            resp=end_convo(data=body)
            return resp
        # elif body.get('type') == "media":
        #     print("body media", body)    
        #     number= body.get("user")
        #     urls= body.get("urls")
        #     resp=get_user_cars(phone_number=number,images=urls)
        #     return resp   

        # Process the message using the process_message function
        # false_data= check_message(body.get("message"))        
        # if false_data:
        #     return {
        #     "statusCode": 200,
        #     "body": json.dumps({
        #         "message": "Sorry please ask appropriate answer",
                
        #     }),
        #     "headers": {
        #             "Content-Type": "application/json",
        #             "Access-Control-Allow-Origin": "*",
        #     },
        # }

        
        response = process_message(body)
        # response = master_agent(body)
        #print("Lambda Response:", response)
        return response
    

    except Exception as e:
        print("Error:", str(e))
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Unable to process request. Please try again later.",
                
            }),
            "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
            },
        }