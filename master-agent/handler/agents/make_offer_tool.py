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


def build_make_offer_prompt(user_input, car_details, vin_id, recent_history):
    prompt = f"""
This is the current action: MAKE OFFER
Below is the last five messages from the conversation for context. Understand the context and then proceed accordingly:
{recent_history}

Proceed according to user input:
User Input: {user_input}

**Important: Use NO prefix like "AI:", "AI response:" in the response.**

- Always start with this question first: "You asked to make an offer on: {car_details}.\
  Do you wish to negotiate a price or ask some questions? You can ask questions about RC docs, outstanding loans, insurance, etc."
**Do not ask this question again and again. If it has been already asked before then move on to the next step.**

- If the user wants suggestions for questions to ask the seller, provide the listed examples.
- If the user wants to negotiate a price, ask him for a price.

**DO NOT answer the user asked question by yourself. Only take the question as input and respond this: "I will now connect you to the seller."**
- Only **after user provides detail for the asked question**, either price or a question, give this response:
    "I will now connect you to the seller"

    
**Strictly follow this format**:
Response:
SOURCES: CarXstream
VIN: {vin_id}
SHORTLISTED FLAG: no
WISHLIST FLAG: no
CONNECT FLAG: no
MAKE_OFFER FLAG: yes
**Send JSON in the end ONLY AFTER USER PROVIDES ALL DETAILS.**
JSON: (If user asked a question put price as empty "", and if user sets a price put question as empty "". Price should be a number format string)
  {{"question":"<user question>","vin":"{vin_id}","price":"<user price>","message":"","type":"car_offer"}}
"""
    return prompt



def make_offer_tool(user_input, car_id, chat_history):
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
    prompt = build_make_offer_prompt(user_input, car_details, selected_car_vin, recent_history=" | ".join([
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
            "AI request": final_payload.get("AI request", ""),
            "price": final_payload.get("price", ""),
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
            "AI request": "",
            "price":"",
            "vin": "",
            "type": ""
        }