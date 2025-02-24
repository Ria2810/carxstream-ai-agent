from langchain.chat_models import ChatOpenAI
from config.Constants import OPENAI_API_KEY,AI_MODEL


def init_openai_chat(temperature=0):
    """
    Initialize an advanced OpenAI Chat model for answering car-related queries."""
    return ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        streaming=True,
        temperature=temperature,
        model=AI_MODEL
    )


def get_llm(temperature=0):
    """
    Return the initialized OpenAI chat model.
    """
    return init_openai_chat(temperature=temperature)
