from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from utils.add_car import get_car_by_id, get_car_by_vin
from agents.sell_tool import sell_tool
from agents.buy_tool import buy_tool
from agents.remove_car_tool import remove_car_tool
from agents.image_handler_tool import image_handler_tool
from agents.make_offer_tool import make_offer_tool
from agents.test_drive_tool import test_drive_tool
from agents.car_loan_tool import car_loan_tool
from agents.customer_service_tool import customer_service_tool, is_confused_response_openai
from Prompt.prompt import prompt
from config.index import OPENAI_API_KEY,AI_MODEL
import json
import re

def extract_vin(input_text):
    """
    Extracts the first VIN from the input text.
    Handles various VIN formats like GJ 76 GY 2877, GJ76GY2877, GJ76 GY2877, etc.
    
    Args:
        input_text (str): The input string containing a VIN.
    
    Returns:
        str: The extracted VIN or None if no VIN is found.
    """
    # Regular expression for matching VIN formats with or without spaces
    vin_pattern = r'\b([A-Z]{2}\s?\d{1,2}\s?[A-Z]{1,2}\s?\d{2,4})\b'

    # Search for the first VIN in the input text
    match = re.search(vin_pattern, input_text, re.IGNORECASE)

    # If a match is found, clean and return the VIN (remove spaces and convert to uppercase)
    if match:
        return re.sub(r'\s+', '', match.group(0)).upper()

    # If no match is found, return None
    return None


def validate_vin_format(vin):
    """
    Validates if the VIN matches the required format:
    - Two uppercase letters
    - Two digits
    - Two uppercase letters
    - Four digits

    Args:
        vin (str): The VIN to validate.

    Returns:
        bool: True if the VIN matches the required format, False otherwise.
    """
    # Regular expression for the strict VIN format
    vin_format_pattern = r'^[A-Z]{2}\d{2}[A-Z]{2}\d{4}$'

    return bool(re.fullmatch(vin_format_pattern, vin))


# Initialize the model
model = ChatOpenAI(temperature=0, model=AI_MODEL, openai_api_key=OPENAI_API_KEY)

# Define tools
tools = [sell_tool, buy_tool, image_handler_tool, remove_car_tool, customer_service_tool]

# Supervisor agent (master agent) creation
supervisor = create_react_agent(model=model, tools=tools)


def build_condense_question_prompt(question, chat_history, last_tool_context):
    """
    Constructs a concise prompt for condensing the user's question.
    Includes prior chat history and the context of the last tool invocation.
    """
    formatted_chat_history = " | ".join([
        f"User: {message['content']}" if message["role"] == "user" else f"AI: {message['content']}"
        for message in chat_history[-5:]  # Limit chat history to the last 5 messages
    ])
    last_tool_context_info = f"Last Tool Used: {last_tool_context['intent']}" if last_tool_context else "No previous tool used."
    prompt = f"""
You are a highly advanced AI specializing in assisting users with car-related queries.
Analyze the user's current question in the context of the chat history and any previously invoked tools.
**Always prioritize the user's current question.**
If the user query indicates switching the intent (e.g., explicitly mentions buying, selling, or another action unrelated to the last tool), update the intent accordingly and smoothly transition the conversation.
Make sure you understand the chat history and determine if the user is in the middle of an ongoing process such as selling, buying, or adding images, and detect the intent accordingly.

**IMPORTANT**: 
- **MAKE_OFFER INTENT, TEST_DRIVE INTENT OR CAR_LOAN INTENT SHOULD ONLY BE CONSIDERED IF THE LAST TOOL WAS MAKE_OFFER_TOOL, TEST_DRIVE_TOOL OR CAR_LOAN_TOOL RESPECTIVELY. IF NOT, THEN USE THE PREVIOUS TOOL ONLY.**
- **Do not infer 'make_offer', 'test_drive' or 'car_loan' intents under any circumstances unless the last tool used was `make_offer_tool`, `test_drive_tool` or 'car_loan_tool' respectively.**

Rules for detecting intent:
1. If the last tool used was the **sell_tool**, actions such as selecting "1" to upload images or "2" for packages should be treated as part of the selling process. Do not change the intent to 'image' unless the user explicitly switches to a new tool or mentions unrelated tasks.
2. If the last tool used was the **buy_tool**, and the current query indicates continuation (e.g., "show more," "add," "save", "shortlist"), continue using the 'buy_tool.' If the user query contains informal buying language (e.g., "give me," "show me," or a car name), direct it to the 'buy_tool' intent.
    - If the last tool used was **buy_tool**, and current query indicates make offer, test drive, visit seller, connect to seller or apply loan, continue using the 'buy_tool'.
3. If the last tool used was the **image_handler_tool**, and the user explicitly continues the image process (e.g., selecting a car, VIN, or providing ordinal information like "1st", or a yes/no), set the intent to 'image.' 
   - **Important**: Only infer 'image intent' if the last tool was `image_handler_tool`. For **image intent**, use this format only: **Intent:Image** with no additional explanation.
4. **If and only if** the last tool used was the **make_offer_tool**, and the user explicitly continues the make offer process (e.g., setting a price, or asking any question), set the intent to 'make_offer.' 
   - **Important**: **Only infer 'make_offer intent' if the last tool was `make_offer_tool`. For **make_offer intent**, use this format only: **Intent: make_offer** with no additional explanation.
5. **If and only if** the last tool used was the **test_drive_tool**, and the user explicitly continues the test_drive process (e.g., giving location, date or time), set the intent to 'test_drive.' 
   - **Important**: **Only infer 'test_drive intent' if the last tool was `test_drive_tool`. For **test_drive intent**, use this format only: **Intent: test_drive** with no additional explanation.
6. **If and only if** the last tool used was the **car_loan_tool**, and the user explicitly continues the car_loan process (e.g., giving amount), set the intent to 'car_loan.' 
   - **Important**: **Only infer 'car_loan intent' if the last tool was `car_loan_tool`. For **car_loan intent**, use this format only: **Intent: car_loan** with no additional explanation.
7. If the user query mentions removing or deleting a car (e.g., "remove car," "delete my car"), extract the intent as 'delete_car.'
8. If the user query mentions contacting customer service (e.g., "customer service," "contact support,"), extract the intent as 'customer_service'.
9. If no context is clear, analyze the chat history and current question to infer intent explicitly.
10. If the user provides yes/no replies, base intent detection on the chat history and the last tool context. Ensure these responses respect the ongoing context unless the user query explicitly indicates an intent switch.


Important Notes:
- Only infer **image intent** if the last tool was `image_handler_tool` and the current query is a continuation of the image process. Otherwise, stick to the current tool's process.
- Only infer **make_offer intent** if the last tool was `make_offer_tool` and the current query is a continuation of the make_offer process. Otherwise, stick to the current tool's process.
- Only infer **test_drive intent** if the last tool was `test_drive_tool` and the current query is a continuation of the test_drive process. Otherwise, stick to the current tool's process.
- Only infer **car_loan intent** if the last tool was `car_loan_tool` and the current query is a continuation of the car_loan process. Otherwise, stick to the current tool's process.
- When the last tool was `sell_tool`, uploading images or similar actions must be part of the selling flow.
- When the last tool was `buy_tool`, actions like make an offer, connect to the seller and test drive actions must be part of the buy flow.
- Always prioritize the **current question** over chat history when detecting intent.

Chat History: {formatted_chat_history}
Last tool: {last_tool_context_info}
Current Question: {question}

**Strict Format of response:**
Intent: sell/buy/image/delete_car/customer_service/make_offer/test_drive/car_loan
"""

    return prompt



def master_agent(messages, phone_number, user_role, env, session_data=None):
    """
    Master agent to process the user message, determine intent, and invoke the appropriate tool.
    """
    # Ensure session_data is initialized as a dictionary
    if session_data is None:
        session_data = {}
    print("\nline 67\n")
    latest_message = messages[-1]
    latest_user_message = latest_message["content"]

    last_tool_context = {}
    if len(messages) > 1:
        last_tool_context = messages[-2]
        print("last_tool_context: ", last_tool_context)
        print(f"\nlast_tool: {last_tool_context['intent']}\n")
    else:
        last_tool_context['intent'] = 'None'

    print(f"\nline 71 - {latest_message}\n")
    # Handle media-type messages using image_handler_tool
    if latest_message.get("type") == "media" or latest_message.get("messageType") == "media":
        print("Invoking image_handler_tool")
        tool_response = image_handler_tool({"messages": messages, "phone_number": phone_number, "session_data": session_data})
        return {
            "message": tool_response.get("message", ""),
            "source": None,
            "data": tool_response.get("data", {}) or {},
            "intent": "image_handler_tool",
            "type": tool_response.get("type", ""),
        }
    
    elif latest_message.get("action_type") == "make_offer":
        print("Invoking make_offer")
        print(f"\nLastest message: {latest_message}\n")
        car_id = latest_message["car_id"]
        print(f"\nCar iD: {car_id}\n")
        tool_response = make_offer_tool("make an offer",car_id, messages)
        return {
            "message": tool_response.get("message", ""),
            "AI request": tool_response.get("AI request", ""),
            "price": tool_response.get("price", ""),
            "vin": tool_response.get("vin", ""),
            "type": tool_response.get("type", ""),
            "intent": "make_offer_tool"
        }
    
    elif latest_message.get("action_type") == "test_drive":
        print("Invoking test drive")
        print(f"\nLastest message: {latest_message}\n")
        car_id = latest_message["car_id"]
        print(f"\nCar iD: {car_id}\n")
        tool_response = test_drive_tool("schedule test drive",car_id, messages)
        return {
            "message": tool_response.get("message", ""),
            "location": tool_response.get("location", ""),
            "date": tool_response.get("date", ""),
            "time": tool_response.get("time", ""),
            "vin": tool_response.get("vin", ""),
            "type": tool_response.get("type", ""),
            "intent": "test_drive_tool"
        }
    
    elif latest_message.get("action_type") == "car_loan":
        print("Invoking  car loan")
        print(f"\nLastest message: {latest_message}\n")
        car_id = latest_message["car_id"]
        print(f"\nCar iD: {car_id}\n")
        tool_response = car_loan_tool("apply loan",car_id, messages)
        return {
            "message": tool_response.get("message", ""),
            "amount": tool_response.get("amount",""),
            "type": tool_response.get("type", ""),
            "intent": "car_loan_tool"
        }

    elif latest_message.get("action_type") == "connect_seller" or (any(term in latest_user_message.lower() for term in ["connect to the seller", "connect to seller", "connect seller"]) and (extract_vin(latest_user_message) is not None)):
        print("Invoking connect_seller")
        if latest_message.get("action_type") == "connect_seller":
            car_id = latest_message.get("car_id", '')
            selected_doc = get_car_by_id(car_id)
            car_details = f"{selected_doc["attributes"]["make"]} {selected_doc["attributes"]["model"]}, {selected_doc["attributes"]["year"]} (VIN: {selected_doc["vin"]})"
            return {
                "message": f"Sure! I will now connect you to the seller of {car_details}.",
                "source": None,
                "car_id": car_id,
                "intent": "connect_seller",
                "type": "connect_seller"
            }
        else:
            vin = extract_vin(latest_user_message)
            print(f"\n\nVin: {vin}\n\n")
            if vin is not None and validate_vin_format(vin):
                car_id = get_car_by_vin(vin)
                return {
                "message": f"Sure! I will now connect you to the seller of {vin}.",
                "source": None,
                "car_id": car_id,
                "intent": "connect_seller",
                "type": "connect_seller"
                }
            else:
                return {
                    "message": "Please provide a valid VIN.",
                    "source": None,
                    "intent": "connect_seller",
                }

    
    # Format the messages for the supervisor
    formatted_messages = [
        HumanMessage(content=message["content"]) if message["role"] == "user" else AIMessage(content=message["content"])
        for message in messages
    ]
    
    # Serialize messages
    serialized_messages = [
        {"role": "user" if isinstance(message, HumanMessage) else "assistant", "content": message["content"]}
        for message in messages
    ]

    # Extract latest user question
    latest_question = latest_message["content"]
    
    # Check if the user explicitly requests customer service
    if "customer service" in latest_question.lower() or "contact support" in latest_question.lower():
        return {
            "message": "Sure, I will now connect you to our customer service.",
            "type": "customer_service",
            "intent": "customer_service",
        }

    print("\nline 95\n")
    # Get the last tool context
    last_tool_context = {}
    if len(messages) > 1:
        last_tool_context = messages[-2]
        print("last_tool_context: ", last_tool_context)
        print(f"\nlast_tool: {last_tool_context['intent']}\n")

    
    print("\nline 113\n")
    # Condense question for intent detection
    condense_prompt = build_condense_question_prompt(latest_question, messages, last_tool_context)
    condensed_question = model.invoke(condense_prompt).content.strip()
    print(f"Condensed Question: {condensed_question}")


    # Determine intent dynamically using the condensed question
    tool_response = None
    intent = None
    
    if "sell" in condensed_question.lower() or "upload" in condensed_question.lower():
        print("Condensed question indicates a 'sell' intent. Invoking sell_tool.")
        session_data["last_tool"] = {"tool_name": "sell_tool"}
        tool_response = sell_tool({"messages": formatted_messages, "user_role": user_role, "env": env})
        intent = "sell_tool"
    elif "buy" in condensed_question.lower() or ("make_offer" in condensed_question.lower() and last_tool_context['intent'] != "make_offer_tool") or ("test_drive" in condensed_question.lower() and last_tool_context['intent'] != "test_drive_tool") or ("car_loan" in condensed_question.lower() and last_tool_context['intent'] != "car_loan_tool"):
        print("Condensed question indicates a 'buy' intent. Invoking buy_tool.")
        session_data["last_tool"] = {"tool_name": "buy_tool"}
        intent = "buy_tool"
        tool_response = buy_tool({"messages": formatted_messages, "phone_number": phone_number})
        
    elif "delete_car" in condensed_question.lower() or any(term in condensed_question.lower() for term in ["remove car", "delete car", "delete", "remove"]):
        print("Detected 'remove car' intent. Invoking remove_car_tool.")
        session_data["in"] = {"tool_name": "remove_car_tool"}
        tool_response = remove_car_tool({"messages": serialized_messages})
        intent = "remove_car_tool"
    elif "image" in condensed_question.lower():
        print("Image handler Invokes")
        session_data["intent"] = {"tool_name": "image_handler_tool"}
        tool_response = image_handler_tool({"messages": messages, "phone_number": phone_number, "session_data": session_data})
        intent = "image_handler_tool"
    elif "customer_service" in condensed_question.lower():
        print("Customer Service handler Invokes")
        session_data["intent"] = {"tool_name": "customer_service_tool"}
        tool_response = customer_service_tool({"messages": formatted_messages, "tool_response": last_tool_context["content"], "user_message": latest_user_message})
        intent = "customer_service_tool"
    elif "make_offer" in condensed_question.lower() and last_tool_context['intent'] == "make_offer_tool":
        print("Make Offer handler Invokes")
        session_data["intent"] = {"tool_name": "make_offer"}
        car_id = ''
        tool_response = make_offer_tool(latest_question, car_id, messages)
        intent = "make_offer_tool"
    elif "test_drive" in condensed_question.lower() and last_tool_context['intent'] == "test_drive_tool":
        print("Test Drive handler Invokes")
        session_data["intent"] = {"tool_name": "make_offer"}
        car_id = ''
        tool_response = test_drive_tool(latest_question, car_id, messages)
        intent = "test_drive_tool"
    elif "car_loan" in condensed_question.lower() and last_tool_context['intent'] == "car_loan_tool":
        print("Loan handler Invokes")
        session_data["intent"] = {"tool_name": "car_loan"}
        car_id = ''
        tool_response = car_loan_tool(latest_question, car_id, messages)
        intent = "car_loan_tool"

    if tool_response:
        return {
            "message": tool_response.get("message", ""),
            "source": None,
            "data": tool_response.get("data", {}) or {},
            "URL": tool_response.get("url", ""),
            "intent": intent,
            "vehicle_number": tool_response.get("vehicle_number",""),
            "question": tool_response.get('question',''),
            "vin": tool_response.get('vin',''),
            "price": tool_response.get('price',''),
            "area": tool_response.get('area',''),
            "location": tool_response.get('location',''),
            "date": tool_response.get('date',''),
            "time": tool_response.get('time',''),
            "amount": tool_response.get('amount',''),
            "type": tool_response.get("type", "")
        }

    # Default fallback response
    return {
        "message": "I couldn't determine the intent clearly. Are you looking for selling or buying a car?",
        "source": None,
        "data": {},
        "URL": "",
        "intent": "",
    }
