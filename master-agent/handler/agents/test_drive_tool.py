from langchain_openai import ChatOpenAI
from config.index import OPENAI_API_KEY,AI_IMAGE_MODEL
from langchain.schema import HumanMessage, AIMessage
from utils.add_car import get_car_by_id
import re
import json


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


def extract_final_json(response):
    """
    Extract the JSON part from the action response.
    """
    try:
        # Use regex to find the JSON at the end of the response
        json_match = re.search(r'(\{.*\})$', response, re.DOTALL)
        if json_match:
            json_data = json_match.group(1)
            # Parse and return the JSON
            return json.loads(json_data)
    except Exception as e:
        print(f"Error extracting JSON: {e}")
    return False


def build_test_drive_prompt(user_input, car_details, vin_id, recent_history):
    prompt = f"""
This is the current action: SCHEDULE TEST DRIVE
Below is the last five messages from the conversation for context. Understand the context and then proceed accordingly:
{recent_history}

Proceed according to user input:
User Input: {user_input}

**Important: Use NO prefix like "AI:", "AI response:" in the response.**

- Always start with this question first: "You asked to schedule a test drive for {car_details}.\
  Please provide your location, date, and time (location should be within 5km of the car location)."
**Do not ask this question again and again. If it has been already asked before then move on to the next step.**

- Make sure all the three inputs are given by user: location, date, and time. If any one of them is missing, ask the user to provide with that detail.

- Only **after user provides details for the asked question**, give this response:
  "I have scheduled the test drive on {{date}} at {{time}} in {{location}}."
  
**Strictly follow this format**:
Response:
SOURCES: CarXstream
VIN: {vin_id}
SHORTLISTED FLAG: no
WISHLIST FLAG: no
CONNECT FLAG: no
MAKE_OFFER FLAG: no
**Send JSON in the end ONLY AFTER USER PROVIDES ALL DETAILS.**
JSON:
  {{"area": "", "vin": "{vin_id}", "location":"<user location>", "date":"<user date>", "time":"<user time>", "type":"test_drive_home"}}
"""
    return prompt



def test_drive_tool(user_input, car_id, chat_history):
    """
    Tool for handling the 'make an offer on a car' functionality using the chat history in 'messages'.
    """
    formatted_chat_history = format_chat_history(chat_history)
    car_details = "Use previous car details"
    selected_car_vin = "Use previous car vin selected"

    if car_id:
        selected_doc = get_car_by_id(car_id)
        car_details = f"{selected_doc["attributes"]["make"]} {selected_doc["attributes"]["model"]} {selected_doc["attributes"]["year"]} vin: {selected_doc["vin"]}"
        selected_car_vin = selected_doc['vin']
        print(f"\nCar Details: {car_details}\n")
    recent_history=" | ".join([
                            f"User: {msg.content}" if isinstance(msg, HumanMessage) else f"AI: {msg.content}"
                            for msg in formatted_chat_history[-4:]
                        ])
    print(f"\nRecent history: {recent_history}\n")
    model = ChatOpenAI(temperature=0, model=AI_IMAGE_MODEL, openai_api_key=OPENAI_API_KEY)
    prompt = build_test_drive_prompt(user_input, car_details, selected_car_vin, recent_history=" | ".join([
                            f"User: {msg.content}" if isinstance(msg, HumanMessage) else f"AI: {msg.content}"
                            for msg in formatted_chat_history[-4:]
                        ]))
    ai_response = model.invoke(prompt).content.strip()
    final_payload = extract_final_json(ai_response)

    if final_payload:
        if "Response" in ai_response:
            stripped_action_response = re.split(r"\s*Response\s*", ai_response, maxsplit=1)[0].strip()
        elif "SOURCES" in ai_response:
                stripped_action_response = re.split(r"\s*SOURCES\s*", ai_response, maxsplit=1)[0].strip()
        else:
            stripped_action_response = re.split(r"\s*JSON\s*", ai_response, maxsplit=1)[0].strip()

        return {
            "message": stripped_action_response,
            "location": final_payload.get("location", ""),
            "date": final_payload.get("date", ""),
            "time": final_payload.get("time", ""),
            "vin": final_payload.get("vin", ""),
            "type": final_payload.get("type", "")
        }
    else:
        if "Response" in ai_response:
            stripped_action_response = re.split(r"\s*Response\s*", ai_response, maxsplit=1)[0].strip()
        elif "SOURCES" in ai_response:
                stripped_action_response = re.split(r"\s*SOURCES\s*", ai_response, maxsplit=1)[0].strip()
        else:
            stripped_action_response = re.split(r"\s*JSON\s*", ai_response, maxsplit=1)[0].strip()

        return {
            "message": stripped_action_response,
            "location": "",
            "date":"",
            "time":"",
            "vin": "",
            "type": ""
        }