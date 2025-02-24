import openai
from config.index import OPENAI_API_KEY
# Load your OpenAI API key from an environment variable

openai.api_key = OPENAI_API_KEY

async def get_intent(message, old_messages):
    messages = [
        *old_messages,
        {
            "role": "system",
            "content": (
                "You are a friendly, advanced assistant specializing in car transactions. "
                "Identify if the user's message indicates they are interested in buying or selling a car. "
                "When responding, use natural language and acknowledge any car models or brands they mention. "
                "If the user wants to sell their car, respond with something like 'You want to sell your [car model]. "
                "I’d love to help you with that! I'll redirect you to our selling agent now.' "
                "If the user wants to buy, respond with something like 'You want to buy a [car model]. "
                "I’ll connect you to our buying agent who can assist further!' "
                "If it’s unclear whether they want to buy or sell, ask a clarifying question or respond with 'I'm here to help!'"
            ),
        },
        {
            "role": "user",
            "content": message,
        },
    ]

    try:
        # Make a request to OpenAI's Chat Completion API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=50,
            temperature=0.7,
        )

        # Extract the response text
        intent_response = response['choices'][0]['message']['content'].strip().lower()

        # Basic intent check
        if "buy" in intent_response:
            return "buy"
        elif "sell" in intent_response:
            return "sell"
        else:
            return "unknown"

    except Exception as e:
        print("Error with OpenAI API request:", e)
        return "error"


