import json
from langchain_core.messages.tool import ToolMessage
from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage
from config.index import CURRENT_ENV
from Agents.Master.master import create_agent
from Prompts.prompt import prompt as base_prompt
from tools.package_showing_tool import PackageRequest

def lambda_handler(event, context):
    print("sell lambda event",event)

    response = ""
    history =  []
    
    # Check if the event is from API Gateway
    if "requestContext" in event:
        # Event from API Gateway
        lambda_source = "API Gateway"
        print("Event from API Gateway")
        history= json.loads(event["body"])
    else:
        # Event from another source (like WhatsApp)
        lambda_source = "whatsapp"
        print("Event from whatsapp")
        history= event

    # Extract env and user_role from the request
    env = history.get("env", "DEV")
    user_role = history.get("user_role", "User")

    print(f"User role: {user_role}")
    print(f"Environment: {env}")

    # Added lines to set the prompt and create the agent
    final_prompt = base_prompt.format(env=env, user_role=user_role)
    print(f"\n\nFinal Prompt: {final_prompt}\n\n")

    master_agent_executor = create_agent(final_prompt)

    try:
        if CURRENT_ENV == "LOCAL":
            print("line no 44",history['messages'])
            config = {"configurable": {"thread_id": "test-thread"}}
            response = master_agent_executor.invoke(
                {
                    "messages": [("human", history['messages'])],
                    "tool_input": PackageRequest(env=env, user_role=user_role).dict()
                },
                config,
            )
        else:
            print("line no 55",history['messages'])
            messages = []
            for message in history['messages']:
                if message['role'] == 'user':
                    messages.append(HumanMessage(content=message['content']))
                else:
                    messages.append(AIMessage(content=message['content']))

            response = master_agent_executor.invoke(
                    {
                        "messages": messages,
                        "tool_input": PackageRequest(env=env, user_role=user_role).dict()
                    },
            )
    except Exception as error: 
        print("error in response",error)

    print("response",response)
    type= ""
    data= ""
    intent= ""
    
    #Capturing car details
    if isinstance(response["messages"][-2], ToolMessage) and response["messages"][-2].name == 'user_input_tool':
        print(json.loads(response["messages"][-2].content))
        type="car_upload"
        data= json.loads(response['messages'][-2].content)
        intent="selling"
    
    #Capturing booster details 
    if isinstance(response["messages"][-2], ToolMessage) and response["messages"][-2].name == 'package_showing_tool':
        type="car_upgrade_showing"
        data= json.loads(response['messages'][-2].content)
        
    #Capturing booster details 
    if isinstance(response["messages"][-2], ToolMessage) and response["messages"][-2].name == 'package_selection_tool':
        type="car_upgrade"
        data= json.loads(response['messages'][-2].content)


    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": response['messages'][-1].content,
            "type":type,
            "data":data,
            "intent":intent,
        }),
    }
