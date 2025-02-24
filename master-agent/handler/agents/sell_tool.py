import json
import boto3
from typing import Annotated
from langgraph.prebuilt import InjectedState
from langchain_core.messages import AIMessage, HumanMessage
from config.index import CURRENT_ENV

# Initialize Lambda client
lambda_client = boto3.client(
    "lambda",
    region_name="ap-south-2" if CURRENT_ENV == "dev" else "ap-south-1"
)

def sell_tool(state: Annotated[dict, InjectedState]):
    """
    Processes the user's request to sell a car.
    Interacts with the sell Lambda function and prevents recursion.
    """
    user_role = state.get("user_role",None)
    env = state.get("env",None)
   
    print("state", state)
    print("Line 33 Received message in sell tool:", state["messages"])
    # print("phone_number", state["phone_number"])
    # phone_number = state["phone_number"]
    serialized_messages = [
    {"role": "user" if isinstance(msg, HumanMessage) else "assistant", "content": msg.content}
    for msg in state["messages"]
    if isinstance(msg, (HumanMessage, AIMessage))
    ]
    print("Line 40 serialized message in sell tool:", serialized_messages)
   

    print("Invoking Sell Lambda:")
    params = {
        "FunctionName": "ai-agent-handler-sell",
        "InvocationType": "RequestResponse",
        "Payload": json.dumps({
            "messages": serialized_messages,
            "user_roles": user_role,
            "env": env
        })
    }
    try:
        response = lambda_client.invoke(**params)
        print("Lambda invocation successful. Response metadata:", response.get("ResponseMetadata", {}))
        print("line 53 sell  response",type(response))
        print("line 54 sell response",response)
        response_payload = json.loads(response["Payload"].read())
        print("Sell Tool Response Payload:", response_payload)

        body = json.loads(response_payload.get("body", "{}"))
        print("Line 61 sell:", body)
        # Add status to signal awaiting user input
        body["status"] = "awaiting_user_input"
        return body
    except Exception as e:
        print(f"Error in sell_tool: {e}")
        return {"success": False, "message": "An error occurred in sell_tool."}
    # response_payload = json.loads(response["Payload"].read())
    # print("Sell Tool Response Payload:", response_payload)

#    body = json.loads(response_payload.get("body", "{}"))
    
    # Handle car upload scenario
   #a:", body.get("data"))

    
    #return body
      #  resp = add_car(body["data"], phone_number)
       # car_body = json.loads(resp["body"])
        #url = car_body["Item"]["url"]
       # print("car upload url:", url)
    # payload = {
    #         "messages": messages
    #     }
    # print("payload:", payload)

    #     # Define the API endpoint
    # api_url = 'http://host.docker.internal:3002/agent/chat/sell'  # Replace with actual Lambda endpoint

    # try:
    #     response = requests.post(api_url, json=payload)
    #     if response.status_code == 200:
    #         try:
    #             response_data = response.json()
    #             if "body" in response_data:
    #                 body = json.loads(response_data["body"])
    #             else:
    #                 body = response_data
    #         except json.JSONDecodeError:
    #                 print("Error: The server response is not in JSON format.")
    #     else:
    #         print(f"Failed to connect to the agent. Status code: {response.status_code}")
    # except requests.exceptions.RequestException as e:
    #     print("Error:", e)
        
    # return  body.get("message", "Default Sell Response")
        