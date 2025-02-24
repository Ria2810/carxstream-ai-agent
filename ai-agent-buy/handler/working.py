import re
import json
from utils.elastic import elasticsearch_client, store
from config.Constants import ES_INDEX,CURRENT_ENV,PROD_URL,DEV_URL
from utils.openAI import get_llm
from utils.prompts import (build_condense_question_prompt, build_qa_prompt, 
                            build_make_offer_prompt, build_test_drive_prompt,
                           build_visit_seller_prompt, build_verification_prompt, build_loan_prompt)
from utils.getCount import get_total_count,get_count_by_query
from langchain.schema import HumanMessage, AIMessage

pagination_states = {}
total_count = get_total_count()
ACTION_PROMPTS = {
    "make_offer": build_make_offer_prompt,
    "test_drive": build_test_drive_prompt,
    "visit_seller": build_visit_seller_prompt,
    "verify_user": build_verification_prompt,
    "loan": build_loan_prompt,
    # add "connect_seller" if needed, etc.
}

def retrieve_docs_by_car_ids(car_ids):
    """
    Perform a fallback search using _mget for CAR IDs and retrieve only the car_id.
    """
    try:
        if not car_ids:
            return []
        
        payload = {
            "docs": [{"_index": ES_INDEX, "_id": car_id, "_source": ["car_id", "year", "make", "model", "trim", "price", "bidsEnabled", "bidsStartingPrice", "vin", "image", "visible", "sold", "locationData","location"]} for car_id in car_ids]
        }

        response = elasticsearch_client.mget(body=payload)

        transformed_array = [
            {
                **element["_source"],  # Unpack the keys and values from _source
                "url": (
                    f"{DEV_URL if CURRENT_ENV == 'dev' else PROD_URL}products/buy/"
                    f"{element['_source'].get('year', 'Unknown')}-"
                    f"{element['_source'].get('make', 'Unknown')}-"
                    f"{element['_source'].get('model', 'Unknown')}-"
                    f"{element['_source'].get('locationData', {}).get('city', 'Unknown')}-"
                    f"{element['_source'].get('locationData', {}).get('state', 'Unknown')}-"
                    f"{element['_source'].get('locationData', {}).get('zipCode', 'Unknown')}-"
                    f"{element['_source'].get('location', {})}-"
                    f"{element['_source'].get('car_id', 'Unknown')}"
                ),
                "bidsEnabled": element['_source'].get('bidsEnabled') if element['_source'].get('bidsEnabled') is not None else False
            }
            for element in response['docs']
            if "_source" in element  # Only process elements that have "_source"
        ]

        return transformed_array

    except Exception as e:
        print(f"Error during fallback search: {e}")
        return []


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


def retrieve_docs_with_store(condensed_question, session_id, batch_size=10, is_new_query=False):
    """
    Retrieve documents using store.as_retriever with proper pagination.
    Ensures each batch contains exactly `batch_size` documents where `sold: false` and `visible: true`.
    """
    print("USER ID: ", session_id)

    if session_id not in pagination_states or is_new_query:
        # Reset state for new queries
        pagination_states[session_id] = {"from": 0, "docs": [], "last_docs": []}

    state = pagination_states[session_id]

    # Fetch documents only once for the given query and cache them
    if is_new_query or not state["docs"]:
        retriever = store.as_retriever(search_kwargs={"k": 100})
        all_docs = retriever.get_relevant_documents(condensed_question)

        # Filter unique documents by 'car_id' and conditions `sold: false` and `visible: true`
        seen_ids = set()
        state["docs"] = [
            doc for doc in all_docs
            if doc.metadata.get("car_id") not in seen_ids
            and not seen_ids.add(doc.metadata.get("car_id"))
        ]
        # print(f"\n\n\nState docs: {state["docs"]}\n\n\n")
        state["docs"].sort(key=lambda doc: len(doc.metadata.get("badges", []) or []), reverse=True)

    # Fetch the next batch for "show more" queries
    batch = []
    while len(batch) < batch_size and state["from"] < len(state["docs"]):
        # Retrieve more documents from cached docs
        doc = state["docs"][state["from"]]
        state["from"] += 1  # Increment the index

        # Extract metadata and check flags
        source = doc.metadata
        sold = source.get("sold", True)  # Default to True to exclude if not explicitly false
        visible = source.get("visible", False)  # Default to False to exclude if not explicitly true

        if not sold and visible:
            batch.append(doc)

    # If batch size is not met, fetch additional data dynamically
    if len(batch) < batch_size:
        retriever = store.as_retriever(search_kwargs={"k": 100})
        additional_docs = retriever.get_relevant_documents(condensed_question)

        # Filter unique and valid additional documents
        seen_ids = {doc.metadata.get("car_id") for doc in state["docs"]}
        additional_docs = [
            doc for doc in additional_docs
            if doc.metadata.get("car_id") not in seen_ids
            and not seen_ids.add(doc.metadata.get("car_id"))
            and not doc.metadata.get("sold", True)  # Default to True to exclude if not explicitly false
            and doc.metadata.get("visible", False)  # Default to False to exclude if not explicitly true
        ]

        additional_docs.sort(key=lambda doc: len(doc.metadata.get("badges", []) or []), reverse=True)

        # Add the remaining documents to the batch until it reaches the required size
        batch.extend(additional_docs[:batch_size - len(batch)])

        # Cache the newly fetched documents
        state["docs"].extend(additional_docs)

    if batch:
        state["last_docs"] = batch  # Cache the current batch as the last shown results
    else:
        print("No more valid records to fetch.")

    return batch, len(batch), len(state["docs"])


def detect_user_intent(condensed_question, state):
    """
    Dynamically detects user intent based on the condensed question and session state.
    Determines whether the query is a refinement, a request for more results, or a new query.
    """
    # Check for "show more" or similar phrases
    if "show more" in condensed_question.lower() or "more results" in condensed_question.lower():
        return "show_more"

    # If there are no previously shown documents, treat as a new query
    if not state["last_docs"]:
        return "new_query"

    # Extract previously shown makes or models for comparison
    shown_attributes = extract_shown_attributes(state["last_docs"])

    # Check if the new query mentions something unrelated to the current dataset
    for token in condensed_question.lower().split():
        if token in shown_attributes:
            return "refinement"

    # If no match with current results, it's a new query
    return "new_query"



def extract_shown_attributes(docs):
    """
    Extracts attributes (e.g., make, model, color) from the last shown documents
    for use in refinement detection.
    """
    attributes = set()
    for doc in docs:
        metadata = doc.metadata
        attributes.update(str(value).lower() for key, value in metadata.items() if isinstance(value, str) and value)
    return attributes



def process_response(answer, session_id):
    """
    Processes the response from the QA system, extracting car IDs, shortlist, and wishlist flags.
    """
    try:
        # Extract car IDs
        car_ids = []
        car_ids_match = re.search(r"CAR IDS:\s*([\s\S]*?)(?=SHORTLISTED FLAG:|WISHLIST FLAG:)", answer)

        if car_ids_match:
            car_ids_section = car_ids_match.group(1).strip()
            car_ids = [car_id.strip() for car_id in car_ids_section.split(",")]
        else:
            car_ids = re.findall(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", answer)

        print("Extracted Car IDs:", car_ids)

        # Fetch matching documents
        matching_docs = retrieve_docs_by_car_ids(car_ids)
        print("\nMatching Car Documents Based on CAR IDS:")
        for doc in matching_docs:
            print(doc)

        # Extract shortlist and wishlist flags
        shortlist_flag, wishlist_flag,connect_flag = extract_flags(answer)
        print(f"Shortlist Flag: {shortlist_flag}")
        print(f"Wishlist Flag: {wishlist_flag}")
        print(f"Connect Flag: {connect_flag}")

        return matching_docs,car_ids,shortlist_flag, wishlist_flag, connect_flag

    except Exception as e:
        print(f"Error processing response: {e}")
        return [], "No", "No", "No"


def extract_flags(answer):
    """
    Extracts shortlist and wishlist flags from the AI response.
    """
    try:
        shortlist_flag_match = re.search(r"SHORTLISTED FLAG:\s*(Yes|No)", answer, re.IGNORECASE)
        wishlist_flag_match = re.search(r"WISHLIST FLAG:\s*(Yes|No)", answer, re.IGNORECASE)
        connect_flag_match = re.search(r"CONNECT FLAG:\s*(Yes|No)", answer, re.IGNORECASE)

        shortlist_flag = shortlist_flag_match.group(1).strip() if shortlist_flag_match else "No"
        wishlist_flag = wishlist_flag_match.group(1).strip() if wishlist_flag_match else "No"
        connect_flag = connect_flag_match.group(1).strip() if connect_flag_match else "No"

        return shortlist_flag, wishlist_flag, connect_flag
    except Exception as e:
        print("Error extracting flags:", e)
        return "No", "No"
    

def get_last_user_message(formatted_chat_history):
    """
    Retrieve the most recent valid user message from the chat history.
    If no user message is found, raise a ValueError.
    """
    for message in reversed(formatted_chat_history):  # Iterate in reverse order
        if isinstance(message, HumanMessage):
            return message.content
    raise ValueError("No valid user query found in the chat history.")


def is_action_completed(response):
    """
    Check if the action is completed.
    For example, we might say if the response contains a final JSON payload with "current_action":"none" or "action_status":"completed".
    Adjust logic based on your final JSON.
    """
    json_match = re.search(r'(\{.*?\})\s*$', response, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            # If current_action is none or action_status is completed means done
            if data.get("current_action","none") == "none" or data.get("action_status") == "completed":
                return True
        except:
            pass
    return False

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


def get_last_action(chat_history):
    """
    Retrieves the last action from the chat history.
    Returns the action name if found, else None.
    """
    # Define a mapping from user phrases to action types
    action_mapping = {
        "make an offer": "make_offer",
        "make offer": "make_offer",
        "offer": "make_offer",
        "test drive": "test_drive",
        "schedule test drive": "test_drive",
        "visit seller": "visit_seller",
        "verify user identity": "verify_user",
        "loan": "loan"
    }
    
    # Traverse the chat history in reverse to find the last action
    for message in reversed(chat_history):  # Iterate in reverse order
        if isinstance(message, HumanMessage):
            user_content = message.content
            for phrase, action in action_mapping.items():
                if phrase in user_content.lower():
                    return action
    return None

def is_action_complete(last_ai_response):
    phrases = [
        'I will now connect you to the seller',
        'I have scheduled the test drive',
        'I have scheduled a visit at the seller location',
        'Your loan request for'
    ]
    # Convert the AI response to lowercase once for efficiency
    last_ai_response_lower = last_ai_response.lower()
    
    # Use any() to check if any phrase is in the response
    return any(phrase.lower() in last_ai_response_lower for phrase in phrases)


def handle_action(user_input, last_ai_response, chat_history):
    """
    Handle the current action based on the last AI response.
    """
    # Check if the last AI response contains a final JSON payload
    if is_action_complete(last_ai_response):
        return False, {}
    
    final_json = extract_final_json(last_ai_response)
    if final_json:
        # Action is completed
        return False, extract_final_json(last_ai_response)

    current_action = None
    vin_id = "Use previous vin only from conversation context"
    car_details = "Use previous car details only"

    # Detect action type based on known response patterns
    ai_response_lower = last_ai_response.lower()
    if ai_response_lower.startswith("you asked to make an offer on"):
        current_action = "make_offer"
    elif ai_response_lower.startswith("you asked to schedule a test drive for"):
        current_action = "test_drive"
    elif ai_response_lower.startswith("you asked to visit the seller location for"):
        current_action = "visit_seller"
    elif ai_response_lower.startswith("you asked to verify user identity"):
        current_action = "verify_user"
    elif ai_response_lower.startswith("you asked about a loan for"):
        current_action = "loan"
    else:
        # If no action type is detected, use the last action type
        current_action = get_last_action(chat_history)

    if current_action:
        # For actions that require car_id, extract it from user_input
        if current_action in ["make_offer", "test_drive", "visit_seller", "loan"]:

            if current_action in ACTION_PROMPTS and vin_id and car_details:
                # Call the corresponding action prompt function with required arguments
                action_prompt_func = ACTION_PROMPTS[current_action]
                if current_action == "make_offer":
                    prompt = action_prompt_func(car_details, vin_id, recent_history=" | ".join([
                        f"User: {msg.content}" if isinstance(msg, HumanMessage) else f"AI: {msg.content}"
                        for msg in chat_history[-5:]
                    ]))
                elif current_action == "test_drive":
                    prompt = action_prompt_func(car_details, vin_id, recent_history=" | ".join([
                        f"User: {msg.content}" if isinstance(msg, HumanMessage) else f"AI: {msg.content}"
                        for msg in chat_history[-5:]
                    ]))
                elif current_action == "visit_seller":
                    prompt = action_prompt_func(car_details, vin_id, recent_history=" | ".join([
                        f"User: {msg.content}" if isinstance(msg, HumanMessage) else f"AI: {msg.content}"
                        for msg in chat_history[-5:]
                    ]))
                elif current_action == "verify_user":
                    prompt = action_prompt_func(recent_history=" | ".join([
                        f"User: {msg.content}" if isinstance(msg, HumanMessage) else f"AI: {msg.content}"
                        for msg in chat_history[-5:]
                    ]))
                elif current_action == "loan":
                    prompt = action_prompt_func(car_details, vin_id, recent_history=" | ".join([
                        f"User: {msg.content}" if isinstance(msg, HumanMessage) else f"AI: {msg.content}"
                        for msg in chat_history[-5:]
                    ]))
                else:
                    print("Action Prompt Func: ", action_prompt_func)
                    prompt = action_prompt_func(car_details, vin_id, recent_history=" | ".join([
                        f"User: {msg.content}" if isinstance(msg, HumanMessage) else f"AI: {msg.content}"
                        for msg in chat_history[-5:]
                    ]))

                action_response = get_llm().invoke(prompt).content
                print("\n----------------------------------------------------")
                print(f"\nAction Response: {action_response}\n")
                print("----------------------------------------------------\n")

                # Check if action completed by looking for final JSON
                if is_action_completed(action_response):
                    final_payload = extract_final_json(action_response)
                    if "Response" in action_response:
                        stripped_action_response = re.split(r"\s*Response\s*", action_response, maxsplit=1)[0].strip()
                    elif "SOURCES" in action_response:
                            stripped_action_response = re.split(r"\s*SOURCES\s*", action_response, maxsplit=1)[0].strip()
                    else:
                        stripped_action_response = re.split(r"\s*JSON\s*", action_response, maxsplit=1)[0].strip()

                    payload = {
                            "message": stripped_action_response,
                            "docs": {},
                            "type": final_payload.get("type",""),
                            "question": final_payload.get("question",""),
                            "vin": final_payload.get("vin",""),
                            "price": final_payload.get("price",""),
                            "area": final_payload.get("area",""),
                            "location": final_payload.get("location",""),
                            "date": final_payload.get("date",""),
                            "time": final_payload.get("time",""),
                            "amount": final_payload.get("amount",""),
                        }
                    return True, payload
                else:
                    if "Response" in action_response:
                        stripped_action_response = re.split(r"\s*Response\s*", action_response, maxsplit=1)[0].strip()
                    elif "SOURCES" in action_response:
                            stripped_action_response = re.split(r"\s*SOURCES\s*", action_response, maxsplit=1)[0].strip()
                    else:
                        stripped_action_response = re.split(r"\s*JSON\s*", action_response, maxsplit=1)[0].strip()
                    # Action is still ongoing, return the action prompt response without JSON
                    return True, {
                        "message": stripped_action_response,
                        "docs": [],
                        "type": "",
                        "question": "",
                        "vin": "",
                        "price": "",
                        "area": "",
                        "location": "",
                        "date": "",
                        "time": "",
                        "amount": "",
                    }

    return False, {}


def detect_user_action_intent(user_input):
    """
    Detects user intent based on the condensed question.
    """
    if any(phrase in user_input.lower() for phrase in ["make an offer", "make offer", "offer"]):
        return "make_offer"
    elif any(phrase in user_input.lower() for phrase in ["test drive", "schedule test drive"]):
        return "test_drive"
    elif "visit seller" in user_input.lower():
        return "visit_seller"
    elif "verify user" in user_input.lower() or "verification" in user_input.lower():
        return "verify_user"
    elif "loan" in user_input.lower():
        return "loan"
    return None


def ask_question(chat_histories, session_id):
    """
    Extracts the last user query as the question from the chat history
    and uses the full chat history as context.
    """
    try:
        # Format the chat history
        
        # Format the chat history
        formatted_chat_history = format_chat_history(chat_histories)
        if not formatted_chat_history:
            raise ValueError("Chat history is empty.")

        # Get the last AI message if any
        last_ai_message = None
        for message in reversed(formatted_chat_history):
            if isinstance(message, AIMessage):
                last_ai_message = message
                break

        # Get the last user message
        last_user_message = None
        for message in reversed(formatted_chat_history):
            if isinstance(message, HumanMessage):
                last_user_message = message
                break
        

        if not last_user_message:
            raise ValueError("No user message found in the chat history.")

        user_input = last_user_message.content
        print("User message: ", user_input)
        # print("AI message: ", last_ai_message.content)

        # Handle ongoing action if any
        if last_ai_message:
            if detect_user_action_intent(user_input) is None:
                action_in_progress, action_result = handle_action(user_input, last_ai_message.content, formatted_chat_history)
                if action_in_progress:
                    # Action is ongoing and requires user input
                    return action_result
                # elif action_result:
                #     # Action has been completed with final payload
                #     return action_result

        condense_question_prompt = build_condense_question_prompt(user_input, formatted_chat_history)
        condensed_question = get_llm().invoke(condense_question_prompt).content.strip()

        print(f"\nCondensed Question: {condensed_question}\n")

        docs_count = get_count_by_query(condensed_question)
        state = pagination_states.get(session_id, {"last_docs": []})

        user_intent = detect_user_intent(condensed_question, state)
        print("\nUser Intent: {user_intent}\n")

        if user_intent == "show_more":
            docs_to_process, count, total = retrieve_docs_with_store(condensed_question, session_id, batch_size=10, is_new_query=False)
        elif user_intent == "refinement":
            if state["last_docs"]:
                docs_to_process = state["last_docs"]
                total = len(docs_to_process)
                count = len(docs_to_process)
            else:
                docs_to_process, count, total = retrieve_docs_with_store(condensed_question, session_id, batch_size=10, is_new_query=True)
        else:
            docs_to_process, count, total = retrieve_docs_with_store(condensed_question, session_id, batch_size=10, is_new_query=True)

        qa_prompt = build_qa_prompt(user_input, docs_to_process, formatted_chat_history, total_count, docs_count)
        answer = get_llm().invoke(qa_prompt).content

        temp = re.sub(r"^\s*Response:\s*", "", answer, flags=re.IGNORECASE).strip()
        stripped_answer = re.split(r"SOURCES", temp)[0].strip()
        print("\n\n--------------------------------------------")
        print(stripped_answer)
        print("--------------------------------------------\n\n")
        matching_docs, car_ids, shortlist_flag, wishlist_flag, connect_flag = process_response(answer, session_id)

        # Determine action triggers
        last_user_input = user_input.lower()

        user__action_intent = detect_user_action_intent(last_user_input)
        print(f"\nUser action intent: {user__action_intent}\n")
        # If user triggers an action
        type = ''
        if user__action_intent and user__action_intent in ACTION_PROMPTS:
            if len(car_ids) == 1:
                selected_car_id = car_ids[0]
                selected_docs = retrieve_docs_by_car_ids([selected_car_id])
                selected_doc = selected_docs[0] if selected_docs else None
                if selected_doc:
                    car_details = f"{selected_doc.get('make','Unknown')} {selected_doc.get('model','Unknown')} {selected_doc.get('year','Unknown')} vin: {selected_doc.get('vin','Unknown')}"
                    selected_car_vin = selected_doc.get('vin','Unknown')
                    action_prompt_func = ACTION_PROMPTS[user__action_intent]
                    if user__action_intent == "make_offer":
                        print("Inside make_offer")
                        prompt = action_prompt_func(car_details, selected_car_vin, recent_history=" | ".join([
                            f"User: {msg.content}" if isinstance(msg, HumanMessage) else f"AI: {msg.content}"
                            for msg in formatted_chat_history[-4:]
                        ]))
                    elif user__action_intent == "test_drive":
                        prompt = action_prompt_func(car_details, selected_car_vin, recent_history=" | ".join([
                            f"User: {msg.content}" if isinstance(msg, HumanMessage) else f"AI: {msg.content}"
                            for msg in formatted_chat_history[-4:]
                        ]))
                        type = 'send_location'
                    elif user__action_intent == "visit_seller":
                        prompt = action_prompt_func(car_details, selected_car_vin, recent_history=" | ".join([
                            f"User: {msg.content}" if isinstance(msg, HumanMessage) else f"AI: {msg.content}"
                            for msg in formatted_chat_history[-4:]
                        ]))
                    elif user__action_intent == "loan":
                        print(f"\nSelected vin: {selected_car_vin}\n")
                        prompt = action_prompt_func(car_details, selected_car_vin, recent_history=" | ".join([
                            f"User: {msg.content}" if isinstance(msg, HumanMessage) else f"AI: {msg.content}"
                            for msg in formatted_chat_history[-4:]
                        ]))
                    elif user__action_intent == "verify_user":
                        prompt = action_prompt_func(recent_history=" | ".join([
                            f"User: {msg.content}" if isinstance(msg, HumanMessage) else f"AI: {msg.content}"
                            for msg in formatted_chat_history[-2:]
                        ]))
                    else:
                        prompt = action_prompt_func(car_details,selected_car_vin, recent_history=" | ".join([
                            f"User: {msg.content}" if isinstance(msg, HumanMessage) else f"AI: {msg.content}"
                            for msg in formatted_chat_history[-4:]
                        ]))
                    action_response = get_llm().invoke(prompt).content
                    print("\n----------------------------------------------------")
                    print(f"\nAction Response: {action_response}\n")
                    print("----------------------------------------------------\n")

                    # Check if action completed by looking for final JSON
                    if extract_final_json(action_response):
                        final_payload = extract_final_json(action_response)
                        if "Response" in action_response:
                            stripped_action_response = re.split(r"\s*Response\s*", action_response, maxsplit=1)[0].strip()
                        elif "SOURCES" in action_response:
                            stripped_action_response = re.split(r"\s*SOURCES\s*", action_response, maxsplit=1)[0].strip()
                        else:
                            stripped_action_response = re.split(r"\s*JSON\s*", action_response, maxsplit=1)[0].strip()
                        return {
                            "message": stripped_action_response,
                            "docs": {},
                            "type": final_payload.get("type",""),
                            "question": final_payload.get("question",""),
                            "vin": final_payload.get("vin",""),
                            "price": final_payload.get("price",""),
                            "area": final_payload.get("area",""),
                            "location": final_payload.get("location",""),
                            "date": final_payload.get("date",""),
                            "time": final_payload.get("time",""),
                            "amount": final_payload.get("amount",""),
                        }
                    else:
                        if "Response" in action_response:
                            stripped_action_response = re.split(r"\s*Response\s*", action_response, maxsplit=1)[0].strip()
                        elif "SOURCES" in action_response:
                            stripped_action_response = re.split(r"\s*SOURCES\s*", action_response, maxsplit=1)[0].strip()
                        else:
                            stripped_action_response = re.split(r"\s*JSON\s*", action_response, maxsplit=1)[0].strip()
                        # Action is ongoing, return the action prompt response without JSON
                        return {
                            "message": stripped_action_response,
                            "docs": matching_docs,
                            "type": type,
                            "question": "",
                            "vin": selected_car_vin,
                            "price": "",
                            "area": "",
                            "location": "",
                            "date": "",
                            "time": "",
                            "amount": "",
                        }

        # If no action triggered, return main QA response
        if shortlist_flag.lower() == "yes":
            type_flag = "shortlisted"
        elif wishlist_flag.lower() == "yes":
            type_flag = "wishlist"
        elif connect_flag.lower() == "yes":
            type_flag = "connect"
        else:
            type_flag = "browse"

        # No "json" key if no action or no special JSON
        return {
            "message": stripped_answer,
            "docs": matching_docs,
            "type": type_flag,
            "question": "",
            "vin": "",
            "price": "",
            "area": "",
            "location": "",
            "date": "",
            "time": "",
            "amount": ""
        }


    except Exception as e:
        print(f"Exception: {e}")
        return "An error occurred while processing your request.", [], "browse"

        
