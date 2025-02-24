import json
from working import ask_question

# import requests


def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """

    # try:
    #     ip = requests.get("http://checkip.amazonaws.com/")
    # except requests.RequestException as e:
    #     # Send some context about this error to Lambda Logs
    #     print(e)

    #     raise e
    body = json.loads(event["body"]) if "body" in event else event
    # Extract relevant data from the request body
    # user_id = body.get("user", "Unknown")
    messages = body.get("messages", [])
    phone_number = body.get("phone_number", None)
   
    #print(messages)
    
    response = ask_question(messages, phone_number)
    # print("line 44 docs",docs)
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": response.get('message', ''),
            "data": response.get('docs',''),
            "type": response.get('type',''),
            "question": response.get('question',''),
            "vin": response.get('vin',''),
            "price": response.get('price',''),
            "area": response.get('area',''),
            "location": response.get('location',''),
            "date": response.get('date',''),
            "time": response.get('time',''),
            "amount": response.get('amount','')
        }),
    }
  
# import json
# from working import ask_question

# def lambda_handler(event, context):
#     print("Incoming event:", json.dumps(event))  # Log the raw event

#     try:
#         # Get the raw body and clean it up
#         raw_body = event["body"] if "body" in event else "{}"
#         clean_body = raw_body.replace("\u00a0", " ").replace("\r\n", "").strip()

#         # Parse the cleaned body
#         body = json.loads(clean_body)
#         print("Parsed body:", body)  # Logs the parsed body
#     except json.JSONDecodeError as e:
#         print(f"JSONDecodeError: {str(e)}")
#         return {
#             "statusCode": 400,
#             "body": json.dumps({
#                 "error": "Invalid JSON format",
#                 "details": str(e)
#             }),
#         }

#     # Extract messages
#     messages = body.get("messages", [])
#     phone_number = body.get("phone_number", None)
#     try:
#         response, docs, type_shortlisted = ask_question(messages, phone_number)
#     except Exception as e:
#         print(f"Error in ask_question: {str(e)}")
#         return {
#             "statusCode": 500,
#             "body": json.dumps({
#                 "error": "Internal Server Error",
#                 "details": str(e),
#             }),
#         }

#     return {
#         "statusCode": 200,
#         "body": json.dumps({
#             "message": response,
#             "data": docs,
#             "type": type_shortlisted,
#         }),
#     }

