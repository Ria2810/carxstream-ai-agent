from langchain_openai import ChatOpenAI
from config.index import OPENAI_API_KEY,AI_IMAGE_MODEL
from utils.add_car import get_user_cars
from langchain.schema import HumanMessage, AIMessage


def format_chat_history(chat_history):
    """
    Formats raw chat history for use in prompt generation.
    """
    formatted_messages = []
    for message in chat_history:
        if message["role"] == "user":
            formatted_messages.append(HumanMessage(content=message["content"]))
        else:
            formatted_messages.append(AIMessage(content=message["content"]))
    return formatted_messages

def get_last_user_message(formatted_chat_history):
    """
    Retrieve the most recent valid user message from the chat history.
    If no user message is found, raise a ValueError.
    """
    for message in reversed(formatted_chat_history):  # Iterate in reverse order
        if isinstance(message, HumanMessage):
            return message.content
    raise ValueError("No valid user query found in the chat history.")

def image_handler_tool(context):
    """
    Tool for handling the 'add images to a car' functionality using the chat history in 'messages'.
    """
    if "messages" not in context or not isinstance(context["messages"], list):
        raise ValueError("'messages' key is missing or not a valid list in the context.")

    # Deserialize messages for processing
    messages = context["messages"]
    phone_number = context.get("phone_number", "")

    # Fetch car details for the user
    cars = get_user_cars(phone_number)

    if cars is None:
        formatted_docs_str = "User has no cars listed. Prompt them to upload a car first."
    else:
        formatted_docs = []
        print("\nCars found.\n")
        for idx, car in enumerate(cars):
            attributes = car["attributes"]
            make = attributes["make"]
            car_model = attributes["model"]
            vin = car["vin"]

            formatted_docs.append(
                f"Make: {make}, Model: {car_model}, VIN Number: {vin}"
            )
        formatted_docs_str = " | ".join(formatted_docs)

    formatted_chat_history = format_chat_history(messages)

    user_message = get_last_user_message(formatted_chat_history)
    if user_message == "":
        user_message = "I have uploaded images"
    print(f"User Message: {user_message}")



    # Construct the AI prompt to ask user for selection or to confirm their selection
    IMAGE_HANDLER_PROMPT = f"""
You are an AI assistant that helps users with car-related queries.
Use the car information provided to answer the user's question.
The user will begin with uploading images saying and you should ask for confirmation **always** only in beginning whether they wish to add these images to any of the uploaded cars? Always ask for this confirmation whenever the user question is 'I have uploaded images'.
Only proceed if user says 'yes'. If user says 'no' then reply I can only help you with uploading images.
Your response must include:
1. A detailed answer to the user's query. Show information for all cars in the car information provided **always in a numbered list**. Display all the car details in a sentence form (do not mention first, second... in the sentences). Ask the user to select one car among the list.
2. After selecting the car, give response like 'successfully added' and show the car details of selected car.

Note: Once the user confirms yes/no do not ask again and again for confirmation.

Car information:
{formatted_docs_str}

Chat History:
{formatted_chat_history}

**User's Current question**: {user_message}

*Do not include phrases like "As an AI" in the response. Directly give the response without any prefix.*
*In the successfully added message DO NOT include any other lines like "Is there anything else you would like to do".* 
Based on the outlined process and the provided user input, determine the appropriate response and proceed accordingly.
"""

    

    # Invoke the AI model to generate the response
    model = ChatOpenAI(temperature=0, model=AI_IMAGE_MODEL, openai_api_key=OPENAI_API_KEY)
    ai_response = model.invoke(IMAGE_HANDLER_PROMPT).content.strip()

    print(f"\nResponse: {ai_response}\n")
    # Parse the car selection and response type
    selected_car = None
    type_flag = None
    data = {}
    tool = "image_handler_tool"

    if "successfully added" in ai_response.lower():
        print("\nSuccessful\n")
        type_flag = "image_upload"
        for car in cars:
            if car["vin"] in ai_response and car["attributes"]["make"].lower() in ai_response.lower() and car["attributes"]["model"].lower() in ai_response.lower():
                selected_car = car
                break
        # ai_response=f"Images have been successfully added to your car: {selected_car['attributes']['make']} {selected_car['attributes']['model']} ({selected_car['attributes']['year']}) - VIN: {selected_car['vin']}."
        data = selected_car

    elif "choose a valid option" in ai_response.lower() or "please select" in ai_response.lower() or "select" in ai_response.lower():
        type_flag = "car_selection_error"
        data = cars

    # Return the final response
    return {
        "message": ai_response,
        "type": type_flag,
        "selected_car": selected_car,
        "data": data,
        "tool": tool
    }

