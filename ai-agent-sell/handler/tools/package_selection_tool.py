from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field

          
class package_selection_input(BaseModel):
    """Package Price"""
    package : int = Field(..., description="Package Price")
    vehicle_number : str = Field(..., description="Vehicle number") 

def package_selection_tool(package: int, vehicle_number : str) -> dict:
    """
    Package Tool
    
    It will take Package option price from user.
    
    """
    
    return {
        'price': package,
        'vehicle_number': vehicle_number
    }
    

package = StructuredTool.from_function(
        func=package_selection_tool,
        name="package_selection_tool",
        description="It will take package option price from user.",
        args_schema=package_selection_input,
    )