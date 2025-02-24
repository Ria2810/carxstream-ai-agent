from langchain_openai import ChatOpenAI
from config.index import OPENAI_API_KEY,AI_MODEL

def remove_car_tool(context):
    """
    Tool for handling the 'remove car' functionality using the chat history in 'messages'.
    """
    # Ensure 'messages' exists in the context and is valid
    if "messages" not in context or not isinstance(context["messages"], list):
        raise ValueError("'messages' key is missing or not a valid list in the context.")

    # Deserialize messages for processing (assume already serialized in master_agent)
    serialized_messages = context["messages"]

    # Construct the AI prompt
    REMOVE_CAR_PROMPT = """
    You are an AI agent designed to assist users with removing cars from their records.

    Your responsibilities:
    1. Always start by asking the user to provide the number plate of the car they want to remove, even if there is prior history.
    2. If the user provides a number plate, confirm whether they want to proceed with deleting that car.
    3. If the user confirms deletion, respond like this:
       "Alright, the car with the number plate <vehicle_number> has been successfully removed."
    4. If the user cancels (says "no"), respond like this:
       "The deletion process has been canceled."
    5. Include no additional JSON in your response.

    Rules:
    - Never prefix responses with "AI:" or other labels.
    - Always guide the user through a clear and logical sequence.
    - Provide concise and user-friendly responses.

    Chat History:
    """
    for msg in serialized_messages:
        role = "User" if msg["role"] == "user" else "Assistant"
        REMOVE_CAR_PROMPT += f"{role}: {msg['content']}\n"

    # Invoke the AI model
    model = ChatOpenAI(temperature=0, model=AI_MODEL, openai_api_key=OPENAI_API_KEY)
    ai_response = model.invoke(REMOVE_CAR_PROMPT).content.strip()

    # Append the AI response to the serialized messages
    serialized_messages.append({"role": "assistant", "content": ai_response})

    # Parse the vehicle number and response type from the AI's response
    vehicle_number = None
    type_flag = None

    if "successfully removed" in ai_response.lower():
        type_flag = "delete_car"
        start = ai_response.find("number plate") + len("number plate")
        end = ai_response.find("has been successfully removed")
        vehicle_number = ai_response[start:end].strip()
    elif "canceled" in ai_response.lower():
        type_flag = "cancel"

    # Return the structured response
    return {
        "message": ai_response,
        "type": type_flag,
        "vehicle_number": vehicle_number,
    }
