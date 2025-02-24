from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field

          
class decision_maker_input(BaseModel):
    """Package Price"""
    intent : str = Field(..., description="Intent")

def decision_maker_tool(intent: str) -> str:
    """
    Decision Making Tool
    
    It helps to take the decision based on intent.
    
    """
    
    return intent
    

decision = StructuredTool.from_function(
        func=decision_maker_tool,
        name="decision_maker_tool",
        description="It helps to take the decision based on intent.",
        args_schema=decision_maker_input,
    )