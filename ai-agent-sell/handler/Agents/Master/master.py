from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from tools.comparison_tool import comparison
from tools.user_input_tool import input
from tools.vehicle_existence_check import vehicle_existence
from tools.package_selection_tool import package
from tools.package_showing_tool import package_list
from config.index import OPEN_API_KEY
from config.index import CURRENT_ENV

def create_agent(custom_prompt):
    llm = ChatOpenAI(temperature=0, model="gpt-4o-mini", openai_api_key=OPEN_API_KEY)
    tools = [comparison, input, vehicle_existence, package, package_list]
    
    # If CURRENT_ENV == "LOCAL", you can use MemorySaver, else just state_modifier
    if CURRENT_ENV == "LOCAL":
        memory = MemorySaver()
        return create_react_agent(llm, tools=tools, checkpointer=memory, state_modifier=custom_prompt)
    else:
        return create_react_agent(llm, tools=tools, state_modifier=custom_prompt)
