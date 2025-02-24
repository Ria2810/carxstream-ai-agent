from langchain_openai import ChatOpenAI
from config.index import OPENAI_API_KEY, AI_MODEL
from langchain_core.messages import AIMessage, HumanMessage

model = ChatOpenAI(temperature=0, model=AI_MODEL, openai_api_key=OPENAI_API_KEY)

def is_confused_response_openai(tool_response_message):
    """
    Uses OpenAI to determine if the tool response indicates confusion or inability to help.
    """
    if not tool_response_message:
        return False

    # Construct the prompt for analysis
    prompt = f"""
    Analyze the following response and determine if it indicates confusion, inability to help, or lack of information:
    Response: "{tool_response_message}"
    
    Return "Yes" if it indicates confusion or inability, otherwise return "No".

    **IMPORTANT: If the Response is indicating questions from users for giving more information or asking to make a choice, then always return "No".**
    """
    # Call OpenAI
    analysis_result = model.invoke(prompt).content.strip().lower()
    if analysis_result.lower() == "yes":
        return analysis_result
    else: 
        return "NO"



def format_chat_history(chat_history):
    """
    Formats raw chat history for use in prompt generation.
    """
    formatted_messages = []
    for message in chat_history:
        if isinstance(message, HumanMessage):
            formatted_messages.append(HumanMessage(content=message.content))
        elif isinstance(message, AIMessage):
            formatted_messages.append(AIMessage(content=message.content))
        else:
            raise ValueError("Unsupported message type in chat history.")
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


def customer_service_tool(context):
    """
    Tool for handling customer service interactions using the chat history in 'messages'.

    Args:
        context (dict): Contains the chat history (messages), the tool's response, and optionally the user's message.

    Returns:
        dict: A structured response indicating the result of the interaction.
    """

    print(f"\nCONTEXT: {context}\n")
    # Ensure 'tool_response' and 'messages' exist in the context and are valid
    if "tool_response" not in context or "messages" not in context or not isinstance(context["messages"], list):
        raise ValueError("'tool_response' or 'messages' key is missing or not valid in the context.")

    tool_response = context["tool_response"]
    serialized_messages = context["messages"]
    user_message = context.get("user_message", None)
    print("User message: ", user_message)

    # formatted_chat_history = format_chat_history(serialized_messages)

    # user_message = get_last_user_message(formatted_chat_history)

    # Construct the AI prompt
    CUSTOMER_SERVICE_PROMPT = f"""
    You are an AI agent responsible for handling customer service interactions. 

    Scenario:
    A user received the following response from a tool, which may indicate confusion or lack of information:
    "{tool_response}"

    Your responsibilities:
    1. Always begin with generating a follow-up message asking the user if they would like to connect to customer service for further assistance along with the last tool message {tool_response} shown in the first line.
        **Make sure you only ask this question once and move forward to the next step.** 
    2. If the user provides a response to the above question:
       - If they agree (e.g., "Yes", "Sure"), confirm connection with a message: "Sure, I will now connect you to customer service."
       - If they decline (e.g., "No", "Not now"), politely acknowledge with a message: "Okay, let me know if I can help you with something else. Thanks!"

    Rules:
    - Always guide the user through a clear and logical sequence.
    - Provide concise and user-friendly responses.

    Chat History:
    {serialized_messages}


    User Response:
    {user_message}
    """

    # Invoke the AI model
    model = ChatOpenAI(temperature=0, model="gpt-4o-mini", openai_api_key=OPENAI_API_KEY)
    ai_response = model.invoke(CUSTOMER_SERVICE_PROMPT).content.strip()

    # Parse the type from the AI's response
    type_flag = None
    if "connect you to customer service" in ai_response.lower():
        type_flag = "customer_service"

    # Return the structured response
    return {
        "message": ai_response,
        "type": type_flag,
    }
