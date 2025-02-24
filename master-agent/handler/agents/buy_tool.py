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

def buy_tool(state: Annotated[dict, InjectedState]):
    """
    Processes the user's request to buy a car.
    Interacts with the buy Lambda function and prevents recursion.
    """
    print("Inovking Buy Lambda")
    print("Line 33 Received message in buy tool:", state["messages"])
  
    serialized_messages = [
    {"role": "user" if isinstance(msg, HumanMessage) else "assistant", "content": msg.content}
    for msg in state["messages"]
    if isinstance(msg, (HumanMessage, AIMessage))
    ]
    
    phone_number = state.get("phone_number", None)
    
    params = {
        "FunctionName": "ai-agent-handler-search",
        "InvocationType": "RequestResponse",
        "Payload": json.dumps({
            "messages": serialized_messages,
            "phone_number": phone_number
        })
    }

    try:

        response = lambda_client.invoke(**params)
        print("Lambda invocation successful. Response metadata:", response.get("ResponseMetadata", {}))
        print("line 53 buy  response",type(response))
        print("line 54 buy response",response)
        response_payload = json.loads(response["Payload"].read())
        print("Buy Tool Response Payload:", response_payload)

        body = json.loads(response_payload.get("body", "{}"))
        print("Line 47 buy:", body)
        # Add status to signal awaiting user input
        body["status"] = "awaiting_user_input"
        return body
    except Exception as e:
        print(f"Error in sell_tool: {e}")
        return {"success": False, "message": "An error occurred in buy_tool."}